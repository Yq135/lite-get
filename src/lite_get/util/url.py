import logging
import socket
import ssl
from importlib import import_module
from urllib import parse, request, error

from .strings import *
from ..cookies import cookiesBox
from .cotools import maybe_print, tr

SITES = {
    '163': 'netease',
    'bilibili': 'bilibili',
    'youtube': 'youtube',
}

fake_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/126.0.2592.113'
    # Latest Edge
}

insecure = False


def urlopen_with_retry(*args, **kwargs):
    retry_time = 3
    for i in range(retry_time):
        try:
            if insecure:
                # ignore ssl errors
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                return request.urlopen(*args, context=ctx, **kwargs)
            else:
                return request.urlopen(*args, **kwargs)
        except socket.timeout as e:
            logging.debug('request attempt %s timeout' % str(i + 1))
            if i + 1 == retry_time:
                raise e
        # try to tackle youku CDN fails
        except error.HTTPError as http_error:
            logging.debug('HTTP Error with code{}'.format(http_error.code))
            if i + 1 == retry_time:
                raise http_error


def get_location(url, headers=None, get_method='HEAD'):
    logging.debug('get_location: %s' % url)

    if headers:
        req = request.Request(url, headers=headers)
    else:
        req = request.Request(url)
    req.get_method = lambda: get_method
    res = urlopen_with_retry(req)
    return res.geturl()


def url_to_module(url):
    # try:
    video_host = r1(r'https?://([^/]+)/', url)
    video_url = r1(r'https?://[^/]+(.*)', url)
    assert video_host and video_url
    # except AssertionError:
    #     raise RuntimeError("The incoming path rule does not match")

    if video_host.endswith('.com.cn') or video_host.endswith('.ac.cn'):
        video_host = video_host[:-3]
    domain = r1(r'(\.[^.]+\.[^.]+)$', video_host) or video_host
    assert domain, 'unsupported url: ' + url

    # all non-ASCII code points must be quoted (percent-encoded UTF-8)
    url = ''.join([ch if ord(ch) in range(128) else parse.quote(ch) for ch in url])
    video_host = r1(r'https?://([^/]+)/', url)
    video_url = r1(r'https?://[^/]+(.*)', url)

    k = r1(r'([^.]+)', domain)
    if k in SITES:
        return (
            import_module('.'.join(['lite_get', 'extractors', SITES[k]])),
            url
        )
    else:
        try:
            try:
                location = get_location(url)  # t.co isn't happy with fake_headers
            except:
                location = get_location(url, headers=fake_headers)
        except:
            location = get_location(url, headers=fake_headers, get_method='GET')

        if location and location != url and not location.startswith('/'):
            return url_to_module(location)
        else:
            return import_module('lite_get.extractors.universal'), url


def remove_url_parameters(url: str, suffix: str):
    start_index = url.index("http")
    end_index = url.index(suffix) + len(suffix)
    return url[start_index:end_index]


def ungzip(data):
    """Decompresses data for Content-Encoding: gzip.
    """
    from io import BytesIO
    import gzip
    buffer = BytesIO(data)
    f = gzip.GzipFile(fileobj=buffer)
    return f.read()


def undeflate(data):
    """Decompresses data for Content-Encoding: deflate.
    (the zlib compression is used.)
    """
    import zlib
    decompressobj = zlib.decompressobj(-zlib.MAX_WBITS)
    return decompressobj.decompress(data) + decompressobj.flush()


def get_content(url, headers={}, decoded=True):
    """Gets the content of a URL via sending a HTTP GET request.

    Args:
        url: A URL.
        headers: Request headers used by the client.
        decoded: Whether decode the response body using UTF-8 or the charset specified in Content-Type.

    Returns:
        The content as a string.
    """

    logging.debug('get_content: %s' % url)

    req = request.Request(url, headers=headers)

    host = r1(r'https?://([^/]+)/', url)
    cookies = cookiesBox.get_cookie(host)

    if cookies:
        # NOTE: Do not use cookies.add_cookie_header(req)
        # #HttpOnly_ cookies were not supported by CookieJar and MozillaCookieJar properly until python 3.10
        # See also:
        # - https://github.com/python/cpython/pull/17471
        # - https://bugs.python.org/issue2190
        # Here we add cookies to the request headers manually
        cookie_strings = []
        for cookie in list(cookies):
            cookie_strings.append(cookie.name + '=' + cookie.value)
        cookie_headers = {'Cookie': '; '.join(cookie_strings)}
        req.headers.update(cookie_headers)

    response = urlopen_with_retry(req)
    data = response.read()

    # Handle HTTP compression for gzip and deflate (zlib)
    content_encoding = response.getheader('Content-Encoding')
    if content_encoding == 'gzip':
        data = ungzip(data)
    elif content_encoding == 'deflate':
        data = undeflate(data)

    # Decode the response body
    if decoded:
        charset = match1(
            response.getheader('Content-Type', ''), r'charset=([\w-]+)'
        )
        if charset is not None:
            data = data.decode(charset, 'ignore')
        else:
            data = data.decode('utf-8', 'ignore')

    return data


def post_content(url, headers={}, post_data={}, decoded=True, **kwargs):
    """Post the content of a URL via sending a HTTP POST request.

    Args:
        url: A URL.
        headers: Request headers used by the client.
        decoded: Whether decode the response body using UTF-8 or the charset specified in Content-Type.

    Returns:
        The content as a string.
    """
    if kwargs.get('post_data_raw'):
        logging.debug('post_content: %s\npost_data_raw: %s' % (url, kwargs['post_data_raw']))
    else:
        logging.debug('post_content: %s\npost_data: %s' % (url, post_data))

    req = request.Request(url, headers=headers)

    host = r1(r'https?://([^/]+)/', url)
    cookies = cookiesBox.get_cookie(host)

    if cookies:
        # NOTE: Do not use cookies.add_cookie_header(req)
        # #HttpOnly_ cookies were not supported by CookieJar and MozillaCookieJar properly until python 3.10
        # See also:
        # - https://github.com/python/cpython/pull/17471
        # - https://bugs.python.org/issue2190
        # Here we add cookies to the request headers manually
        cookie_strings = []
        for cookie in list(cookies):
            cookie_strings.append(cookie.name + '=' + cookie.value)
        cookie_headers = {'Cookie': '; '.join(cookie_strings)}
        req.headers.update(cookie_headers)
    if kwargs.get('post_data_raw'):
        post_data_enc = bytes(kwargs['post_data_raw'], 'utf-8')
    else:
        post_data_enc = bytes(parse.urlencode(post_data), 'utf-8')
    response = urlopen_with_retry(req, data=post_data_enc)
    data = response.read()

    # Handle HTTP compression for gzip and deflate (zlib)
    content_encoding = response.getheader('Content-Encoding')
    if content_encoding == 'gzip':
        data = ungzip(data)
    elif content_encoding == 'deflate':
        data = undeflate(data)

    # Decode the response body
    if decoded:
        charset = match1(
            response.getheader('Content-Type'), r'charset=([\w-]+)'
        )
        if charset is not None:
            data = data.decode(charset)
        else:
            data = data.decode('utf-8')

    return data


def url_info(url, faker=False, headers={}):
    logging.debug('url_info: %s' % url)

    if faker:
        response = urlopen_with_retry(
            request.Request(url, headers=fake_headers)
        )
    elif headers:
        response = urlopen_with_retry(request.Request(url, headers=headers))
    else:
        response = urlopen_with_retry(request.Request(url))

    headers = response.headers

    type = headers['content-type']
    if type == 'image/jpg; charset=UTF-8' or type == 'image/jpg':
        type = 'audio/mpeg'  # fix for netease
    mapping = {
        'video/3gpp': '3gp',
        'video/f4v': 'flv',
        'video/mp4': 'mp4',
        'video/MP2T': 'ts',
        'video/quicktime': 'mov',
        'video/webm': 'webm',
        'video/x-flv': 'flv',
        'video/x-ms-asf': 'asf',
        'audio/mp4': 'mp4',
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/wave': 'wav',
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'application/pdf': 'pdf',
    }
    if type in mapping:
        ext = mapping[type]
    else:
        type = None
        if headers['content-disposition']:
            try:
                filename = parse.unquote(
                    r1(r'filename="?([^"]+)"?', headers['content-disposition'])
                )
                if len(filename.split('.')) > 1:
                    ext = filename.split('.')[-1]
                else:
                    ext = None
            except:
                ext = None
        else:
            ext = None

    if headers['transfer-encoding'] != 'chunked':
        size = headers['content-length'] and int(headers['content-length'])
    else:
        size = None

    return type, ext, size


def print_info(site_info, title, type, size, **kwargs):
    # if json_output:
    #     json_output_.print_info(
    #         site_info=site_info, title=title, type=type, size=size
    #     )
    #     return
    if type:
        type = type.lower()
    if type in ['3gp']:
        type = 'video/3gpp'
    elif type in ['asf', 'wmv']:
        type = 'video/x-ms-asf'
    elif type in ['flv', 'f4v']:
        type = 'video/x-flv'
    elif type in ['mkv']:
        type = 'video/x-matroska'
    elif type in ['mp3']:
        type = 'audio/mpeg'
    elif type in ['mp4']:
        type = 'video/mp4'
    elif type in ['mov']:
        type = 'video/quicktime'
    elif type in ['ts']:
        type = 'video/MP2T'
    elif type in ['webm']:
        type = 'video/webm'

    elif type in ['jpg']:
        type = 'image/jpeg'
    elif type in ['png']:
        type = 'image/png'
    elif type in ['gif']:
        type = 'image/gif'

    if type in ['video/3gpp']:
        type_info = '3GPP multimedia file (%s)' % type
    elif type in ['video/x-flv', 'video/f4v']:
        type_info = 'Flash video (%s)' % type
    elif type in ['video/mp4', 'video/x-m4v']:
        type_info = 'MPEG-4 video (%s)' % type
    elif type in ['video/MP2T']:
        type_info = 'MPEG-2 transport stream (%s)' % type
    elif type in ['video/webm']:
        type_info = 'WebM video (%s)' % type
    # elif type in ['video/ogg']:
    #    type_info = 'Ogg video (%s)' % type
    elif type in ['video/quicktime']:
        type_info = 'QuickTime video (%s)' % type
    elif type in ['video/x-matroska']:
        type_info = 'Matroska video (%s)' % type
    # elif type in ['video/x-ms-wmv']:
    #    type_info = 'Windows Media video (%s)' % type
    elif type in ['video/x-ms-asf']:
        type_info = 'Advanced Systems Format (%s)' % type
    # elif type in ['video/mpeg']:
    #    type_info = 'MPEG video (%s)' % type
    elif type in ['audio/mp4', 'audio/m4a']:
        type_info = 'MPEG-4 audio (%s)' % type
    elif type in ['audio/mpeg']:
        type_info = 'MP3 (%s)' % type
    elif type in ['audio/wav', 'audio/wave', 'audio/x-wav']:
        type_info = 'Waveform Audio File Format ({})'.format(type)

    elif type in ['image/jpeg']:
        type_info = 'JPEG Image (%s)' % type
    elif type in ['image/png']:
        type_info = 'Portable Network Graphics (%s)' % type
    elif type in ['image/gif']:
        type_info = 'Graphics Interchange Format (%s)' % type
    elif type in ['m3u8']:
        if 'm3u8_type' in kwargs:
            if kwargs['m3u8_type'] == 'master':
                type_info = 'M3U8 Master {}'.format(type)
        else:
            type_info = 'M3U8 Playlist {}'.format(type)
    else:
        type_info = 'Unknown type (%s)' % type

    maybe_print('Site:      ', site_info)
    maybe_print('Title:     ', unescape_html(tr(title)))
    print('Type:      ', type_info)
    if type != 'm3u8':
        print(
            'Size:      ', round(size / 1048576, 2),
            'MiB (' + str(size) + ' Bytes)'
        )
    if type == 'm3u8' and 'm3u8_url' in kwargs:
        print('M3U8 Url:   {}'.format(kwargs['m3u8_url']))
    print()


# DEPRECATED in favor of get_content()
def get_response(url, faker=False):
    logging.debug('get_response: %s' % url)
    ctx = None
    if insecure:
        # ignore ssl errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    # install cookies
    host = r1(r'https?://([^/]+)/', url)
    cookies = cookiesBox.get_cookie(host)

    if cookies:
        opener = request.build_opener(request.HTTPCookieProcessor(cookies))
        request.install_opener(opener)

    if faker:
        response = request.urlopen(
            request.Request(url, headers=fake_headers), None, context=ctx,
        )
    else:
        response = request.urlopen(url, context=ctx)

    data = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        data = ungzip(data)
    elif response.info().get('Content-Encoding') == 'deflate':
        data = undeflate(data)
    response.data = data
    return response


def get_decoded_html(url, faker=False):
    response = get_response(url, faker)
    data = response.data
    charset = r1(r'charset=([\w-]+)', response.headers['content-type'])
    if charset:
        return data.decode(charset, 'ignore')
    else:
        return data

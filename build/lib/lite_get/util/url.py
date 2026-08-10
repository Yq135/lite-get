import logging
import socket
import ssl
from importlib import import_module
from urllib import parse, request, error

from .strings import r1

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
            import_module('.'.join(['you_get', 'extractors', SITES[k]])),
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
            return import_module('you_get.extractors.universal'), url


def remove_url_parameters(url: str, suffix: str):
    start_index = url.index("http")
    end_index = url.index(suffix) + len(suffix)
    return url[start_index:end_index]

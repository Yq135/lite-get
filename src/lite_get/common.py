#!/usr/bin/env python

import argparse
import os
import sys
import time

from .cookies.cookiesBox import set_cookie
from .util import log, term
from .util.url import *
from .version import __version__

dry_run = False
# json_output = False
force = False
skip_existing_file_size_check = False
# player = None
# extractor_proxy = None
cookies = None
output_filename = None
auto_rename = False
# insecure = False
m3u8 = False


def url_save(
        url, filepath, bar, refer=None, is_part=False, faker=False,
        headers=None, timeout=None, **kwargs
):
    tmp_headers = headers.copy() if headers is not None else {}
    # When a referer specified with param refer,
    # the key must be 'Referer' for the hack here
    if refer is not None:
        tmp_headers['Referer'] = refer
    if type(url) is list:
        chunk_sizes = [url_size(url, faker=faker, headers=tmp_headers) for url in url]
        file_size = sum(chunk_sizes)
        is_chunked, urls = True, url
    else:
        file_size = url_size(url, faker=faker, headers=tmp_headers)
        chunk_sizes = [file_size]
        is_chunked, urls = False, [url]

    continue_renameing = True
    while continue_renameing:
        continue_renameing = False
        if os.path.exists(filepath):
            if not force and (file_size == os.path.getsize(filepath) or skip_existing_file_size_check):
                if not is_part:
                    if bar:
                        bar.done()
                    if skip_existing_file_size_check:
                        log.warning(
                            'Skipping {} without checking size: file already exists'.format(
                                tr(os.path.basename(filepath))
                            )
                        )
                    else:
                        log.warning(
                            'Skipping {}: file already exists'.format(
                                tr(os.path.basename(filepath))
                            )
                        )
                else:
                    if bar:
                        bar.update_received(file_size)
                return
            else:
                if not is_part:
                    if bar:
                        bar.done()
                    if not force and auto_rename:
                        path, ext = os.path.basename(filepath).rsplit('.', 1)
                        finder = re.compile(r' \([1-9]\d*?\)$')
                        if (finder.search(path) is None):
                            thisfile = path + ' (1).' + ext
                        else:
                            def numreturn(a):
                                return ' (' + str(int(a.group()[2:-1]) + 1) + ').'

                            thisfile = finder.sub(numreturn, path) + ext
                        filepath = os.path.join(os.path.dirname(filepath), thisfile)
                        print('Changing name to %s' % tr(os.path.basename(filepath)), '...')
                        continue_renameing = True
                        continue
                    if log.yes_or_no('File with this name already exists. Overwrite?'):
                        log.warning('Overwriting %s ...' % tr(os.path.basename(filepath)))
                    else:
                        return
        elif not os.path.exists(os.path.dirname(filepath)):
            os.mkdir(os.path.dirname(filepath))

    temp_filepath = filepath + '.download' if file_size != float('inf') \
        else filepath
    received = 0
    if not force:
        open_mode = 'ab'

        if os.path.exists(temp_filepath):
            received += os.path.getsize(temp_filepath)
            if bar:
                bar.update_received(os.path.getsize(temp_filepath))
    else:
        open_mode = 'wb'

    chunk_start = 0
    chunk_end = 0
    for i, url in enumerate(urls):
        received_chunk = 0
        chunk_start += 0 if i == 0 else chunk_sizes[i - 1]
        chunk_end += chunk_sizes[i]
        if received < file_size and received < chunk_end:
            if faker:
                tmp_headers = fake_headers
            '''
            if parameter headers passed in, we have it copied as tmp_header
            elif headers:
                headers = headers
            else:
                headers = {}
            '''
            if received:
                # chunk_start will always be 0 if not chunked
                tmp_headers['Range'] = 'bytes=' + str(received - chunk_start) + '-'
            if refer:
                tmp_headers['Referer'] = refer

            if timeout:
                response = urlopen_with_retry(
                    request.Request(url, headers=tmp_headers), timeout=timeout
                )
            else:
                response = urlopen_with_retry(
                    request.Request(url, headers=tmp_headers)
                )
            try:
                range_start = int(
                    response.headers[
                        'content-range'
                    ][6:].split('/')[0].split('-')[0]
                )
                end_length = int(
                    response.headers['content-range'][6:].split('/')[1]
                )
                range_length = end_length - range_start
            except:
                content_length = response.headers['content-length']
                range_length = int(content_length) if content_length is not None \
                    else float('inf')

            if is_chunked:  # always append if chunked
                open_mode = 'ab'
            elif file_size != received + range_length:  # is it ever necessary?
                received = 0
                if bar:
                    bar.received = 0
                open_mode = 'wb'

            with open(temp_filepath, open_mode) as output:
                while True:
                    buffer = None
                    try:
                        buffer = response.read(1024 * 256)
                    except socket.timeout:
                        pass
                    if not buffer:
                        if file_size == float('+inf'):  # Prevent infinite downloading
                            break
                        if is_chunked and received_chunk == range_length:
                            break
                        elif not is_chunked and received == file_size:  # Download finished
                            break
                        # Unexpected termination. Retry request
                        tmp_headers['Range'] = 'bytes=' + str(received - chunk_start) + '-'
                        response = urlopen_with_retry(
                            request.Request(url, headers=tmp_headers)
                        )
                        continue
                    output.write(buffer)
                    received += len(buffer)
                    received_chunk += len(buffer)
                    if bar:
                        bar.update_received(len(buffer))

    assert received == os.path.getsize(temp_filepath), '%s == %s == %s' % (
        received, os.path.getsize(temp_filepath), temp_filepath
    )

    if os.access(filepath, os.W_OK) and file_size != float('inf'):
        # on Windows rename could fail if destination filepath exists
        # we should simply choose a new name instead of brutal os.remove(filepath)
        filepath = filepath + " (2)"
    os.rename(temp_filepath, filepath)


class SimpleProgressBar:
    term_size = term.get_terminal_size()[1]

    def __init__(self, total_size, total_pieces=1):
        self.displayed = False
        self.total_size = total_size
        self.total_pieces = total_pieces
        self.current_piece = 1
        self.received = 0
        self.speed = ''
        self.last_updated = time.time()

        total_pieces_len = len(str(total_pieces))
        # 38 is the size of all statically known size in self.bar
        total_str = '%5s' % round(self.total_size / 1048576, 1)
        total_str_width = max(len(total_str), 5)
        self.bar_size = self.term_size - 28 - 2 * total_pieces_len \
                        - 2 * total_str_width
        self.bar = '{:>4}%% ({:>%s}/%sMB) ├{:─<%s}┤[{:>%s}/{:>%s}] {}' % (
            total_str_width, total_str, self.bar_size, total_pieces_len,
            total_pieces_len
        )

    def update(self):
        self.displayed = True
        bar_size = self.bar_size
        percent = round(self.received * 100 / self.total_size, 1)
        if percent >= 100:
            percent = 100
        dots = bar_size * int(percent) // 100
        plus = int(percent) - dots // bar_size * 100
        if plus > 0.8:
            plus = '█'
        elif plus > 0.4:
            plus = '>'
        else:
            plus = ''
        bar = '█' * dots + plus
        bar = self.bar.format(
            percent, round(self.received / 1048576, 1), bar,
            self.current_piece, self.total_pieces, self.speed
        )
        sys.stdout.write('\r' + bar)
        sys.stdout.flush()

    def update_received(self, n):
        self.received += n
        time_diff = time.time() - self.last_updated
        bytes_ps = n / time_diff if time_diff else 0
        if bytes_ps >= 1024 ** 3:
            self.speed = '{:4.0f} GB/s'.format(bytes_ps / 1024 ** 3)
        elif bytes_ps >= 1024 ** 2:
            self.speed = '{:4.0f} MB/s'.format(bytes_ps / 1024 ** 2)
        elif bytes_ps >= 1024:
            self.speed = '{:4.0f} kB/s'.format(bytes_ps / 1024)
        else:
            self.speed = '{:4.0f}  B/s'.format(bytes_ps)
        self.last_updated = time.time()
        self.update()

    def update_piece(self, n):
        self.current_piece = n

    def done(self):
        if self.displayed:
            print()
            self.displayed = False


class PiecesProgressBar:
    def __init__(self, total_size, total_pieces=1):
        self.displayed = False
        self.total_size = total_size
        self.total_pieces = total_pieces
        self.current_piece = 1
        self.received = 0

    def update(self):
        self.displayed = True
        bar = '{0:>5}%[{1:<40}] {2}/{3}'.format(
            '', '=' * 40, self.current_piece, self.total_pieces
        )
        sys.stdout.write('\r' + bar)
        sys.stdout.flush()

    def update_received(self, n):
        self.received += n
        self.update()

    def update_piece(self, n):
        self.current_piece = n

    def done(self):
        if self.displayed:
            print()
            self.displayed = False


class DummyProgressBar:
    def __init__(self, *args):
        pass

    def update_received(self, n):
        pass

    def update_piece(self, n):
        pass

    def done(self):
        pass


def get_output_filename(urls, title, ext, output_dir, merge, **kwargs):
    # lame hack for the --output-filename option
    global output_filename
    if output_filename:
        result = output_filename
        if kwargs.get('part', -1) >= 0:
            result = '%s[%02d]' % (result, kwargs.get('part'))
        if ext:
            result = '%s.%s' % (result, ext)
        return result

    merged_ext = ext
    if (len(urls) > 1) and merge:
        from .processor.ffmpeg import has_ffmpeg_installed
        if ext in ['flv', 'f4v']:
            if has_ffmpeg_installed():
                merged_ext = 'mp4'
            else:
                merged_ext = 'flv'
        elif ext == 'mp4':
            merged_ext = 'mp4'
        elif ext == 'ts':
            if has_ffmpeg_installed():
                merged_ext = 'mkv'
            else:
                merged_ext = 'ts'
    result = title
    if kwargs.get('part', -1) >= 0:
        result = '%s[%02d]' % (result, kwargs.get('part'))
    result = '%s.%s' % (result, merged_ext)
    return result.replace("'", "_")


def url_size(url, faker=False, headers={}):
    if faker:
        response = urlopen_with_retry(
            request.Request(url, headers=fake_headers)
        )
    elif headers:
        response = urlopen_with_retry(request.Request(url, headers=headers))
    else:
        response = urlopen_with_retry(url)

    size = response.headers['content-length']
    return int(size) if size is not None else float('inf')


def urls_size(urls, faker=False, headers={}):
    return sum([url_size(url, faker=faker, headers=headers) for url in urls])


def download_urls(
        urls, title, ext, total_size, output_dir='.', refer=None, merge=True,
        faker=False, headers={}, **kwargs
):
    assert urls
    # if json_output:
    #     json_output_.download_urls(
    #         urls=urls, title=title, ext=ext, total_size=total_size,
    #         refer=refer
    #     )
    #     return
    # if dry_run:
    #     print_user_agent(faker=faker)
    #     try:
    #         print('Real URLs:\n%s' % '\n'.join(urls))
    #     except:
    #         print('Real URLs:\n%s' % '\n'.join([j for i in urls for j in i]))
    #     return

    # if player:
    #     launch_player(player, urls)
    #     return

    if not total_size:
        try:
            total_size = urls_size(urls, faker=faker, headers=headers)
        except:
            import traceback
            traceback.print_exc(file=sys.stdout)
            pass

    title = tr(get_filename(title))
    # if postfix and 'vid' in kwargs:
    #     title = "%s [%s]" % (title, kwargs['vid'])
    # if prefix is not None:
    #     title = "[%s] %s" % (prefix, title)
    output_filename = get_output_filename(urls, title, ext, output_dir, merge)
    output_filepath = os.path.join(output_dir, output_filename)

    if total_size:
        bar = SimpleProgressBar(total_size, len(urls))
    else:
        bar = PiecesProgressBar(total_size, len(urls))

    if len(urls) == 1:
        url = urls[0]
        print('Downloading %s ...' % tr(output_filename))
        bar.update()
        url_save(
            url, output_filepath, bar, refer=refer, faker=faker,
            headers=headers, **kwargs
        )
        bar.done()
    else:
        parts = []
        print('Downloading %s ...' % tr(output_filename))
        bar.update()
        for i, url in enumerate(urls):
            output_filename_i = get_output_filename(urls, title, ext, output_dir, merge, part=i)
            output_filepath_i = os.path.join(output_dir, output_filename_i)
            parts.append(output_filepath_i)
            # print 'Downloading %s [%s/%s]...' % (tr(filename), i + 1, len(urls))
            bar.update_piece(i + 1)
            url_save(
                url, output_filepath_i, bar, refer=refer, is_part=True, faker=faker,
                headers=headers, **kwargs
            )
        bar.done()

        if not merge:
            print()
            return

        if 'av' in kwargs and kwargs['av']:
            from .processor.ffmpeg import has_ffmpeg_installed
            if has_ffmpeg_installed():
                from .processor.ffmpeg import ffmpeg_concat_av
                ret = ffmpeg_concat_av(parts, output_filepath, ext)
                print('Merged into %s' % output_filename)
                if ret == 0:
                    for part in parts:
                        os.remove(part)

        elif ext in ['flv', 'f4v']:
            try:
                from .processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from .processor.ffmpeg import ffmpeg_concat_flv_to_mp4
                    ffmpeg_concat_flv_to_mp4(parts, output_filepath)
                else:
                    from .processor.join_flv import concat_flv
                    concat_flv(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'mp4':
            try:
                from .processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from .processor.ffmpeg import ffmpeg_concat_mp4_to_mp4
                    ffmpeg_concat_mp4_to_mp4(parts, output_filepath)
                else:
                    from .processor.join_mp4 import concat_mp4
                    concat_mp4(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'ts':
            try:
                from .processor.ffmpeg import has_ffmpeg_installed
                if has_ffmpeg_installed():
                    from .processor.ffmpeg import ffmpeg_concat_ts_to_mkv
                    ffmpeg_concat_ts_to_mkv(parts, output_filepath)
                else:
                    from .processor.join_ts import concat_ts
                    concat_ts(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        elif ext == 'mp3':
            try:
                from .processor.ffmpeg import has_ffmpeg_installed

                assert has_ffmpeg_installed()
                from .processor.ffmpeg import ffmpeg_concat_mp3_to_mp3
                ffmpeg_concat_mp3_to_mp3(parts, output_filepath)
                print('Merged into %s' % output_filename)
            except:
                raise
            else:
                for part in parts:
                    os.remove(part)

        else:
            print("Can't merge %s files" % ext)

    print()


def print_more_compatible(*args, **kwargs):
    import builtins as __builtin__
    """Overload default print function as py (<3.3) does not support 'flush' keyword.
    Although the function name can be same as print to get itself overloaded automatically,
    I'd rather leave it with a different name and only overload it when importing to make less confusion.
    """
    # nothing happens on py3.3 and later
    if sys.version_info[:2] >= (3, 3):
        return __builtin__.print(*args, **kwargs)

    # in lower pyver (e.g. 3.2.x), remove 'flush' keyword and flush it as requested
    doFlush = kwargs.pop('flush', False)
    ret = __builtin__.print(*args, **kwargs)
    if doFlush:
        kwargs.get('file', sys.stdout).flush()
    return ret


def download_url_ffmpeg(url, title, ext, params={}, output_dir='.', stream=True):
    assert url

    from .processor.ffmpeg import has_ffmpeg_installed, ffmpeg_download_stream
    assert has_ffmpeg_installed(), 'FFmpeg not installed.'

    global output_filename
    if output_filename:
        dotPos = output_filename.rfind('.')
        if dotPos > 0:
            title = output_filename[:dotPos]
            ext = output_filename[dotPos + 1:]
        else:
            title = output_filename

    title = tr(get_filename(title))

    ffmpeg_download_stream(url, title, ext, params, output_dir, stream=stream)


def download_main(download, urls, **kwargs):
    for url in urls:
        if re.match(r'https?://', url) is None:
            url = 'http://' + url

        if m3u8:
            if output_filename:
                title = output_filename
            else:
                title = "m3u8file"
            download_url_ffmpeg(url=url, title=title, ext='mp4', output_dir=".", stream=False)
        else:
            download(url, **kwargs)


def script_main(download, **kwargs):
    logging.basicConfig(format='[%(levelname)s] %(message)s')

    def print_version():
        log.info(
            'version {}, a tiny downloader that scrapes the web.'.format(
                __version__
            )
        )

    parser = argparse.ArgumentParser(
        prog='lite-get',
        usage='lite-get [OPTION]... URL...',
        description='A tiny downloader that scrapes the web',
        add_help=False,
    )
    parser.add_argument(
        '-V', '--version', action='store_true',
        help='Print version and exit'
    )
    parser.add_argument(
        '-h', '--help', action='store_true',
        help='Print this help message and exit'
    )
    dry_run_grp = parser.add_argument_group(
        'Dry-run options', '(no actual downloading)'
    )
    dry_run_grp = dry_run_grp.add_mutually_exclusive_group()
    dry_run_grp.add_argument(
        '-i', '--info', action='store_true', help='Print extracted information'
    )
    dry_run_grp.add_argument(
        '-u', '--url', action='store_true',
        help='Print extracted information with URLs'
    )
    dry_run_grp.add_argument(
        '--json', action='store_true',
        help='Print extracted URLs in JSON format'
    )
    download_grp = parser.add_argument_group('Download options')
    download_grp.add_argument(
        '-O', '--output-filename', metavar='FILE', help='Set output filename'
    )
    download_grp.add_argument(
        '-o', '--output-dir', metavar='DIR', default='.',
        help='Set output directory'
    )
    download_grp.add_argument(
        '-c', '--cookies', metavar='COOKIES_FILE',
        help='Set cookies for each website via cookies.txt'
    )
    download_grp.add_argument('-m', '--m3u8', action='store_true', default=False,
                              help='download video using an m3u8 url')
    download_grp.add_argument(
        '-d', '--debug', action='store_true',
        help='Show traceback and other debug info'
    )
    parser.add_argument('URL', nargs='*', help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.help:
        print_version()
        parser.print_help()
        sys.exit()
    if args.version:
        print_version()
        sys.exit()
    if args.cookies:
        set_cookie(args.cookies)
        sys.exit()

    if args.debug:
        # Set level of root logger to DEBUG
        logging.getLogger().setLevel(logging.DEBUG)

    global output_filename
    output_filename = args.output_filename
    global m3u8
    if args.m3u8:
        m3u8 = True

    info_only = args.info
    # if args.url:
    #     dry_run = True

    URLs = []

    URLs.extend(args.URL)

    if not URLs:
        parser.print_help()
        sys.exit()

    socket.setdefaulttimeout(600)  # 设置默认十分钟

    try:
        extra = {'args': args}

        download_main(download, URLs,
                      output_dir=args.output_dir, merge=True, info_only=info_only,
                      **extra)

    except KeyboardInterrupt:
        if args.debug:
            raise
        else:
            sys.exit(1)
    except UnicodeEncodeError:
        if args.debug:
            raise
        log.error(
            '[error] oops, the current environment does not seem to support '
            'Unicode.'
        )
        log.error('please set it to a UTF-8-aware locale first,')
        log.error(
            'so as to save the video (with some Unicode characters) correctly.'
        )
        log.error('you can do it like this:')
        log.error('    (Windows)    % chcp 65001 ')
        log.error('    (Linux)      $ LC_CTYPE=en_US.UTF-8')
        sys.exit(1)
    except Exception:
        if not args.debug:
            log.error('[error] oops, something went wrong.')
            log.error(
                'don\'t panic, c\'est la vie. please try the following steps:'
            )
            log.error('  (1) Rule out any network problem.')
            log.error('  (2) Run the command with \'--debug\' option,')
            log.error('      and report this issue with the full output.')
        else:
            print_version()
            log.info(args)
            raise
        sys.exit(1)


def any_download(url, **kwargs):
    m, url = url_to_module(url)
    m.download(url, **kwargs)


def main(**kwargs):
    # print("fuck the common")
    script_main(any_download, **kwargs)

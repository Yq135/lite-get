#!/usr/bin/env python

import argparse
import locale
import logging
import re
import socket
import sys

from .util import log
from .util.strings import get_filename
from .util.url import url_to_module
from .version import __version__

if sys.stdout.isatty():
    default_encoding = sys.stdout.encoding.lower()
else:
    default_encoding = locale.getpreferredencoding().lower()

dry_run = False
json_output = False
force = False
skip_existing_file_size_check = False
player = None
extractor_proxy = None
cookies = None
output_filename = None
auto_rename = False
insecure = False
m3u8 = False
postfix = False
prefix = None


def tr(s):
    if default_encoding == 'utf-8':
        return s
    else:
        return s


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

    if args.debug:
        # Set level of root logger to DEBUG
        logging.getLogger().setLevel(logging.DEBUG)

    global output_filename
    output_filename = args.output_filename
    global m3u8
    if args.m3u8:
        m3u8 = True

    info_only = args.info
    if args.url:
        dry_run = True

    URLs = []
    # if args.input_file:
    #     logging.debug('you are trying to load urls from %s', args.input_file)
    #     if args.playlist:
    #         log.error(
    #             "reading playlist from a file is unsupported "
    #             "and won't make your life easier"
    #         )
    #         sys.exit(2)
    #     URLs.extend(args.input_file.read().splitlines())
    #     args.input_file.close()
    URLs.extend(args.URL)

    if not URLs:
        parser.print_help()
        sys.exit()

    socket.setdefaulttimeout(600)  # 设置默认十分钟

    try:
        extra = {'args': args}

        download_main(download, URLs, **extra)

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
            log.error('  (2) Make sure you-get is up-to-date.')
            log.error('  (3) Check if the issue is already known, on')
            log.error('        https://github.com/soimort/you-get/wiki/Known-Bugs')
            log.error('        https://github.com/soimort/you-get/issues')
            log.error('  (4) Run the command with \'--debug\' option,')
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

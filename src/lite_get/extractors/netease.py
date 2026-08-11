# 网易云提取器

__all__ = ['netease_download']

import os
from json import loads

from ..common import download_urls
from ..util.url import *


def netease_lyric_download(song, lyric, output_dir='.', info_only=False, playlist_prefix=""):
    if info_only: return

    title = "%s%s. %s" % (playlist_prefix, song['position'], song['name'])
    filename = '%s.lrc' % get_filename(title)
    print('Saving %s ...' % filename, end="", flush=True)
    with open(os.path.join(output_dir, filename),
              'w', encoding='utf-8') as x:
        x.write(lyric)
        print('Done.')


def netease_song_download(song, output_dir='.', info_only=False, playlist_prefix=""):
    title = "%s%s. %s" % (playlist_prefix, song['position'], song['name'])
    url_best = "http://music.163.com/song/media/outer/url?id=" + \
               str(song['id']) + ".mp3"
    '''
    songNet = 'p' + song['mp3Url'].split('/')[2][1:]

    if 'hMusic' in song and song['hMusic'] != None:
        url_best = make_url(songNet, song['hMusic']['dfsId'])
    elif 'mp3Url' in song:
        url_best = song['mp3Url']
    elif 'bMusic' in song:
        url_best = make_url(songNet, song['bMusic']['dfsId'])
    '''
    netease_download_common(title, url_best,
                            output_dir=output_dir, info_only=info_only)


def netease_download_common(title, url_best, output_dir, info_only):
    songtype, ext, size = url_info(url_best, faker=True)
    print_info(site_info, title, songtype, size)
    if not info_only:
        download_urls([url_best], title, ext, size, output_dir, faker=True)


def netease_cloud_music_download(url, output_dir='.', merge=True, info_only=False, **kwargs):
    rid = match1(url, r'\Wid=(.*)')
    if rid is None:
        rid = match1(url, r'/(\d+)/?')

    if "song" in url:
        j = loads(get_content("http://music.163.com/api/song/detail/?id=%s&ids=[%s]&csrf_token=" % (rid, rid),
                              headers={"Referer": "http://music.163.com/"}))
        netease_song_download(j["songs"][0], output_dir=output_dir, info_only=info_only)
        try:  # download lyrics
            assert kwargs['caption']
            l = loads(get_content("http://music.163.com/api/song/lyric/?id=%s&lv=-1&csrf_token=" % rid,
                                  headers={"Referer": "http://music.163.com/"}))
            netease_lyric_download(j["songs"][0], l["lrc"]["lyric"], output_dir=output_dir, info_only=info_only)
        except:
            pass
    else:
        print("其他暂不支持")
        pass



def netease_download(url, output_dir='.', merge=True, info_only=False, **kwargs):
    if "163.fm" in url:
        url = get_location(url)
    if "music.163.com" in url:
        netease_cloud_music_download(url, output_dir, merge, info_only, **kwargs)
    else:
        html = get_decoded_html(url)

        title = r1('movieDescription=\'([^\']+)\'', html) or r1('<title>(.+)</title>', html)

        if title[0] == ' ':
            title = title[1:]

        src = r1(r'<source src="([^"]+)"', html) or r1(r'<source type="[^"]+" src="([^"]+)"', html)

        if src:
            url = src
            _, ext, size = url_info(src)
            # sd_url = r1(r'(.+)-mobile.mp4', src) + ".flv"
            # hd_url = re.sub('/SD/', '/HD/', sd_url)

        else:
            url = (r1(r'["\'](.+)-list.m3u8["\']', html) or r1(r'["\'](.+).m3u8["\']', html)) + ".mp4"
            _, _, size = url_info(url)
            ext = 'mp4'

        print_info(site_info, title, ext, size)
        if not info_only:
            download_urls([url], title, ext, size, output_dir=output_dir, merge=merge)


site_info = "163.com"
download = netease_download

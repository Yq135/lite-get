import os
import time
from http import cookiejar
from pathlib import Path

from ..util import log
from ..util.strings import r1

# 获取当前脚本所在的文件夹路径
current_dir = Path(__file__).resolve().parent
cookies = None

SITES = {
    '163': '163Cookies',
    'bilibili': 'biliCookies',
    'youtube': 'youtubeCookies',
}


def load_cookies(cookiefile):
    global cookies
    if cookiefile.endswith('.txt'):
        # MozillaCookieJar treats prefix '#HttpOnly_' as comments incorrectly!
        # do not use its load()
        # see also:
        #   - https://docs.python.org/3/library/http.cookiejar.html#http.cookiejar.MozillaCookieJar
        #   - https://github.com/python/cpython/blob/4b219ce/Lib/http/cookiejar.py#L2014
        #   - https://curl.haxx.se/libcurl/c/CURLOPT_COOKIELIST.html#EXAMPLE
        # cookies = cookiejar.MozillaCookieJar(cookiefile)
        # cookies.load()
        from http.cookiejar import Cookie
        cookies = cookiejar.MozillaCookieJar()
        now = time.time()
        ignore_discard, ignore_expires = False, False
        with open(cookiefile, 'r', encoding='utf-8') as f:
            for line in f:
                # last field may be absent, so keep any trailing tab
                if line.endswith("\n"): line = line[:-1]

                # skip comments and blank lines XXX what is $ for?
                if (line.strip().startswith(("#", "$")) or
                        line.strip() == ""):
                    if not line.strip().startswith('#HttpOnly_'):  # skip for #HttpOnly_
                        continue

                domain, domain_specified, path, secure, expires, name, value = \
                    line.split("\t")
                secure = (secure == "TRUE")
                domain_specified = (domain_specified == "TRUE")
                if name == "":
                    # cookies.txt regards 'Set-Cookie: foo' as a cookie
                    # with no name, whereas http.cookiejar regards it as a
                    # cookie with no value.
                    name = value
                    value = None

                initial_dot = domain.startswith(".")
                if not line.strip().startswith('#HttpOnly_'):  # skip for #HttpOnly_
                    assert domain_specified == initial_dot

                discard = False
                if expires == "":
                    expires = None
                    discard = True

                # assume path_specified is false
                c = Cookie(0, name, value,
                           None, False,
                           domain, domain_specified, initial_dot,
                           path, False,
                           secure,
                           expires,
                           discard,
                           None,
                           None,
                           {})
                if not ignore_discard and c.discard:
                    continue
                if not ignore_expires and c.is_expired(now):
                    continue
                cookies.set_cookie(c)

    elif cookiefile.endswith(('.sqlite', '.sqlite3')):
        import sqlite3, shutil, tempfile
        temp_dir = tempfile.gettempdir()
        temp_cookiefile = os.path.join(temp_dir, 'temp_cookiefile.sqlite')
        shutil.copy2(cookiefile, temp_cookiefile)

        cookies = cookiejar.MozillaCookieJar()
        con = sqlite3.connect(temp_cookiefile)
        cur = con.cursor()
        cur.execute("""SELECT host, path, isSecure, expiry, name, value
        FROM moz_cookies""")
        for item in cur.fetchall():
            c = cookiejar.Cookie(
                0, item[4], item[5], None, False, item[0],
                item[0].startswith('.'), item[0].startswith('.'),
                item[1], False, item[2], item[3], item[3] == '', None,
                None, {},
            )
            cookies.set_cookie(c)

    else:
        log.error('[error] unsupported cookies format')
        # TODO: Chromium Cookies
        # SELECT host_key, path, secure, expires_utc, name, encrypted_value
        # FROM cookies
        # http://n8henrie.com/2013/11/use-chromes-cookies-for-easier-downloading-with-python-requests/


def set_cookie(cookiefile):
    # TODO 将传入的文件保存到/用户/lite-get/cookies目录下
    pass


def get_cookie(host):
    domain = r1(r'(\.[^.]+\.[^.]+)$', host) or host
    # all non-ASCII code points must be quoted (percent-encoded UTF-8)
    k = r1(r'([^.]+)', domain)
    # print(os.path[0])
    # print(f"当前脚本所在目录: {current_dir}")
    cookiefile = str(current_dir) + "/" + SITES[k] + ".txt"
    load_cookies(cookiefile)
    return cookies

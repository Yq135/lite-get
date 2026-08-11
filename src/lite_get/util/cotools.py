import locale
import sys

if sys.stdout.isatty():
    default_encoding = sys.stdout.encoding.lower()
else:
    default_encoding = locale.getpreferredencoding().lower()


def tr(s):
    if default_encoding == 'utf-8':
        return s
    else:
        return s


def maybe_print(*s):
    try:
        print(*s)
    except:
        pass

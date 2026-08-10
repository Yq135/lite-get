import re
from html import unescape as unescape_html
from .fs import legitimize


def r1(pattern, text):
    m = re.search(pattern, text)
    if m:
        return m.group(1)


def get_filename(htmlstring):
    return legitimize(unescape_html(htmlstring))


def parameterize(string):
    return "'%s'" % string.replace("'", r"'\''")

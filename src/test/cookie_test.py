import unittest

from lite_get.cookies.cookiesBox import *

class TestUtil(unittest.TestCase):
    def test_get_cookie(self):
        cookie = get_cookie("music.163.com")
        print(cookie)


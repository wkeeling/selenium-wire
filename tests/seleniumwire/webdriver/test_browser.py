import logging
logging.basicConfig(level=logging.DEBUG)
from unittest import TestCase

from seleniumwire.webdriver import Firefox


class FirefoxEndToEndTest(TestCase):

    def test_capture_requests(self):
        firefox = Firefox()
        firefox.get('http://localhost')
        # firefox.get('http://www.google.co.uk')
        # firefox.get('http://www.github.com')
        for request in firefox.requests:
            print(request)
        # firefox.quit()

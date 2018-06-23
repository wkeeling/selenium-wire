import logging
logging.basicConfig(level=logging.INFO)
from unittest import TestCase

from seleniumwire.webdriver import Firefox


class FirefoxEndToEndTest(TestCase):

    def test_capture_requests(self):
        firefox = Firefox()
        firefox.get('http://www.bbc.co.uk')
        firefox.get('http://www.google.co.uk')
        firefox.capture_requests()
        firefox.get('http://www.github.com')
        firefox.quit()

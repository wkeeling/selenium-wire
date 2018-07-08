import logging
import os
import sys
from unittest import TestCase

# logging.basicConfig(level=logging.DEBUG)
sys.path.remove(os.path.dirname(__file__))

from seleniumwire import webdriver


# Need to test:
#    - Different browsers
#    - Different OS's
#    - Different Selenium versions


class SeleniumIntegrationTest(TestCase):

    # List of URLs and corresponding title elements
    sites = [
        ('https://www.python.org/', 'Python')
    ]

    def test_can_access_requests(self):
        firefox = webdriver.Firefox()
        firefox.get(self.sites[0][0])

        self.assertTrue(self.sites[0][1] in firefox.title)
        request = firefox.wait_for_request(self.sites[0][0])
        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        firefox.quit()

import logging
import os
import sys
from unittest import TestCase

logging.basicConfig(level=logging.DEBUG)
sys.path.remove(os.path.dirname(__file__))

from seleniumwire import webdriver


# Need to test:
#    - Different browsers
#    - Different OS's
#    - Different Selenium versions


class SeleniumIntegrationTest(TestCase):

    driver_config = [
        # (webdriver.Firefox, 'https://www.python.org/', 'Python'),
        (webdriver.Chrome, 'https://www.wikipedia.org/', 'Wikipedia')
    ]

    def test_can_access_requests(self):
        for driver_cls, url, title in self.driver_config:
            driver = driver_cls()
            driver.get(url)

            self.assertTrue(title in driver.title)
            request = driver.wait_for_request(url)
            self.assertEqual(request.response.status_code, 200)
            self.assertIn('text/html', request.response.headers['Content-Type'])

            driver.quit()

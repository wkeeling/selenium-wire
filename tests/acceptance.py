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
        ('https://www.wikipedia.org/', 'Wikipedia'),
        ('https://github.com/', 'GitHub')
    ]

    options = {
            'proxy': {
                'http': 'http://167.99.193.171:8000',
                'https': 'https://167.99.193.171:8000'
            }
    }

    def test_firefox_can_access_requests(self):
        url = 'https://www.python.org/'
        title = 'Python'
        driver = webdriver.Firefox(seleniumwire_options=self.options)
        driver.get(url)

        self.assertTrue(title in driver.title)
        request = driver.wait_for_request(url)
        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()


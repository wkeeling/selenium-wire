import logging
import os
from unittest import TestCase

logging.basicConfig(level=logging.DEBUG)

from seleniumwire import webdriver


class BrowserIntegrationTest(TestCase):

    def test_firefox_can_access_requests(self):
        url = 'https://www.python.org/'
        driver = webdriver.Firefox()
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_chrome_can_access_requests(self):
        url = 'https://www.wikipedia.org/'
        driver = webdriver.Chrome()
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_safari_can_access_requests(self):
        url = 'https://github.com/'
        options = {
            'port': 12345
        }
        driver = webdriver.Safari(seleniumwire_options=options)
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_edge_can_access_requests(self):
        url = 'https://google.com/'
        options = {
            'port': 12345
        }
        driver = webdriver.Edge(seleniumwire_options=options)
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_modify_user_agent(self):
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/28.0.1500.52 Safari/537.36 OPR/15.0.1147.100'
        url = 'https://www.python.org/'
        driver = webdriver.Firefox()
        driver.header_overrides = {
            'User-Agent': user_agent
        }
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.headers['User-Agent'], user_agent)

        driver.quit()

    def test_rewrite_url(self):
        driver = webdriver.Firefox()
        driver.rewrite_rules = [
            (r'(https?://)www.python.org/', r'\1www.wikipedia.org/')
        ]

        driver.get('https://www.python.org/')

        driver.wait_for_request('https://www.wikipedia.org/')  # Should find www.wikipedia.org

        driver.quit()

    def test_wait_for_request_headless_chrome(self):
        # https://github.com/wkeeling/selenium-wire/issues/6
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")

        def get_page_response(url):

            # check for current os
            if os.name == 'posix':
                # osx
                driver_path = '/usr/local/bin/chromedriver'
            elif os.name == 'nt':
                # win32
                driver_path = 'C:\chromedriver\chromedriver'
            else:
                print('Unknown operating system!!!')
                exit()

            driver = webdriver.Chrome(
                chrome_options=chrome_options,
                executable_path=driver_path
            )
            driver.get(url)
            request = driver.wait_for_request(url, timeout=3)
            print(request)

            self.assertEqual(request.path, 'https://www.google.com/')

        get_page_response('https://www.google.com')

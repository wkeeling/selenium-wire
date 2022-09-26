import logging
from unittest import TestCase

from seleniumwire import webdriver

logging.basicConfig(level=logging.INFO)


class BrowserIntegrationTest(TestCase):
    def test_simple_example(self):
        # Create a new instance of the Firefox driver
        driver = webdriver.Firefox()

        # Go to the Google home page
        driver.get('https://www.google.com')

        # Access requests via the `requests` attribute
        for request in driver.requests:
            if request.response:
                print(request.url, request.response.status_code, request.response.headers['Content-Type'])

        driver.quit()

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

    def test_chrome_remote_debugger(self):
        import subprocess
        import time

        def interceptor(request):
            del request.headers['referer']
            request.headers['referer'] = "https://www.test.com"

        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:12264")
        chromeadres = '/usr/bin/google-chrome-stable'
        subprocess.Popen(
            [
                chromeadres,
                "--remote-debugging-port=12264",
                "--ignore-certificate-errors",
                "--proxy-server=http://localhost:12345",
            ]
        )
        time.sleep(0.3)
        driver = webdriver.Chrome(chrome_options=options, seleniumwire_options={'port': 12345})
        driver.request_interceptor = interceptor
        driver.get('https://www.whatismyreferer.com')

        time.sleep(3)

    def test_safari_can_access_requests(self):
        url = 'https://github.com/'
        options = {'port': 12345}
        driver = webdriver.Safari(seleniumwire_options=options)
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_edge_can_access_requests(self):
        url = 'https://www.wikipedia.org/'
        driver = webdriver.Edge()
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_intercept_request(self):
        url = 'https://python.org'
        user_agent = (
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/28.0.1500.52 Safari/537.36 OPR/15.0.1147.100'
        )
        driver = webdriver.Firefox()

        def intercept(req):
            del req.headers['User-Agent']
            req.headers['User-Agent'] = user_agent

        driver.request_interceptor = intercept

        driver.get(url)

        driver.quit()

    def test_intercept_response(self):
        url = 'https://www.wikipedia.org/'
        driver = webdriver.Firefox()

        def intercept(req, res):
            res.headers['X-Foo'] = 'bar'

        driver.response_interceptor = intercept

        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual('bar', request.response.headers['X-Foo'])

        driver.quit()

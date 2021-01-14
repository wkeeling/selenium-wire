import logging
from unittest import TestCase

from seleniumwire import webdriver

logging.basicConfig(level=logging.DEBUG)


class BrowserIntegrationTest(TestCase):

    def test_simple_example(self):
        # Create a new instance of the Firefox driver
        driver = webdriver.Firefox()

        # Go to the Google home page
        driver.get('https://www.google.com')

        # Access requests via the `requests` attribute
        for request in driver.requests:
            if request.response:
                print(
                    request.url,
                    request.response.status_code,
                    request.response.headers['Content-Type']
                )

    def test_firefox_can_access_requests(self):
        url = 'https://www.python.org/'
        driver = webdriver.Firefox()
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(request.response.status_code, 200)
        self.assertIn('text/html', request.response.headers['Content-Type'])

        driver.quit()

    def test_firefox_can_access_requests_mitmproxy(self):
        url = 'https://www.python.org/'
        options = {
            'backend': 'mitmproxy',
        }
        driver = webdriver.Firefox(seleniumwire_options=options)
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

    def test_intercept_request(self):
        url = 'https://www.python.org'
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/28.0.1500.52 Safari/537.36 OPR/15.0.1147.100'
        driver = webdriver.Firefox()

        def intercept(req):
            del req.headers['User-Agent']
            req.headers['User-Agent'] = user_agent
            req.params = {**req.params, 'foo': 'bar'}

        driver.request_interceptor = intercept

        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual(user_agent, request.headers['User-Agent'])

        driver.quit()

    def test_intercept_response(self):
        url = 'https://www.guardian.co.uk'
        driver = webdriver.Firefox()

        def intercept(req, res):
            res.headers['X-Foo'] = 'bar'

        driver.response_interceptor = intercept

        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual('bar', request.response.headers['X-Foo'])

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

        self.assertEqual(user_agent, request.headers['User-Agent'])

        driver.quit()

    def test_add_cache_control(self):
        url = 'https://www.python.org/'
        driver = webdriver.Firefox()
        driver.header_overrides = {
            'response:Cache-Control': 'none'
        }
        driver.get(url)

        request = driver.wait_for_request(url)

        self.assertEqual('none', request.response.headers['Cache-Control'])

        driver.quit()

    def test_modify_param(self):
        driver = webdriver.Firefox()
        driver.param_overrides = {
            'foo': 'baz'
        }
        driver.get('https://httpbin.org/get?foo=bar')

        request = driver.wait_for_request(r'https://httpbin.org/get\?foo=baz')

        self.assertEqual({'foo': 'baz'}, request.params)

        driver.quit()

    def test_modify_querystring(self):
        options = {
            'backend': 'mitmproxy',
            'disable_encoding': True,
            'mitmproxy': {
                'https': 'https://localhost:8080'
            }
        }
        driver = webdriver.Firefox(seleniumwire_options=options)
        driver.querystring_overrides = 'foo=baz'
        driver.get('https://httpbin.org/get?foo=bar')

        request = driver.wait_for_request(r'https://httpbin.org/get\?foo=baz')

        self.assertEqual({'foo': 'baz'}, request.params)

        driver.quit()

    def test_rewrite_url(self):
        driver = webdriver.Firefox()
        driver.rewrite_rules = [
            (r'(https?://)www.python.org/', r'\1www.wikipedia.org/')
        ]

        driver.get('https://www.python.org/')

        driver.wait_for_request('https://www.wikipedia.org/')  # Should find www.wikipedia.org

        driver.quit()

    def test_custom_response_handler(self):
        """NOTE: this is being deprecated. Use driver.response_interceptor."""
        def custom(req, req_body, res, res_body):
            print(f'res_body length: {len(res_body)}')

        options = {
            'custom_response_handler': custom
        }

        driver = webdriver.Firefox(seleniumwire_options=options)

        driver.get('https://www.python.org/')

        driver.quit()

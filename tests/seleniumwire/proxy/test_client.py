import ssl
from unittest import TestCase
import urllib.error
import urllib.request

from seleniumwire.proxy.client import AdminClient


class AdminClientIntegrationTest(TestCase):

    def test_create_proxy(self):
        html = self._make_request('http://python.org')

        self.assertIn(b'Welcome to Python.org', html)

    def test_destroy_proxy(self):
        self.client.destroy_proxy()

        with self.assertRaises(urllib.error.URLError):
            self._make_request('http://github.com')

    def test_get_requests_single(self):
        self._make_request('https://www.python.org/')

        requests = self.client.get_requests()

        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request['method'], 'GET')
        self.assertEqual(request['path'], 'https://www.python.org/')
        self.assertEqual(request['headers']['Accept-Encoding'], 'identity')
        self.assertEqual(request['response']['status_code'], 200)
        self.assertEqual(request['response']['headers']['Content-Type'], 'text/html; charset=utf-8')

    def test_get_requests_multiple(self):
        self._make_request('https://github.com/')
        self._make_request('https://www.wikipedia.org/')

        requests = self.client.get_requests()

        self.assertEqual(len(requests), 2)

    def test_get_last_request(self):
        self._make_request('https://python.org')
        self._make_request('https://www.bbc.co.uk/')

        last_request = self.client.get_last_request()

        self.assertEqual(last_request['path'], 'https://www.bbc.co.uk/')

    def test_get_last_request_none(self):
        last_request = self.client.get_last_request()

        self.assertIsNone(last_request)

    def test_clear_requests(self):
        self._make_request('https://python.org')
        self._make_request('https://www.wikipedia.org')

        self.client.clear_requests()

        self.assertEqual(self.client.get_requests(), [])

    def test_find(self):
        self._make_request('https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15')
        self._make_request('https://docs.python.org/3.4/library/http.client.html')

        self.assertEqual(self.client.find('/questions/tagged/django')['path'],
                         'https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15')
        self.assertEqual(self.client.find('/3.4/library/http.client.html')['path'],
                         'https://docs.python.org/3.4/library/http.client.html')

    def test_get_request_body_empty(self):
        self._make_request('https://www.amazon.com')
        last_request = self.client.get_last_request()

        body = self.client.get_request_body(last_request['id'])

        self.assertIsNone(body)

    def test_get_response_body(self):
        self._make_request('https://www.wikipedia.org')
        last_request = self.client.get_last_request()

        body = self.client.get_response_body(last_request['id'])

        self.assertIsInstance(body, bytes)
        self.assertIn(b'html', body)

    def test_get_response_body_binary(self):
        self._make_request('https://www.python.org/static/img/python-logo@2x.png')
        last_request = self.client.get_last_request()

        body = self.client.get_response_body(last_request['id'])

        self.assertIsInstance(body, bytes)

    def test_get_response_body_empty(self):
        self._make_request('http://www.python.org')  # Redirects to https with empty body
        redirect_request = self.client.get_requests()[0]

        body = self.client.get_response_body(redirect_request['id'])

        self.assertIsNone(body)

    def test_set_header_overrides(self):
        self.client.set_header_overrides({
            'User-Agent': 'Test_User_Agent_String'
        })
        self._make_request('https://www.github.com')

        last_request = self.client.get_last_request()

        self.assertEqual(last_request['headers']['User-Agent'], 'Test_User_Agent_String')

    def test_set_header_overrides_case_insensitive(self):
        self.client.set_header_overrides({
            'user-agent': 'Test_User_Agent_String'  # Lowercase header name
        })
        self._make_request('https://www.bbc.co.uk')

        last_request = self.client.get_last_request()

        self.assertEqual(last_request['headers']['User-Agent'], 'Test_User_Agent_String')

    def test_set_header_overrides_filters_out_header(self):
        self.client.set_header_overrides({
            'User-Agent': None
        })
        self._make_request('https://www.wikipedia.org')

        last_request = self.client.get_last_request()

        self.assertNotIn('User-Agent', last_request['headers'])

    def test_clear_header_overrides(self):
        self.client.set_header_overrides({
            'User-Agent': 'Test_User_Agent_String'
        })
        self.client.clear_header_overrides()
        self._make_request('https://www.stackoverflow.com')

        last_request = self.client.get_last_request()

        self.assertNotEqual(last_request['headers']['User-Agent'], 'Test_User_Agent_String')

    def test_get_header_overrides(self):
        self.client.set_header_overrides({
            'User-Agent': 'Test_User_Agent_String'
        })

        self.assertEqual(self.client.get_header_overrides(), {
            'User-Agent': 'Test_User_Agent_String'
        })

    def test_set_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'http://stackoverflow.com(.*)', r'https://github.com\1'),
        ])
        self._make_request('http://stackoverflow.com')

        last_request = self.client.get_last_request()

        self.assertEqual(last_request['path'], 'https://github.com/')
        self.assertEqual(last_request['headers']['Host'], 'github.com')

    def test_clear_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'https://stackoverflow.com(.*)', r'https://www.github.com\1'),
        ])
        self.client.clear_rewrite_rules()

        self._make_request('https://www.stackoverflow.com/')

        last_request = self.client.get_last_request()

        self.assertEqual(last_request['path'], 'https://stackoverflow.com/')
        self.assertEqual(last_request['headers']['Host'], 'stackoverflow.com')

    def test_get_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'http://www.stackoverflow.com(.*)', r'https://www.github.com\1'),
        ])

        self.assertEqual(self.client.get_rewrite_rules(), [
            [r'http://www.stackoverflow.com(.*)', r'https://www.github.com\1'],
        ])

    def setUp(self):
        self.client = AdminClient()
        host, port = self.client.create_proxy()
        self._configure_proxy(host, port)

    def tearDown(self):
        self.client.destroy_proxy()

    def _configure_proxy(self, host, port):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        https_handler = urllib.request.HTTPSHandler(context=context)
        proxy_handler = urllib.request.ProxyHandler({
            'http': 'http://{}:{}'.format(host, port),
            'https': 'http://{}:{}'.format(host, port),
        })
        opener = urllib.request.build_opener(https_handler, proxy_handler)
        urllib.request.install_opener(opener)

    def _make_request(self, url):
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                         '(KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36')
        with urllib.request.urlopen(request, timeout=5) as response:
            html = response.read()

        return html

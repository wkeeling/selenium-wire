import json
import os
import ssl
import urllib.error
import urllib.request
from unittest import TestCase
from urllib.parse import parse_qs, urlsplit

from seleniumwire import backend


class BackendIntegrationTest(TestCase):

    backend = None

    def test_create_proxy(self):
        html = self._make_request('http://python.org')

        self.assertIn(b'Welcome to Python.org', html)

    def test_shutdown(self):
        self.backend.shutdown()

        with self.assertRaises(OSError):
            self._make_request('http://github.com')

    def test_get_requests_single(self):
        self._make_request('https://www.python.org/')

        requests = self.backend.storage.load_requests()

        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual('GET', request.method)
        self.assertEqual('https://www.python.org/', request.url)
        self.assertEqual('identity', request.headers['Accept-Encoding'])
        self.assertEqual(200, request.response.status_code)
        self.assertEqual('text/html; charset=utf-8', request.response.headers['Content-Type'])
        self.assertTrue(len(request.response.body) > 0)
        self.assertIn(b'html', request.response.body)

    def test_get_requests_multiple(self):
        self._make_request('https://github.com/')
        self._make_request('https://www.wikipedia.org/')

        requests = self.backend.storage.load_requests()

        self.assertEqual(2, len(requests))

    def test_get_last_request(self):
        self._make_request('https://python.org')
        self._make_request('https://www.bbc.co.uk/')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('https://www.bbc.co.uk/', last_request.url)

    def test_get_last_request_none(self):
        last_request = self.backend.storage.load_last_request()

        self.assertIsNone(last_request)

    def test_clear_requests(self):
        self._make_request('https://python.org')
        self._make_request('https://www.wikipedia.org')

        self.backend.storage.clear_requests()

        self.assertEqual([], self.backend.storage.load_requests())

    def test_find(self):
        self._make_request(
            'https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15')
        self._make_request(
            'https://docs.python.org/3.4/library/http.client.html')
        self._make_request('https://www.google.com')

        self.assertEqual(
            'https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15',
            self.backend.storage.find('/questions/tagged/django').url
        )
        self.assertEqual(
            'https://docs.python.org/3.4/library/http.client.html',
            self.backend.storage.find('/3.4/library/http.client.html').url
        )
        self.assertEqual(
            'https://www.google.com/',
            self.backend.storage.find('https://www.google.com').url
        )

    def test_get_request_body_empty(self):
        self._make_request('https://www.amazon.com')
        last_request = self.backend.storage.load_last_request()

        self.assertEqual(b'', last_request.body)

    def test_get_response_body_json(self):
        self._make_request('https://radiopaedia.org/api/v1/countries/current')  # Returns JSON
        last_request = self.backend.storage.load_last_request()

        self.assertIsInstance(last_request.response.body, bytes)

    def test_get_response_body_image(self):
        self._make_request(
            'https://www.python.org/static/img/python-logo@2x.png')
        last_request = self.backend.storage.load_last_request()

        self.assertIsInstance(last_request.response.body, bytes)

    def test_get_response_body_empty(self):
        # Redirects to https with empty body
        self._make_request('http://www.python.org')
        redirect_request = self.backend.storage.load_requests()[0]

        self.assertEqual(301, redirect_request.response.status_code)
        self.assertEqual(b'', redirect_request.response.body)

    def test_set_header_overrides(self):
        self.backend.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        self._make_request('https://www.github.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('Test_User_Agent_String', last_request.headers['User-Agent'])

    def test_set_header_overrides_case_insensitive(self):
        self.backend.modifier.headers = {
            'user-agent': 'Test_User_Agent_String'  # Lowercase header name
        }
        self._make_request('https://www.bbc.co.uk')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('Test_User_Agent_String', last_request.headers['User-Agent'])

    def test_set_header_overrides_filters_out_header(self):
        self.backend.modifier.headers = {
            'User-Agent': None
        }
        self._make_request('https://www.wikipedia.org')

        last_request = self.backend.storage.load_last_request()

        self.assertNotIn('User-Agent', last_request.headers)

    def test_clear_header_overrides(self):
        self.backend.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        del self.backend.modifier.headers
        self._make_request('https://www.stackoverflow.com')

        last_request = self.backend.storage.load_last_request()

        self.assertNotEqual(
            'Test_User_Agent_String', last_request.headers['User-Agent']
        )

    def test_set_param_overrides(self):
        self.backend.modifier.params = {'foo': 'baz'}

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.backend.storage.load_last_request()

        params = {k: v[0] for k, v in parse_qs(urlsplit(last_request.url).query).items()}
        self.assertEqual({
            'foo': 'baz',
            'spam': 'eggs'
        }, params)

    def test_set_param_overrides_post(self):
        self.backend.modifier.params = {'foo': 'baz'}

        self._make_request(
            'https://httpbin.org/post',
            method='POST',
            data=b'foo=bazzz&spam=eggs'
        )

        last_request = self.backend.storage.load_last_request()

        qs = parse_qs(last_request.body.decode('utf-8'))
        self.assertEqual(2, len(qs))
        self.assertEqual('baz', qs['foo'][0])
        self.assertEqual('eggs', qs['spam'][0])

    def test_set_param_overrides_filters_out_param(self):
        self.backend.modifier.params = {'foo': None}

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.backend.storage.load_last_request()

        query = urlsplit(last_request.url).query
        self.assertEqual('spam=eggs', query)

    def test_clear_param_overrides(self):
        self.backend.modifier.params = {'foo': 'baz'}
        del self.backend.modifier.params
        self._make_request('https://www.stackoverflow.com')

        last_request = self.backend.storage.load_last_request()

        query = urlsplit(last_request.url).query
        self.assertEqual('', query)

    def test_set_querystring_overrides(self):
        self.backend.modifier.querystring = 'foo=baz'

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.backend.storage.load_last_request()

        query = urlsplit(last_request.url)[3]
        self.assertEqual('foo=baz', query)

    def test_set_querystring_overrides_filters(self):
        self.backend.modifier.querystring = ''  # Empty string to filter a querystring (not None)

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.backend.storage.load_last_request()

        query = urlsplit(last_request.url)[3]
        self.assertEqual('', query)

    def test_clear_querystring_overrides(self):
        self.backend.modifier.querystring = 'foo=baz'
        del self.backend.modifier.querystring
        self._make_request('https://httpbin.org/get?foo=bar')

        last_request = self.backend.storage.load_last_request()

        query = urlsplit(last_request.url)[3]
        self.assertEqual('foo=bar', query)

    def test_set_rewrite_rules(self):
        self.backend.modifier.rewrite_rules = [
            (r'https://stackoverflow.com(.*)', r'https://github.com\1'),
        ]
        self._make_request('https://stackoverflow.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('https://github.com/', last_request.url)
        self.assertEqual('github.com', last_request.headers['Host'])

    def test_clear_rewrite_rules(self):
        self.backend.modifier.rewrite_rules = [
            (r'https://stackoverflow.com(.*)', r'https://www.github.com\1'),
        ]
        del self.backend.modifier.rewrite_rules

        self._make_request('https://www.stackoverflow.com/')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request.url)
        self.assertEqual('stackoverflow.com', last_request.headers['Host'])

    def test_set_single_scopes(self):
        self.backend.scopes = ['.*stackoverflow.*']

        self._make_request('https://stackoverflow.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request.url)
        self.assertEqual('stackoverflow.com', last_request.headers['Host'])

        self._make_request('https://github.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request.url)
        self.assertEqual('stackoverflow.com', last_request.headers['Host'])
        self.assertNotEqual('https://github.com/', last_request.url)
        self.assertNotEqual('github.com', last_request.headers['Host'])

    def test_set_multiples_scopes(self):
        self.backend.scopes = ('.*stackoverflow.*', '.*github.*')

        self._make_request('https://stackoverflow.com')
        last_request = self.backend.storage.load_last_request()
        self.assertEqual('https://stackoverflow.com/', last_request.url)
        self.assertEqual('stackoverflow.com', last_request.headers['Host'])

        self._make_request('https://github.com')
        last_request = self.backend.storage.load_last_request()
        self.assertEqual('https://github.com/', last_request.url)
        self.assertEqual('github.com', last_request.headers['Host'])

        self._make_request('https://google.com')
        last_request = self.backend.storage.load_last_request()
        self.assertNotEqual('https://google.com/', last_request.url)
        self.assertNotEqual('google.com', last_request.headers['Host'])

    def test_reset_scopes(self):
        self.backend.scopes = ('.*stackoverflow.*', '.*github.*')
        self.backend.scopes = []

        self._make_request('https://www.stackoverflow.com')
        self.assertTrue(self.backend.storage.load_last_request())

    def test_disable_encoding(self):
        self.backend.options['disable_encoding'] = True
        # Explicitly set the accept-encoding to gzip
        self.backend.modifier.headers = {
            'Accept-Encoding': 'gzip'
        }

        self._make_request('https://www.google.com/')

        requests = self.backend.storage.load_requests()

        # No Content-Encoding header implies 'identity'
        self.assertEqual(
            'identity',
            requests[0].response.headers.get('Content-Encoding', 'identity')
        )

    def test_intercept_request_headers(self):
        def interceptor(request):
            del request.headers['User-Agent']
            request.headers['User-Agent'] = 'Test_User_Agent_String'

        self.backend.request_interceptor = interceptor

        self._make_request('https://www.github.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('Test_User_Agent_String', last_request.headers['User-Agent'])

    def test_intercept_request_params(self):
        def interceptor(request):
            # Update the existing parameters
            request.params = {**request.params, 'foo': 'baz', 'a': 'b'}

        self.backend.request_interceptor = interceptor

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual({'foo': 'baz', 'spam': 'eggs', 'a': 'b'}, last_request.params)

    def test_intercept_request_body(self):
        def interceptor(request):
            data = json.loads(request.body.decode('utf-8'))
            data.update({'foo': 'baz', 'a': 'b'})
            request.body = json.dumps(data).encode('utf-8')

        self.backend.request_interceptor = interceptor

        self._make_request(
            'https://httpbin.org/post',
            method='POST',
            data=b'{"foo": "bar", "spam": "eggs"}'
        )

        last_request = self.backend.storage.load_last_request()

        self.assertEqual({'foo': 'baz', 'spam': 'eggs', 'a': 'b'}, json.loads(last_request.body.decode('utf-8')))

    def test_intercept_response_headers(self):
        def interceptor(request, response):
            del response.headers['Cache-Control']
            response.headers['Cache-Control'] = 'none'

        self.backend.response_interceptor = interceptor

        self._make_request('https://www.github.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual('none', last_request.response.headers['Cache-Control'])

    def test_intercept_response_body(self):
        def interceptor(request, response):
            response.body = b'helloworld'

        self.backend.response_interceptor = interceptor

        self._make_request('https://www.github.com')

        last_request = self.backend.storage.load_last_request()

        self.assertEqual(b'helloworld', last_request.response.body)

    @classmethod
    def setUpClass(cls):
        options = {'backend': os.environ.get('SW_TEST_BACKEND', 'default')}
        cls.backend = backend.create(options=options)
        cls._configure_proxy(*cls.backend.address())

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()

    def tearDown(self):
        del self.backend.modifier.headers
        del self.backend.modifier.params
        del self.backend.modifier.querystring
        del self.backend.modifier.rewrite_rules
        self.backend.scopes = []
        self.backend.request_interceptor = None
        self.backend.response_interceptor = None
        self.backend.storage.clear_requests()
        self.backend.options['disable_encoding'] = False

    @classmethod
    def _configure_proxy(cls, host, port):
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

    def _make_request(self, url, method='GET', data=None):
        request = urllib.request.Request(url, method=method, data=data)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                         '(KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36')
        with urllib.request.urlopen(request, timeout=5) as response:
            html = response.read()

        return html

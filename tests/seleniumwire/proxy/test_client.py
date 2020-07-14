import os
import ssl
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit
from unittest import TestCase

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
        self.assertEqual('GET', request['method'])
        self.assertEqual('https://www.python.org/', request['url'])
        self.assertEqual('identity', request['headers']['Accept-Encoding'])
        self.assertEqual(200, request['response']['status_code'])
        self.assertEqual( 'text/html; charset=utf-8', request['response']['headers']['Content-Type'])

    def test_get_requests_multiple(self):
        self._make_request('https://github.com/')
        self._make_request('https://www.wikipedia.org/')

        requests = self.client.get_requests()

        self.assertEqual(2, len(requests))

    def test_get_last_request(self):
        self._make_request('https://python.org')
        self._make_request('https://www.bbc.co.uk/')

        last_request = self.client.get_last_request()

        self.assertEqual('https://www.bbc.co.uk/', last_request['url'])

    def test_get_last_request_none(self):
        last_request = self.client.get_last_request()

        self.assertIsNone(last_request)

    def test_clear_requests(self):
        self._make_request('https://python.org')
        self._make_request('https://www.wikipedia.org')

        self.client.clear_requests()

        self.assertEqual([], self.client.get_requests())

    def test_find(self):
        self._make_request(
            'https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15')
        self._make_request(
            'https://docs.python.org/3.4/library/http.client.html')
        self._make_request('https://www.google.com')

        self.assertEqual(
            'https://stackoverflow.com/questions/tagged/django?page=2&sort=newest&pagesize=15',
            self.client.find('/questions/tagged/django')['url']
        )
        self.assertEqual(
            'https://docs.python.org/3.4/library/http.client.html',
            self.client.find('/3.4/library/http.client.html')['url']
        )
        self.assertEqual(
            'https://www.google.com/',
            self.client.find('https://www.google.com')['url']
        )

    def test_get_request_body_empty(self):
        self._make_request('https://www.amazon.com')
        last_request = self.client.get_last_request()

        body = self.client.get_request_body(last_request['id'])

        self.assertEqual(b'', body)

    def test_get_response_body(self):
        self._make_request('https://www.wikipedia.org')
        last_request = self.client.get_last_request()

        body = self.client.get_response_body(last_request['id'])

        self.assertIsInstance(body, bytes)
        self.assertIn(b'html', body)

    def test_get_response_body_json(self):
        self._make_request('https://radiopaedia.org/api/v1/countries/current')
        last_request = self.client.get_last_request()

        body = self.client.get_response_body(last_request['id'])

        self.assertIsInstance(body, bytes)

    def test_get_response_body_image(self):
        self._make_request(
            'https://www.python.org/static/img/python-logo@2x.png')
        last_request = self.client.get_last_request()

        body = self.client.get_response_body(last_request['id'])

        self.assertIsInstance(body, bytes)

    def test_get_response_body_empty(self):
        # Redirects to https with empty body
        self._make_request('http://www.python.org')
        redirect_request = self.client.get_requests()[0]

        body = self.client.get_response_body(redirect_request['id'])

        self.assertEqual(b'', body)

    def test_set_header_overrides(self):
        self.client.set_header_overrides({
            'User-Agent': 'Test_User_Agent_String'
        })
        self._make_request('https://www.github.com')

        last_request = self.client.get_last_request()

        self.assertEqual('Test_User_Agent_String', last_request['headers']['User-Agent'])

    def test_set_header_overrides_case_insensitive(self):
        self.client.set_header_overrides({
            'user-agent': 'Test_User_Agent_String'  # Lowercase header name
        })
        self._make_request('https://www.bbc.co.uk')

        last_request = self.client.get_last_request()

        self.assertEqual('Test_User_Agent_String', last_request['headers']['User-Agent'])

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

        self.assertNotEqual(
            'Test_User_Agent_String', last_request['headers']['User-Agent']
        )

    def test_get_header_overrides(self):
        self.client.set_header_overrides({'User-Agent': 'Test_User_Agent_String'})

        self.assertEqual({'User-Agent': 'Test_User_Agent_String'}, self.client.get_header_overrides())

    def test_get_url_match_header_overrides(self):
        self.client.set_header_overrides([['host1', {
            'User-Agent': 'Test_User_Agent_String'
        }], ['host2', {'User-Agent2': 'Test_User_Agent_String'
                       }]])

        self.assertEqual([
            ['host1', {'User-Agent': 'Test_User_Agent_String'}],
            ['host2', {'User-Agent2': 'Test_User_Agent_String'}]
        ], self.client.get_header_overrides())

    def test_get_param_overrides(self):
        self.client.set_param_overrides({'foo': 'bar'})

        self.assertEqual({'foo': 'bar'}, self.client.get_param_overrides())

    def test_set_param_overrides(self):
        self.client.set_param_overrides({'foo': 'baz'})

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.client.get_last_request()

        params = {k: v[0] for k, v in parse_qs(urlsplit(last_request['url']).query).items()}
        self.assertEqual({
            'foo': 'baz',
            'spam': 'eggs'
        }, params)

    def test_set_param_overrides_post(self):
        self.client.set_param_overrides({'foo': 'baz'})

        self._make_request(
            'https://httpbin.org/post',
            method='POST',
            data=b'foo=baz&spam=eggs'
        )

        last_request = self.client.get_last_request()
        body = self.client.get_request_body(last_request['id'])

        qs = parse_qs(body.decode('utf-8'))
        self.assertEqual(2, len(qs))
        self.assertEqual('baz', qs['foo'][0])
        self.assertEqual('eggs', qs['spam'][0])

    def test_set_param_overrides_filters_out_param(self):
        self.client.set_param_overrides({'foo': None})

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.client.get_last_request()

        query = urlsplit(last_request['url']).query
        self.assertEqual('spam=eggs', query)

    def test_clear_param_overrides(self):
        self.client.set_param_overrides({'foo': 'baz'})
        self.client.clear_param_overrides()
        self._make_request('https://www.stackoverflow.com')

        last_request = self.client.get_last_request()

        query = urlsplit(last_request['url']).query
        self.assertEqual('', query)

    def test_get_querystring_overrides(self):
        self.client.set_querystring_overrides('foo=bar')

        self.assertEqual('foo=bar', self.client.get_querystring_overrides())

    def test_set_querystring_overrides(self):
        self.client.set_querystring_overrides('foo=baz')

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.client.get_last_request()

        query = urlsplit(last_request['url'])[3]
        self.assertEqual('foo=baz', query)

    def test_set_querystring_overrides_filters(self):
        self.client.set_querystring_overrides('')  # Empty string to filter a querystring (not None)

        self._make_request('https://httpbin.org/?foo=bar&spam=eggs')

        last_request = self.client.get_last_request()

        query = urlsplit(last_request['url'])[3]
        self.assertEqual('', query)

    def test_clear_querystring_overrides(self):
        self.client.set_querystring_overrides('foo=baz')
        self.client.clear_querystring_overrides()
        self._make_request('https://www.stackoverflow.com')

        last_request = self.client.get_last_request()

        query = urlsplit(last_request['url'])[3]
        self.assertEqual('', query)

    def test_set_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'https://stackoverflow.com(.*)', r'https://github.com\1'),
        ])
        self._make_request('https://stackoverflow.com')

        last_request = self.client.get_last_request()

        self.assertEqual('https://github.com/', last_request['url'])
        self.assertEqual('github.com', last_request['headers']['Host'])

    def test_clear_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'https://stackoverflow.com(.*)', r'https://www.github.com\1'),
        ])
        self.client.clear_rewrite_rules()

        self._make_request('https://www.stackoverflow.com/')

        last_request = self.client.get_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request['url'])
        self.assertEqual('stackoverflow.com', last_request['headers']['Host'])

    def test_get_rewrite_rules(self):
        self.client.set_rewrite_rules([
            (r'http://www.stackoverflow.com(.*)', r'https://www.github.com\1'),
        ])

        self.assertEqual([
            [r'http://www.stackoverflow.com(.*)', r'https://www.github.com\1'],
        ], self.client.get_rewrite_rules())

    def test_set_single_scopes(self):
        self.client.set_scopes('.*stackoverflow.*')

        self._make_request('https://stackoverflow.com')

        last_request = self.client.get_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request['url'])
        self.assertEqual('stackoverflow.com', last_request['headers']['Host'])

        self._make_request('https://github.com')

        last_request = self.client.get_last_request()

        self.assertEqual('https://stackoverflow.com/', last_request['url'])
        self.assertEqual('stackoverflow.com', last_request['headers']['Host'])
        self.assertNotEqual('https://github.com/', last_request['url'])
        self.assertNotEqual('github.com', last_request['headers']['Host'])

    def test_set_multiples_scopes(self):
        self.client.set_scopes(('.*stackoverflow.*', '.*github.*'))

        self._make_request('https://stackoverflow.com')
        last_request = self.client.get_last_request()
        self.assertEqual('https://stackoverflow.com/', last_request['url'])
        self.assertEqual('stackoverflow.com', last_request['headers']['Host'])

        self._make_request('https://github.com')
        last_request = self.client.get_last_request()
        self.assertEqual('https://github.com/', last_request['url'])
        self.assertEqual('github.com', last_request['headers']['Host'])

        self._make_request('https://google.com')
        last_request = self.client.get_last_request()
        self.assertNotEqual('https://google.com/', last_request['url'])
        self.assertNotEqual('google.com', last_request['headers']['Host'])

    def test_reset_scopes(self):
        self.client.set_scopes(('.*stackoverflow.*', '.*github.*'))
        self.client.reset_scopes()

        self._make_request('https://www.stackoverflow.com')
        self.assertTrue(self.client.get_last_request())

    def test_get_scopes(self):
        self.client.set_scopes(('.*stackoverflow.*', '.*github.*'))

        self.assertEqual(['.*stackoverflow.*', '.*github.*'], self.client.get_scopes())

    def test_disable_encoding(self):
        # Explicitly set the accept-encoding to gzip
        self.client.set_header_overrides({
            'Accept-Encoding': 'gzip'
        })

        self._make_request('https://www.google.com/')

        requests = self.client.get_requests()

        # No Content-Encoding header implies 'identity'
        self.assertEqual(
            'identity',
            requests[0]['response']['headers'].get('Content-Encoding', 'identity')
        )

    def setUp(self):
        options = {'backend': os.environ.get('SW_TEST_BACKEND', 'default')}
        if self._testMethodName == 'test_disable_encoding':
            options['disable_encoding'] = True
        self.client = AdminClient()
        host, port = self.client.create_proxy(options=options)
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

    def _make_request(self, url, method='GET', data=None):
        request = urllib.request.Request(url, method=method, data=data)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                         '(KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36')
        with urllib.request.urlopen(request, timeout=5) as response:
            html = response.read()

        return html

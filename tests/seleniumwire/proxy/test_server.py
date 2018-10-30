import os
from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.proxy.server import ProxyHTTPServer


class ProxyHTTPServerTest(TestCase):

    def test_sets_http_proxy_config(self):
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=self.proxy_config, bind_and_activate=False
        )

        self.assertEqual(self.server.proxy_config['http'], ('http', 'username', 'password', 'server:9999'))

    def test_sets_https_proxy_config(self):
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=self.proxy_config, bind_and_activate=False
        )

        self.assertEqual(self.server.proxy_config['https'], ('https', 'username', 'password', 'server:8888'))

    def test_sets_no_proxy_config(self):
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=self.proxy_config, bind_and_activate=False
        )

        self.assertEqual(self.server.proxy_config['no_proxy'], ['localhost', '127.0.0.1'])

    def test_sets_no_http_when_none(self):
        self.proxy_config['http'] = None
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=self.proxy_config, bind_and_activate=False
        )

        self.assertIsNone(self.server.proxy_config['http'])

    def test_sets_no_http_when_not_supplied(self):
        del self.proxy_config['http']
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=self.proxy_config, bind_and_activate=False
        )

        self.assertNotIn('http', self.server.proxy_config)

    def test_sets_nothing(self):
        self.server = ProxyHTTPServer(
            ('127.0.0.1', 8080), Mock(), proxy_config=None, bind_and_activate=False
        )

        self.assertEqual(self.server.proxy_config, {})

    def setUp(self):
        try:
            del os.environ['http_proxy']
            del os.environ['https_proxy']
            del os.environ['no_proxy']
        except KeyError:
            pass

        self.proxy_config = {
            'http': 'http://username:password@server:9999/path',
            'https': 'https://username:password@server:8888/path',
            'no_proxy': 'localhost, 127.0.0.1'
        }

    def tearDown(self):
        self.server.socket.close()

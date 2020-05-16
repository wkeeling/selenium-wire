from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.request import _parse_proxy

from seleniumwire.proxy.proxy2 import (ProxyAwareHTTPConnection, ProxyAwareHTTPSConnection,
                                       create_auth_header)


class ProxyAwareHTTPConnectionTest(TestCase):

    def test_is_proxied(self):
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertTrue(conn.proxied)
        self.assertEqual(conn.host, 'host')

    def test_is_not_proxied_when_no_proxy(self):
        self.config['no_proxy'] += ',example.com'
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertFalse(conn.proxied)
        self.assertEqual(conn.host, 'example.com')

    def test_is_not_proxied_when_no_config(self):
        self.config = {}
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertFalse(conn.proxied)
        self.assertEqual(conn.host, 'example.com')

    @patch('seleniumwire.proxy.proxy2.HTTPConnection.request')
    def test_request_uses_absolute_url(self, mock_request):
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn._create_connection = Mock()
        conn.request('GET', '/foobar')

        mock_request.assert_called_once_with(
            'GET', 'http://example.com/foobar', None,
            headers={'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='}
        )

    @patch('seleniumwire.proxy.proxy2.HTTPConnection.request')
    def test_request_uses_original_url_when_not_proxied(self, mock_request):
        self.config = {}
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn._create_connection = Mock()
        conn.request('GET', '/foobar')

        mock_request.assert_called_once_with(
            'GET', '/foobar', None, headers={}
        )

    def setUp(self):
        self.config = {
            'http': _parse_proxy('http://username:password@host:3128'),
            'https': _parse_proxy('https://username:password@host:3128'),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }


class ProxyAwareHTTPSConnectionTest(TestCase):

    def test_is_proxied(self):
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertTrue(conn.proxied)
        self.assertEqual(conn.host, 'host')

    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.set_tunnel')
    def test_set_tunnel_is_called(self, mock_set_tunnel):
        ProxyAwareHTTPSConnection(self.config, 'example.com')

        mock_set_tunnel.assert_called_once_with(
            'example.com', headers={'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='}
        )

    def test_is_not_proxied_when_no_proxy(self):
        self.config['no_proxy'] += ',example.com'
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertFalse(conn.proxied)
        self.assertEqual(conn.host, 'example.com')

    def test_is_not_proxied_when_no_config(self):
        self.config = {}
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertFalse(conn.proxied)
        self.assertEqual(conn.host, 'example.com')

    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.set_tunnel')
    def test_set_tunnel_is_not_called(self, mock_set_tunnel):
        self.config = {}
        ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertEqual(mock_set_tunnel.call_count, 0)

    def setUp(self):
        self.config = {
            'http': _parse_proxy('http://username:password@host:3128'),
            'https': _parse_proxy('https://username:password@host:3128'),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }


class ProxyAuthHeadersTest(TestCase):

    def test_create_headers(self):
        username = 'username'
        password = 'password'
        custom_proxy_authorization = None

        headers = create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='})

    def test_does_not_create_headers_when_missing_username(self):
        username = None
        password = 'password'
        custom_proxy_authorization = None

        headers = create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {})

    def test_does_not_create_headers_when_missing_password(self):
        username = 'username'
        password = None
        custom_proxy_authorization = None

        headers = create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {})

    def test_create_headers_when_provide_custom_proxy_authorization(self):
        username = None
        password = None
        custom_proxy_authorization = 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='

        headers = create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='})

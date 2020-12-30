import socket
from collections import namedtuple
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.request import _parse_proxy

from seleniumwire.proxy import socks
from seleniumwire.proxy.proxy2 import ProxyAwareHTTPConnection, ProxyAwareHTTPSConnection, _create_auth_header


class ProxyAwareHTTPConnectionTest(TestCase):

    def setUp(self):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'http': conf(*_parse_proxy('http://username:password@host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }

    def test_use_proxy(self):
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertTrue(conn.use_proxy)
        self.assertEqual(conn.host, 'host')

    def test_is_not_proxied_when_no_proxy(self):
        self.config['no_proxy'] += ',example.com'
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertFalse(conn.use_proxy)
        self.assertEqual(conn.host, 'example.com')

    def test_is_not_proxied_when_no_config(self):
        self.config = {}
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        self.assertFalse(conn.use_proxy)
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

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_does_not_use_socks_proxy(self, mock_socks):
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn._create_connection = Mock()
        conn.connect()

        assert mock_socks._create_connection.call_count == 0

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_socks5_proxy(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'http': conf(*_parse_proxy('socks5://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS5 = socks.PROXY_TYPE_SOCKS5

        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 80),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS5,
            'socks_host',
            3128,
            False,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_remote_dns(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'http': conf(*_parse_proxy('socks5h://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS5 = socks.PROXY_TYPE_SOCKS5

        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 80),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS5,
            'socks_host',
            3128,
            True,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_socks4_proxy(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'http': conf(*_parse_proxy('socks4://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS4 = socks.PROXY_TYPE_SOCKS4

        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 80),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS4,
            'socks_host',
            3128,
            False,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_raises_exception_when_invalid_socks_scheme(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'http': conf(*_parse_proxy('socks6://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }

        conn = ProxyAwareHTTPConnection(self.config, 'example.com')

        with self.assertRaises(TypeError):
            conn.connect()


class ProxyAwareHTTPSConnectionTest(TestCase):

    def setUp(self):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('https://username:password@host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }

    def test_use_proxy(self):
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertTrue(conn.use_proxy)
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

        self.assertFalse(conn.use_proxy)
        self.assertEqual(conn.host, 'example.com')

    def test_is_not_proxied_when_no_config(self):
        self.config = {}
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertFalse(conn.use_proxy)
        self.assertEqual(conn.host, 'example.com')

    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.set_tunnel')
    def test_set_tunnel_is_not_called(self, mock_set_tunnel):
        self.config = {}
        ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertEqual(mock_set_tunnel.call_count, 0)

    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.set_tunnel')
    def test_set_tunnel_is_not_called_when_socks(self, mock_set_tunnel):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('socks5://username:password@host:3128'))
        }
        ProxyAwareHTTPSConnection(self.config, 'example.com')

        self.assertEqual(mock_set_tunnel.call_count, 0)

    @patch('seleniumwire.proxy.proxy2.socks')
    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.connect')
    @patch('seleniumwire.proxy.proxy2.HTTPSConnection.set_tunnel')
    def test_connect_does_not_use_socks_proxy(self, mock_set_tunnel, mock_connect, mock_socks):
        conn = ProxyAwareHTTPSConnection(self.config, 'example.com')
        conn.connect()

        assert mock_socks._create_connection.call_count == 0
        mock_connect.assert_called_once_with()

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_socks5_proxy(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('socks5://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS5 = socks.PROXY_TYPE_SOCKS5

        conn = ProxyAwareHTTPSConnection(self.config, 'example.com', context=Mock())
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 443),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS5,
            'socks_host',
            3128,
            False,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_remote_dns(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('socks5h://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS5 = socks.PROXY_TYPE_SOCKS5

        conn = ProxyAwareHTTPSConnection(self.config, 'example.com', context=Mock())
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 443),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS5,
            'socks_host',
            3128,
            True,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_connect_uses_socks4_proxy(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('socks4://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }
        mock_socks.PROXY_TYPE_SOCKS4 = socks.PROXY_TYPE_SOCKS4

        conn = ProxyAwareHTTPSConnection(self.config, 'example.com', context=Mock())
        conn.connect()

        mock_socks.create_connection.assert_called_once_with(
            ('example.com', 443),
            socket._GLOBAL_DEFAULT_TIMEOUT,
            None,
            socks.PROXY_TYPE_SOCKS4,
            'socks_host',
            3128,
            False,
            'socks_user',
            'socks_pass',
            ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
        )

    @patch('seleniumwire.proxy.proxy2.socks')
    def test_raises_exception_when_invalid_socks_scheme(self, mock_socks):
        conf = namedtuple('ProxyConf', 'scheme username password hostport')
        self.config = {
            'https': conf(*_parse_proxy('socks6://socks_user:socks_pass@socks_host:3128')),
            'no_proxy': 'localhost,127.0.0.1,dev_server:8080'
        }

        conn = ProxyAwareHTTPSConnection(self.config, 'example.com', context=Mock())

        with self.assertRaises(TypeError):
            conn.connect()


class ProxyAuthHeaderTest(TestCase):

    def test_create_header(self):
        username = 'username'
        password = 'password'
        custom_proxy_authorization = None

        headers = _create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='})

    def test_create_header_missing_username(self):
        username = None
        password = 'password'
        custom_proxy_authorization = None

        headers = _create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {})

    def test_create_header_missing_password(self):
        username = 'username'
        password = None
        custom_proxy_authorization = None

        headers = _create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {})

    def test_create_header_custom_proxy_authorization(self):
        username = None
        password = None
        custom_proxy_authorization = 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='

        headers = _create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='})

    def test_create_header_quoted(self):
        username = 'username%3b'
        password = 'password%3b'
        custom_proxy_authorization = None

        headers = _create_auth_header(username, password, custom_proxy_authorization)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU7OnBhc3N3b3JkOw=='})

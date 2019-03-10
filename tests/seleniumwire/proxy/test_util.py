from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.request import _parse_proxy

from seleniumwire.proxy.util import (ProxyAwareHTTPConnection, ProxyAwareHTTPSConnection,
                                     RequestModifier, proxy_auth_headers)


class RequestModifierTest(TestCase):

    def setUp(self):
        self.modifier = RequestModifier()

    def test_override_header(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_override_header_case_insensitive(self):
        self.modifier.headers = {
            'user-agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_add_new_header(self):
        self.modifier.headers = {
            'New-Header': 'Some-Value'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['New-Header'], 'Some-Value')

    def test_filter_out_header(self):
        self.modifier.headers = {
            'User-Agent': None
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('User-Agent', mock_request.headers)

    def test_clear_header_overrides(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        del self.modifier.headers
        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'],
                         'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0')

    def test_get_header_overrides(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }

        self.assertEqual(self.modifier.headers, {
            'User-Agent': 'Test_User_Agent_String'
        })

    def test_rewrite_url(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.path, 'https://prod2.server.com/some/path/12345/foo/')

    def test_rewrite_url_first_match(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/bar/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.path, 'https://prod2.server.com/some/path/12345/foo/')

    def test_does_not_rewrite_url(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()
        mock_request.path = 'https://prod3.server.com/some/path/12345'

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.path, 'https://prod3.server.com/some/path/12345')

    def test_rewrite_url_updates_host_header(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()
        mock_request.headers['Host'] = 'prod1.server.com'

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['Host'], 'prod2.server.com')

    def test_rewrite_url_does_not_update_host_header(self):
        """Should not update the Host header if it does not already exist."""
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('Host', mock_request.headers)

    def _create_mock_request(self):
        mock_request = Mock()
        mock_request.path = 'https://prod1.server.com/some/path/12345'
        mock_request.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0'
        }
        return mock_request


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

    @patch('seleniumwire.proxy.util.HTTPConnection.request')
    def test_request_uses_absolute_url(self, mock_request):
        conn = ProxyAwareHTTPConnection(self.config, 'example.com')
        conn._create_connection = Mock()
        conn.request('GET', '/foobar')

        mock_request.assert_called_once_with(
            'GET', 'http://example.com/foobar', None,
            headers={'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='}
        )

    @patch('seleniumwire.proxy.util.HTTPConnection.request')
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

    @patch('seleniumwire.proxy.util.HTTPSConnection.set_tunnel')
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

    @patch('seleniumwire.proxy.util.HTTPSConnection.set_tunnel')
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

        headers = proxy_auth_headers(username, password)

        self.assertEqual(headers, {'Proxy-Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='})

    def test_does_not_create_headers_when_missing_username(self):
        username = None
        password = 'password'

        headers = proxy_auth_headers(username, password)

        self.assertEqual(headers, {})

    def test_does_not_create_headers_when_missing_password(self):
        username = 'username'
        password = None

        headers = proxy_auth_headers(username, password)

        self.assertEqual(headers, {})

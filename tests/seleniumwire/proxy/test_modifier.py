from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.proxy.modifier import RequestModifier


class RequestModifierTest(TestCase):

    def setUp(self):
        self.modifier = RequestModifier()

    def test_override_header(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Test_User_Agent_String', mock_request.headers['User-Agent']
        )

    def test_override_header_with_single_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Test_User_Agent_String', mock_request.headers['User-Agent']
        )

    def test_override_multiple_headers_with_single_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String',
                                      'New-Header': 'HeaderValue'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Test_User_Agent_String', mock_request.headers['User-Agent']
        )
        self.assertEqual(
            'HeaderValue', mock_request.headers['New-Header']
        )

    def test_override_headers_with_multiple_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String',
                                      'New-Header': 'HeaderValue'}),
            (".*prod2.server.com.*", {'User-Agent2': 'Test_User_Agent_String2',
                                      'New-Header2': 'HeaderValue'})
        ]
        url = "https://prod1.server.com/some/path/12345"
        mock_request = self._create_mock_request(url)

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Test_User_Agent_String', mock_request.headers['User-Agent']
        )
        self.assertEqual(url, mock_request.url)
        self.assertFalse('User-Agent2' in mock_request.headers
                         or 'New-Header2' in mock_request.headers)

        url = "https://prod2.server.com/some/path/12345"
        mock_request = self._create_mock_request(url)

        self.modifier.modify(mock_request)
        self.assertEqual(
            'HeaderValue', mock_request.headers['New-Header2']
        )
        self.assertEqual(url, mock_request.url)
        self.assertFalse('New-Header' in mock_request.headers)

    def test_override_header_with_url_not_matching(self):
        self.modifier.headers = [
            (".*prod.server.com.*", {'User-Agent': 'Test_User_Agent_String'})
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 '
            'Firefox/10.0',
            mock_request.headers['User-Agent'],
        )

    def test_override_header_case_insensitive(self):
        self.modifier.headers = {
            'user-agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'Test_User_Agent_String', mock_request.headers['User-Agent']
        )

    def test_add_new_header(self):
        self.modifier.headers = {
            'New-Header': 'Some-Value'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual('Some-Value', mock_request.headers['New-Header'])

    def test_filter_out_header(self):
        self.modifier.headers = {
            'User-Agent': None
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('User-Agent', mock_request.headers)

    def test_filter_out_non_existent_header(self):
        self.modifier.headers = {
            'Host': None  # Does not exist in the request
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('Host', mock_request.headers)

    def test_clear_header_overrides(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        del self.modifier.headers
        self.modifier.modify(mock_request)

        self.assertEqual('Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/'
                         '20100101 Firefox/10.0',
                         mock_request.headers['User-Agent'])

    def test_get_header_overrides(self):
        self.modifier.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }

        self.assertEqual(
            {'User-Agent': 'Test_User_Agent_String'}, self.modifier.headers
        )

    def test_override_param_qs(self):
        self.modifier.params = {
            'foo': 'baz'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz&spam=eggs',
            mock_request.url
        )

    def test_override_param_body(self):
        self.modifier.params = {
            'foo': 'bazz'
        }
        mock_request = self._create_mock_request(
            url='https://prod1.server.com/some/path/12345',
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            body=b'foo=bar&spam=eggs'
        )

        self.modifier.modify(mock_request)

        self.assertEqual(b'foo=bazz&spam=eggs', mock_request.body)
        self.assertEqual(18, mock_request.headers['Content-Length'])

    def test_override_multiple_params(self):
        self.modifier.params = {
            'foo': 'baz',
            'spam': 'ham'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz&spam=ham',
            mock_request.url
        )

    def test_override_param_multiple_values(self):
        self.modifier.params = {
            'foo': ['a', 'b']
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=a&foo=b&spam=eggs',
            mock_request.url
        )

    def test_override_param_body_no_content_type(self):
        self.modifier.params = {
            'foo': 'baz'
        }
        mock_request = self._create_mock_request(
            url='https://prod1.server.com/some/path/12345?foo=baz&spam=eggs',
            method='POST',
            body=b'foo=bar&spam=eggs'
        )

        self.modifier.modify(mock_request)

        self.assertEqual(b'foo=bar&spam=eggs', mock_request.body)

    def test_override_param_with_single_url_matching(self):
        self.modifier.params = [
            (".*prod1.server.com.*", {'foo': 'baz'})
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz&spam=eggs',
            mock_request.url
        )

    def test_override_multiple_params_with_single_url_matching(self):
        self.modifier.params = [
            (".*prod1.server.com.*", {'foo': 'baz', 'spam': 'ham'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz&spam=ham',
            mock_request.url
        )

    def test_override_params_with_multiple_url_matching(self):
        self.modifier.params = [
            (".*prod1.server.com.*", {'foo': 'baz', 'spam': 'ham'}),
            (".*prod2.server.com.*", {'foo': 'baz2', 'spam': 'ham2'})
        ]

        # Modify a request that matches the first pattern
        url = 'https://prod1.server.com/some/path/12345?foo=bar&spam=eggs'
        mock_request = self._create_mock_request(url)

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz&spam=ham',
            mock_request.url
        )

        # Modify a request that matches the second pattern
        url = 'https://prod2.server.com/some/path/12345?foo=bar&spam=eggs'
        mock_request = self._create_mock_request(url)

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod2.server.com/some/path/12345?foo=baz2&spam=ham2',
            mock_request.url
        )

    def test_override_param_with_url_not_matching(self):
        self.modifier.params = [
            (".*prod.server.com.*", {'foo': 'baz'})
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=bar&spam=eggs',
            mock_request.url
        )

    def test_add_new_param_qs(self):
        self.modifier.params = {
            'foo': 'baz'
        }
        mock_request = self._create_mock_request('https://prod1.server.com/some/path/12345?spam=eggs')

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?spam=eggs&foo=baz',
            mock_request.url
        )

    def test_add_new_param_body(self):
        self.modifier.params = {
            'foo': 'bazz'
        }
        mock_request = self._create_mock_request(
            url='https://prod1.server.com/some/path/12345',
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            body=b'spam=eggs'
        )

        self.modifier.modify(mock_request)

        self.assertEqual(b'spam=eggs&foo=bazz', mock_request.body)
        self.assertEqual(18, mock_request.headers['Content-Length'])

    def test_add_param_no_qs(self):
        self.modifier.params = {
            'foo': 'baz'
        }
        mock_request = self._create_mock_request('https://prod1.server.com/some/path/12345')

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=baz',
            mock_request.url
        )

    def test_add_param_no_body(self):
        self.modifier.params = {
            'foo': 'bazz'
        }
        mock_request = self._create_mock_request(
            url='https://prod1.server.com/some/path/12345',
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            body=b''
        )

        self.modifier.modify(mock_request)

        self.assertEqual(b'foo=bazz', mock_request.body)
        self.assertEqual(8, mock_request.headers['Content-Length'])

    def test_filter_out_param_qs(self):
        self.modifier.params = {
            'foo': None
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?spam=eggs',
            mock_request.url
        )

    def test_filter_out_param_body(self):
        self.modifier.params = {
            'foo': None
        }
        mock_request = self._create_mock_request(
            url='https://prod1.server.com/some/path/12345',
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            body=b'foo=bar&spam=eggs'
        )

        self.modifier.modify(mock_request)

        self.assertEqual(b'spam=eggs', mock_request.body)
        self.assertEqual(9, mock_request.headers['Content-Length'])

    def test_filter_out_non_existent_param(self):
        self.modifier.params = {
            'hello': None  # Does not exist in the request
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=bar&spam=eggs',
            mock_request.url
        )

    def test_clear_param_overrides(self):
        self.modifier.params = {
            'foo': 'baz',
            'spam': 'ham'
        }
        mock_request = self._create_mock_request()

        del self.modifier.params
        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod1.server.com/some/path/12345?foo=bar&spam=eggs',
            mock_request.url
        )

    def test_get_param_overrides(self):
        self.modifier.params = {
            'foo': 'baz',
            'spam': 'ham'
        }

        self.assertEqual(
            {'foo': 'baz', 'spam': 'ham'}, self.modifier.params
        )

    def test_rewrite_url(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod2.server.com/some/path/12345/foo/', mock_request.url
        )

    def test_rewrite_url_first_match(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/bar/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod2.server.com/some/path/12345/foo/', mock_request.url
        )

    def test_does_not_rewrite_url(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()
        mock_request.url = 'https://prod3.server.com/some/path/12345'

        self.modifier.modify(mock_request)

        self.assertEqual(
            'https://prod3.server.com/some/path/12345', mock_request.url
        )

    def test_rewrite_url_updates_host_header(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()
        mock_request.headers['Host'] = 'prod1.server.com'

        self.modifier.modify(mock_request)

        self.assertEqual('prod2.server.com', mock_request.headers['Host'])

    def test_rewrite_url_does_not_update_host_header(self):
        """Should not update the Host header if it does not already exist."""
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('Host', mock_request.headers)

    def _create_mock_request(self, url="https://prod1.server.com/some/path/12345?foo=bar&spam=eggs",
                             method='GET', headers=None, body=b''):
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0'
            }

        mock_request = Mock()
        mock_request.url = url
        mock_request.method = method
        mock_request.body = body
        mock_request.headers = headers
        return mock_request

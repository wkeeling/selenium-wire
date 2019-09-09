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
            mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_override_header_with_single_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_override_multiple_headers_with_single_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String',
                                      'New-Header': 'HeaderValue'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            mock_request.headers['User-Agent'], 'Test_User_Agent_String')
        self.assertEqual(
            mock_request.headers['New-Header'], 'HeaderValue')

    def test_override_headers_with_multiple_url_matching(self):
        self.modifier.headers = [
            (".*prod1.server.com.*", {'User-Agent': 'Test_User_Agent_String',
                                      'New-Header': 'HeaderValue'}),
            (".*prod2.server.com.*", {'User-Agent2': 'Test_User_Agent_String2',
                                      'New-Header2': 'HeaderValue'})]
        path = "https://prod1.server.com/some/path/12345"
        mock_request = self._create_mock_request(path)

        self.modifier.modify(mock_request)

        self.assertEqual(
            mock_request.headers['User-Agent'], 'Test_User_Agent_String')
        self.assertEqual(mock_request.path, path)
        self.assertFalse('User-Agent2' in mock_request.headers
                         or 'New-Header2' in mock_request.headers)

        path = "https://prod2.server.com/some/path/12345"
        mock_request = self._create_mock_request(path)

        self.modifier.modify(mock_request)
        self.assertEqual(
            mock_request.headers['New-Header2'], 'HeaderValue')
        self.assertEqual(mock_request.path, path)
        self.assertFalse('New-Header' in mock_request.headers)

    def test_not_override_header_withurl_matching(self):
        self.modifier.headers = [
            (".*prod.server.com.*", {'User-Agent': 'Test_User_Agent_String'})]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            mock_request.headers['User-Agent'],
            'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 '
            'Firefox/10.0')

    def test_override_header_case_insensitive(self):
        self.modifier.headers = {
            'user-agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(
            mock_request.headers['User-Agent'], 'Test_User_Agent_String')

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
                         'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/'
                         '20100101 Firefox/10.0')

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

        self.assertEqual(mock_request.path,
                         'https://prod2.server.com/some/path/12345/foo/')

    def test_rewrite_url_first_match(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/bar/'),
        ]
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.path,
                         'https://prod2.server.com/some/path/12345/foo/')

    def test_does_not_rewrite_url(self):
        self.modifier.rewrite_rules = [
            (r'(https?://)prod1.server.com(.*)', r'\1prod2.server.com\2/foo/'),
        ]
        mock_request = self._create_mock_request()
        mock_request.path = 'https://prod3.server.com/some/path/12345'

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.path,
                         'https://prod3.server.com/some/path/12345')

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

    def _create_mock_request(self,
                             path="https://prod1.server.com/some/path/12345"):
        mock_request = Mock()
        mock_request.path = path
        mock_request.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/'
            '20100101 Firefox/10.0'
        }
        return mock_request

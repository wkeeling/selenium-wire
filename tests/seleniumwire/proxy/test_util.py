from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.proxy.util import RequestModifier


class RequestModifierTest(TestCase):

    def setUp(self):
        self.modify_request = RequestModifier()

    def test_override_header(self):
        self.modify_request.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modify_request(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_override_header_case_insensitive(self):
        self.modify_request.headers = {
            'user-agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        self.modify_request(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_filter_out_header(self):
        self.modify_request.headers = {
            'User-Agent': None
        }
        mock_request = self._create_mock_request()

        self.modify_request(mock_request)

        self.assertNotIn('User-Agent', mock_request.headers)

    def test_clear_header_overrides(self):
        self.modify_request.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }
        mock_request = self._create_mock_request()

        del self.modify_request.headers
        self.modify_request(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'],
                         'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0')

    def test_get_header_overrides(self):
        self.modify_request.headers = {
            'User-Agent': 'Test_User_Agent_String'
        }

        self.assertEqual(self.modify_request.headers, {
            'User-Agent': 'Test_User_Agent_String'
        })

    def test_rewrite_url(self):
        self.fail('Implement')

    def test_rewrite_url_mangled(self):
        self.fail('Implement')

    def test_rewrite_url_updates_host_header(self):
        self.fail('Implement')

    def test_rewrite_url_does_not_update_host_header(self):
        """HTTPS requests should not update host (hostname and port cannot be changed)."""
        self.fail('Implement')

    def _create_mock_request(self):
        mock_request = Mock()
        mock_request.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0'
        }
        return mock_request

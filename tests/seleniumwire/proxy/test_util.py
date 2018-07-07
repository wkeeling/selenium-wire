from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.proxy.util import RequestModifier


class RequestModifierTest(TestCase):

    def setUp(self):
        self.modifier = RequestModifier()

    def test_override_header(self):
        self.modifier.set_headers({
            'User-Agent': 'Test_User_Agent_String'
        })
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_override_header_case_insensitive(self):
        self.modifier.set_headers({
            'user-agent': 'Test_User_Agent_String'
        })
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'], 'Test_User_Agent_String')

    def test_filter_out_header(self):
        self.modifier.set_headers({
            'User-Agent': None
        })
        mock_request = self._create_mock_request()

        self.modifier.modify(mock_request)

        self.assertNotIn('User-Agent', mock_request.headers)

    def test_clear_header_overrides(self):
        self.modifier.set_headers({
            'User-Agent': 'Test_User_Agent_String'
        })
        mock_request = self._create_mock_request()

        self.modifier.clear_headers()
        self.modifier.modify(mock_request)

        self.assertEqual(mock_request.headers['User-Agent'],
                         'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0')

    def _create_mock_request(self):
        mock_request = Mock()
        mock_request.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0'
        }
        return mock_request

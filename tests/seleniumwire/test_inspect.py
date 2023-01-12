from collections.abc import Iterator
from unittest import TestCase
from unittest.mock import Mock, patch

from seleniumwire.inspect import InspectRequestsMixin, TimeoutException


class Driver(InspectRequestsMixin):
    def __init__(self, backend):
        self.backend = backend


class InspectRequestsMixinTest(TestCase):
    def setUp(self):
        self.mock_backend = Mock()
        self.driver = Driver(self.mock_backend)

    def test_get_requests(self):
        self.mock_backend.storage.load_requests.return_value = [Mock()]

        requests = self.driver.requests

        self.mock_backend.storage.load_requests.assert_called_once_with()
        self.assertEqual(1, len(requests))

    def test_set_requests(self):
        with self.assertRaises(AttributeError):
            self.driver.requests = [Mock()]

    def test_delete_requests(self):
        del self.driver.requests

        self.mock_backend.storage.clear_requests.assert_called_once_with()

    def test_delete_request(self):
        self.driver.delete_request("foo")

        self.mock_backend.storage.clear_request_by_id.assert_called_once_with("foo")

    def test_iter_requests(self):
        self.mock_backend.storage.iter_requests.return_value = iter([Mock()])

        self.assertIsInstance(self.driver.iter_requests(), Iterator)

    def test_last_request(self):
        self.mock_backend.storage.load_last_request.return_value = Mock()

        last_request = self.driver.last_request

        self.assertIsNotNone(last_request)
        self.mock_backend.storage.load_last_request.assert_called_once_with()

    def test_last_request_none(self):
        self.mock_backend.storage.load_last_request.return_value = None

        last_request = self.driver.last_request

        self.assertIsNone(last_request)
        self.mock_backend.storage.load_last_request.assert_called_once_with()

    def test_wait_for_request(self):
        self.mock_backend.storage.find.return_value = Mock()

        request = self.driver.wait_for_request('/some/path')

        self.assertIsNotNone(request)
        self.mock_backend.storage.find.assert_called_once_with('/some/path')

    def test_wait_for_request_timeout(self):
        self.mock_backend.storage.find.return_value = None

        with self.assertRaises(TimeoutException):
            self.driver.wait_for_request('/some/path', timeout=1)

        self.assertTrue(self.mock_backend.storage.find.call_count > 0)
        self.assertTrue(self.mock_backend.storage.find.call_count <= 5)

    @patch('seleniumwire.inspect.har')
    def test_har(self, mock_har):
        self.mock_backend.storage.load_har_entries.return_value = [
            'test_entry1',
            'test_entry2',
        ]
        mock_har.generate_har.return_value = 'test_har'

        har = self.driver.har

        self.assertEqual('test_har', har)
        self.mock_backend.storage.load_har_entries.assert_called_once_with()
        mock_har.generate_har.assert_called_once_with(
            [
                'test_entry1',
                'test_entry2',
            ]
        )

    def test_set_header_overrides(self):
        header_overrides = {'User-Agent': 'Test_User_Agent_String', 'Accept-Encoding': None}

        self.driver.header_overrides = header_overrides

        self.assertEqual(header_overrides, self.mock_backend.modifier.headers)

    def test_set_header_overrides_non_str(self):
        header_overrides = {'MyHeader': 99}

        with self.assertRaises(AssertionError):
            self.driver.header_overrides = header_overrides

    def test_delete_header_overrides(self):
        self.mock_backend.modifier.headers = {'User-Agent': 'Test_User_Agent_String', 'Accept-Encoding': None}

        del self.driver.header_overrides

        self.assertFalse(hasattr(self.mock_backend.modifier, 'headers'))

    def test_get_header_overrides(self):
        header_overrides = {'User-Agent': 'Test_User_Agent_String', 'Accept-Encoding': None}
        self.mock_backend.modifier.headers = header_overrides

        self.assertEqual(header_overrides, self.driver.header_overrides)

    def test_set_param_overrides(self):
        param_overrides = {'foo': 'bar'}

        self.driver.param_overrides = param_overrides

        self.assertEqual(param_overrides, self.mock_backend.modifier.params)

    def test_delete_param_overrides(self):
        self.mock_backend.modifier.params = {'foo': 'bar'}

        del self.driver.param_overrides

        self.assertFalse(hasattr(self.mock_backend.modifier, 'params'))

    def test_get_param_overrides(self):
        param_overrides = {'foo': 'bar'}

        self.mock_backend.modifier.params = param_overrides

        self.assertEqual(param_overrides, self.driver.param_overrides)

    def test_set_querystring_overrides(self):
        querystring_overrides = 'foo=bar&hello=world'

        self.driver.querystring_overrides = querystring_overrides

        self.assertEqual(querystring_overrides, self.mock_backend.modifier.querystring)

    def test_delete_querystring_overrides(self):
        self.mock_backend.modifier.querystring = 'foo=bar&hello=world'

        del self.driver.querystring_overrides

        self.assertFalse(hasattr(self.mock_backend.modifier, 'querystring'))

    def test_get_querystring_overrides(self):
        querystring_overrides = 'foo=bar&hello=world'

        self.mock_backend.modifier.querystring = querystring_overrides

        self.assertEqual(querystring_overrides, self.driver.querystring_overrides)

    def test_set_rewrite_rules(self):
        rewrite_rules = [
            ('http://somewhere.com/', 'https://www.somewhere.com'),
            ('http://otherplace.com/', 'http://otherplace.com/api/'),
        ]

        self.driver.rewrite_rules = rewrite_rules

        self.assertEqual(rewrite_rules, self.mock_backend.modifier.rewrite_rules)

    def test_delete_rewrite_rules(self):
        self.mock_backend.modifier.rewrite_rules = [
            ('http://somewhere.com/', 'https://www.somewhere.com'),
            ('http://otherplace.com/', 'http://otherplace.com/api/'),
        ]

        del self.driver.rewrite_rules

        self.assertFalse(hasattr(self.mock_backend.modifier, 'rewrite_rules'))

    def test_get_rewrite_rules(self):
        rewrite_rules = [
            ('http://somewhere.com/', 'https://www.somewhere.com'),
            ('http://otherplace.com/', 'http://otherplace.com/api/'),
        ]

        self.mock_backend.modifier.rewrite_rules = rewrite_rules

        self.assertEqual(rewrite_rules, self.driver.rewrite_rules)

    def test_set_scopes(self):
        scopes = ['.*stackoverflow.*', '.*github.*']

        self.driver.scopes = scopes

        self.assertEqual(scopes, self.mock_backend.scopes)

    def test_delete_scopes(self):
        self.mock_backend.scopes = ['.*stackoverflow.*', '.*github.*']

        del self.driver.scopes

        self.assertEqual([], self.mock_backend.scopes)

    def test_get_scopes(self):
        scopes = ['.*stackoverflow.*', '.*github.*']

        self.mock_backend.scopes = scopes

        self.assertEqual(scopes, self.driver.scopes)

    def test_set_request_interceptor(self):
        def interceptor(r):
            pass

        self.driver.request_interceptor = interceptor

        self.assertEqual(interceptor, self.mock_backend.request_interceptor)

    def test_delete_request_interceptor(self):
        def interceptor(r):
            pass

        self.mock_backend.request_interceptor = interceptor

        del self.driver.request_interceptor

        self.assertIsNone(self.mock_backend.request_interceptor)

    def test_get_request_interceptor(self):
        def interceptor(r):
            pass

        self.mock_backend.request_interceptor = interceptor

        self.assertEqual(interceptor, self.driver.request_interceptor)

    def test_set_response_interceptor(self):
        def interceptor(req, res):
            pass

        self.driver.response_interceptor = interceptor

        self.assertEqual(interceptor, self.mock_backend.response_interceptor)

    def test_set_response_interceptor_invalid_signature(self):
        def interceptor(res):
            pass

        with self.assertRaises(RuntimeError):
            self.driver.response_interceptor = interceptor

    def test_delete_response_interceptor(self):
        def interceptor(req, res):
            pass

        self.mock_backend.response_interceptor = interceptor

        del self.driver.response_interceptor

        self.assertIsNone(self.mock_backend.response_interceptor)

    def test_get_response_interceptor(self):
        def interceptor(req, res):
            pass

        self.mock_backend.response_interceptor = interceptor

        self.assertEqual(interceptor, self.driver.response_interceptor)

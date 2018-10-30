from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.proxy.handler import CaptureRequestHandler


class CaptureRequestHandlerTest(TestCase):

    def test_request_modifier_called(self):
        self.handler.request_handler(self.handler, self.body)

        self.mock_modifier.modify.assert_called_once_with(self.handler)

    def test_save_request_called(self):
        self.handler.request_handler(self.handler, self.body)

        self.mock_storage.save_request.assert_called_once_with(self.handler, self.body)

    def test_ignores_options_method_by_default(self):
        self.handler.command = 'OPTIONS'
        self.handler.request_handler(self.handler, self.body)

        self.assertFalse(self.mock_modifier.modify.called)
        self.assertFalse(self.mock_storage.save_request.called)

    def test_ignores_get_method(self):
        self.handler.server.options = {'ignore_http_methods': ['OPTIONS', 'GET']}
        self.handler.request_handler(self.handler, self.body)

        self.assertFalse(self.mock_modifier.modify.called)
        self.assertFalse(self.mock_storage.save_request.called)

    def test_ignores_no_method(self):
        self.handler.command = 'OPTIONS'
        self.handler.server.options = {'ignore_http_methods': []}
        self.handler.request_handler(self.handler, self.body)

        self.mock_storage.save_request.assert_called_once_with(self.handler, self.body)

    def test_save_response_called(self):
        res, res_body = Mock(), Mock()
        self.handler.response_handler(self.handler, self.body, res, res_body)

        self.mock_storage.save_response.assert_called_once_with('12345', res, res_body)

    def test_ignores_response(self):
        res, res_body = Mock(), Mock()
        delattr(self.handler, 'id')
        self.handler.response_handler(self.handler, self.body, res, res_body)

        self.assertFalse(self.mock_storage.save_response.called)

    def setUp(self):
        CaptureRequestHandler.__init__ = Mock(return_value=None)
        self.mock_modifier, self.mock_storage = Mock(), Mock()
        self.handler = CaptureRequestHandler()
        self.handler.server = Mock()
        self.handler.id = '12345'
        self.handler.server.modifier = self.mock_modifier
        self.handler.server.storage = self.mock_storage
        self.handler.server.options = {}
        self.handler.path = 'https://www.google.com/foo/bar?x=y'
        self.handler.command = 'GET'
        self.body = b'hello world'

from unittest import TestCase
from unittest.mock import call, Mock

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
        self.body = None


class AdminMixinTest(TestCase):

    def test_get_requests(self):
        self.handler.path = 'http://seleniumwire/requests'
        self.mock_storage.load_requests.return_value = [
            {'id': '12345'},
            {'id': '67890'},
        ]

        self.handler.admin_handler()

        self.mock_storage.load_requests.assert_called_once()
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 34)],
            body=b'[{"id": "12345"}, {"id": "67890"}]'
        )

    def test_delete_requests(self):
        self.handler.path = 'http://seleniumwire/requests'
        self.handler.command = 'DELETE'

        self.handler.admin_handler()

        self.mock_storage.clear_requests.assert_called_once()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_last_request(self):
        self.handler.path = 'http://seleniumwire/last_request'
        self.mock_storage.load_last_request.return_value = {'id': '12345'}

        self.handler.admin_handler()

        self.mock_storage.load_last_request.assert_called_once()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 15)],
            body=b'{"id": "12345"}'
        )

    def test_get_request_body(self):
        self.handler.path = 'http://seleniumwire/request_body?request_id=12345'
        self.mock_storage.load_request_body.return_value = b'bodycontent'

        self.handler.admin_handler()

        self.mock_storage.load_request_body.assert_called_once_with('12345')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/octet-stream'),
                     ('Content-Length', 11)],
            body=b'bodycontent'
        )

    def test_get_response_body(self):
        self.handler.path = 'http://seleniumwire/response_body?request_id=12345'
        self.mock_storage.load_response_body.return_value = b'bodycontent'

        self.handler.admin_handler()

        self.mock_storage.load_response_body.assert_called_once_with('12345')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/octet-stream'),
                     ('Content-Length', 11)],
            body=b'bodycontent'
        )

    def test_get_response_body_string(self):
        self.handler.path = 'http://seleniumwire/response_body?request_id=12345'
        self.mock_storage.load_response_body.return_value = 'bodycontent'

        self.handler.admin_handler()

        self.mock_storage.load_response_body.assert_called_once_with('12345')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/octet-stream'),
                     ('Content-Length', 11)],
            body=b'bodycontent'
        )

    def test_find(self):
        self.handler.path = 'http://seleniumwire/find?path=/foo/bar'
        self.mock_storage.find.return_value = {'id': '12345'}

        self.handler.admin_handler()

        self.mock_storage.find.assert_called_once_with('/foo/bar')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 15)],
            body=b'{"id": "12345"}'
        )

    def test_find_no_match(self):
        self.handler.path = 'http://seleniumwire/find?path=/foo/bar'
        self.mock_storage.find.return_value = None

        self.handler.admin_handler()

        self.mock_storage.find.assert_called_once_with('/foo/bar')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 4)],
            body=b'null'
        )

    def test_set_header_overrides(self):
        self.handler.path = 'http://seleniumwire/header_overrides'
        self.command = 'POST'



    def assert_response_mocks_called(self, status, headers, body):
        self.mock_send_response.assert_called_once_with(status)
        self.mock_send_header.assert_has_calls([call(k, v) for k, v in headers])
        self.mock_end_headers.assert_called_once()
        self.mock_wfile.write.assert_called_once_with(body)

    def setUp(self):
        CaptureRequestHandler.__init__ = Mock(return_value=None)
        self.mock_modifier = Mock()
        self.mock_storage = Mock()
        self.mock_send_response = Mock()
        self.mock_send_header = Mock()
        self.mock_end_headers = Mock()
        self.mock_wfile = Mock()

        self.handler = CaptureRequestHandler()
        self.handler.server = Mock()
        self.handler.server.modifier = self.mock_modifier
        self.handler.server.storage = self.mock_storage
        self.handler.server.options = {}
        self.handler.command = 'GET'
        self.handler.send_response = self.mock_send_response
        self.handler.send_header = self.mock_send_header
        self.handler.end_headers = self.mock_end_headers
        self.handler.wfile = self.mock_wfile

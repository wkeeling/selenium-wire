from unittest import TestCase
from unittest.mock import ANY, Mock

from seleniumwire.proxy.handler import CaptureRequestHandler


class CaptureRequestHandlerTest(TestCase):

    def test_request_modifier_called(self):
        self.handler.command = 'POST'
        self.body = b'foobar'
        modified = []

        def modify_request(req, **kwargs):
            modified.append((req, kwargs))
            req.body = b'foobarbaz'

        self.mock_modifier.modify_request.side_effect = modify_request

        body = self.handler.handle_request(self.handler, self.body)

        self.assertEqual(1, len(modified))
        request, attrs = modified[0]
        self.assertEqual('https://www.google.com/foo/bar?x=y', request.path)
        self.assertEqual({'urlattr': 'path', 'methodattr': 'command'}, attrs)
        self.assertEqual(b'foobarbaz', body)

    def test_save_request_called(self):
        saved = []
        self.mock_storage.save_request.side_effect = lambda r: saved.append(r)

        self.handler.handle_request(self.handler, self.body)

        self.assertEqual(1, len(saved))
        self.assertEqual('https://www.google.com/foo/bar?x=y', saved[0].url)

    def test_ignore_get_method(self):
        self.handler.server.options = {'ignore_http_methods': ['GET']}

        self.handler.handle_request(self.handler, self.body)

        self.assertFalse(self.mock_storage.save_request.called)

    def test_no_ignores(self):
        self.handler.command = 'OPTIONS'
        self.handler.options = {'ignore_http_methods': []}

        self.handler.handle_request(self.handler, self.body)

        self.assertTrue(self.mock_modifier.modify_request.called)

    def test_not_in_scope(self):
        self.handler.server.scopes = ['http://www.somewhere.com']

        self.handler.handle_request(self.handler, self.body)

        self.assertFalse(self.mock_storage.save_request.called)

    def test_response_modifier_called(self):
        modified = []

        def modify_response(res, req, **kwargs):
            modified.append((res, req, kwargs))

        self.mock_modifier.modify_response.side_effect = modify_response
        res, res_body = Mock(status=200, reason='OK', headers={}), b'the body'

        self.handler.handle_response(self.handler, self.body, res, res_body)

        self.assertEqual(1, len(modified))
        response, request, attrs = modified[0]
        self.assertEqual('200 OK', '{} {}'.format(response.status, response.reason))
        self.assertEqual('https://www.google.com/foo/bar?x=y', request.path)
        self.assertEqual({'urlattr': 'path'}, attrs)

    def test_save_response_called(self):
        saved = []
        self.mock_storage.save_response.side_effect = lambda i, r: saved.append((i, r))
        res, res_body = Mock(status=200, reason='OK', headers={}), b'the body'

        self.handler.handle_response(self.handler, self.body, res, res_body)

        self.assertEqual(1, len(saved))
        request_id, response = saved[0]
        self.assertEqual('12345', request_id)
        self.assertEqual(200, response.status_code)
        self.assertEqual('OK', response.reason)

    def test_ignores_response(self):
        res, res_body = Mock(), Mock()
        delattr(self.handler, 'id')
        self.handler.handle_response(self.handler, self.body, res, res_body)

        self.assertFalse(self.mock_storage.save_response.called)

    def test_request_interceptor_called(self):
        self.body = b'foobar'

        def intercept(req):
            req.method = 'POST'
            req.url = 'https://www.google.com/foo/bar?x=y'
            req.body = b'foobarbaz'
            req.headers = {'a': 'b'}

        self.handler.server.request_interceptor = intercept

        body = self.handler.handle_request(self.handler, self.body)

        self.assertEqual('POST', self.handler.command)
        self.assertEqual('https://www.google.com/foo/bar?x=y', self.handler.path)
        self.assertEqual(b'foobarbaz', body)
        self.assertEqual({'a': 'b'}, dict(self.handler.headers))

    def test_request_interceptor_creates_response(self):
        def intercept(req):
            req.create_response(
                status_code=200,
                headers={'a': 'b'},
                body=b'foobarbaz'
            )

        self.handler.server.request_interceptor = intercept

        body = self.handler.handle_request(self.handler, self.body)

        self.assertIs(False, body)
        self.handler.commit_response.assert_called_once_with(
            200, 'OK', ANY, b'foobarbaz'
        )

    def test_response_interceptor_called(self):
        response, res_body = Mock(status=200, reason='OK', headers={}), b'the body'

        def intercept(req, res):
            if req.url == 'https://www.google.com/foo/bar?x=y':
                res.status_code = 201
                res.reason = 'Created'
                res.body = b'foobarbaz'
                res.headers = {'a': 'b'}

        self.handler.server.response_interceptor = intercept

        res_body = self.handler.handle_response(self.handler, self.body, response, res_body)

        self.assertEqual(201, response.status)
        self.assertEqual('Created', response.reason)
        self.assertEqual(b'foobarbaz', res_body)
        self.assertEqual({'a': 'b'}, dict(response.headers))

    def setUp(self):
        CaptureRequestHandler.__init__ = Mock(return_value=None)
        self.mock_modifier, self.mock_storage = Mock(), Mock()
        self.handler = CaptureRequestHandler()
        self.handler.server = Mock()
        self.handler.id = '12345'
        self.handler.server.options = {}
        self.handler.server.modifier = self.mock_modifier
        self.handler.server.storage = self.mock_storage
        self.handler.server.scopes = []
        self.handler.server.request_interceptor = None
        self.handler.server.response_interceptor = None
        self.handler.headers = {}
        self.handler.path = 'https://www.google.com/foo/bar?x=y'
        self.handler.command = 'GET'
        self.handler.status = None
        self.handler.commit_response = Mock()
        self.body = None

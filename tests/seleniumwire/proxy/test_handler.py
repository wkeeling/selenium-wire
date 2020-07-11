import json
from unittest import TestCase
from unittest.mock import Mock, call

from seleniumwire.proxy.handler import CaptureRequestHandler
from seleniumwire.proxy.request import Request


class CaptureRequestHandlerTest(TestCase):

    def test_request_modifier_called(self):
        modified = []
        self.mock_modifier.modify.side_effect = lambda r: modified.append(r)

        self.handler.handle_request(self.handler, self.body)

        self.assertEqual(1, len(modified))
        self.assertEqual('https://www.google.com/foo/bar?x=y', modified[0].url)

    def test_save_request_called(self):
        saved = []
        self.mock_storage.save_request.side_effect = lambda r: saved.append(r)

        self.handler.handle_request(self.handler, self.body)

        self.assertEqual(1, len(saved))
        self.assertEqual('https://www.google.com/foo/bar?x=y', saved[0].url)

    def test_ignores_options(self):
        self.handler.command = 'OPTIONS'

        self.handler.handle_request(self.handler, self.body)

        self.assertFalse(self.mock_storage.save_request.called)

    def test_ignores_get(self):
        self.handler.options = {'ignore_http_methods': ['OPTIONS', 'GET']}

        self.handler.handle_request(self.handler, self.body)

        self.assertFalse(self.mock_storage.save_request.called)

    def test_no_ignores(self):
        self.handler.command = 'OPTIONS'
        self.handler.options = {'ignore_http_methods': []}

        self.handler.handle_request(self.handler, self.body)

        self.assertTrue(self.mock_modifier.modify.called)

    def test_not_in_scope(self):
        self.handler.scopes = ['http://www.somewhere.com']

        self.handler.handle_request(self.handler, self.body)

        self.assertFalse(self.mock_storage.save_request.called)

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

    def setUp(self):
        CaptureRequestHandler.__init__ = Mock(return_value=None)
        self.mock_modifier, self.mock_storage = Mock(), Mock()
        self.handler = CaptureRequestHandler()
        self.handler.server = Mock()
        self.handler.id = '12345'
        self.handler.options = {}
        self.handler.modifier = self.mock_modifier
        self.handler.storage = self.mock_storage
        self.handler.scopes = []
        self.handler.options = {}
        self.handler.scopes = []
        self.handler.headers = {}
        self.handler.url = 'https://www.google.com/foo/bar?x=y'
        self.handler.command = 'GET'
        self.body = None


class AdminMixinTest(TestCase):

    def test_get_requests(self):
        self.handler.path = 'http://seleniumwire/requests'
        request_1 = Request(method='GET', url='http://somewhere.com/foo', headers={})
        request_1.id = '12345'
        request_2 = Request(method='GET', url='http://somewhere.com/bar', headers={})
        request_2.id = '67890'
        self.mock_storage.load_requests.return_value = [request_1, request_2]

        self.handler.handle_admin()

        self.mock_storage.load_requests.assert_called_once_with()
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 206)],
            body=b'[{"id": "12345", "method": "GET", "url": "http://somewhere.com/foo", "headers": {}, '
                 b'"response": null}, {"id": "67890", "method": "GET", '
                 b'"path": "http://somewhere.com/bar", "headers": {}, "response": null}]'
        )

    def test_delete_requests(self):
        self.handler.path = 'http://seleniumwire/requests'
        self.handler.command = 'DELETE'

        self.handler.handle_admin()

        self.mock_storage.clear_requests.assert_called_once_with()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_last_request(self):
        self.handler.path = 'http://seleniumwire/last_request'
        request = Request(method='GET', url='http://somewhere.com/foo', headers={})
        request.id = '12345'
        self.mock_storage.load_last_request.return_value = request

        self.handler.handle_admin()

        self.mock_storage.load_last_request.assert_called_once_with()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 101)],
            body=b'{"id": "12345", "method": "GET", "url": "http://somewhere.com/foo", "headers": {}, '
                 b'"response": null}'
        )

    def test_get_request_body(self):
        self.handler.path = 'http://seleniumwire/request_body?request_id=12345'
        self.mock_storage.load_request_body.return_value = b'bodycontent'

        self.handler.handle_admin()

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

        self.handler.handle_admin()

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

        self.handler.handle_admin()

        self.mock_storage.load_response_body.assert_called_once_with('12345')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/octet-stream'),
                     ('Content-Length', 11)],
            body=b'bodycontent'
        )

    def test_find(self):
        self.handler.path = 'http://seleniumwire/find?path=/foo/bar'
        request = Request(method='GET', url='http://somewhere.com/foo', headers={})
        request.id = '12345'
        self.mock_storage.find.return_value = request

        self.handler.handle_admin()

        self.mock_storage.find.assert_called_once_with('/foo/bar')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 101)],
            body=b'{"id": "12345", "method": "GET", "url": "http://somewhere.com/foo", "headers": {}, '
                 b'"response": null}'
        )

    def test_find_no_match(self):
        self.handler.path = 'http://seleniumwire/find?path=/foo/bar'
        self.mock_storage.find.return_value = None

        self.handler.handle_admin()

        self.mock_storage.find.assert_called_once_with('/foo/bar')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 4)],
            body=b'null'
        )

    def test_set_header_overrides(self):
        self.handler.path = 'http://seleniumwire/header_overrides'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 20
        }
        self.mock_rfile.read.return_value = b'{"User-Agent": "useragent"}'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(20)
        self.assertEqual(self.mock_modifier.headers, {'User-Agent': 'useragent'})
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_delete_header_overrides(self):
        self.handler.path = 'http://seleniumwire/header_overrides'
        self.handler.command = 'DELETE'
        self.mock_modifier.headers = {'User-Agent': 'useragent'}

        self.handler.handle_admin()

        self.assertFalse(hasattr(self.mock_modifier, 'headers'))
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_header_overrides(self):
        self.handler.path = 'http://seleniumwire/header_overrides'
        self.mock_modifier.headers = {'User-Agent': 'useragent'}

        self.handler.handle_admin()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 27)],
            body=b'{"User-Agent": "useragent"}'
        )

    def test_set_param_overrides(self):
        self.handler.path = 'http://seleniumwire/param_overrides'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 14
        }
        self.mock_rfile.read.return_value = b'{"foo": "bar"}'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(14)
        self.assertEqual(self.mock_modifier.params, {'foo': 'bar'})
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_delete_param_overrides(self):
        self.handler.path = 'http://seleniumwire/param_overrides'
        self.handler.command = 'DELETE'
        self.mock_modifier.params = {'foo': 'bar'}

        self.handler.handle_admin()

        self.assertFalse(hasattr(self.mock_modifier, 'params'))
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_param_overrides(self):
        self.handler.path = 'http://seleniumwire/param_overrides'
        self.mock_modifier.params = {'foo': 'bar'}

        self.handler.handle_admin()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 14)],
            body=b'{"foo": "bar"}'
        )

    def test_set_querystring_overrides(self):
        self.handler.path = 'http://seleniumwire/querystring_overrides'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 36
        }
        self.mock_rfile.read.return_value = b'{"overrides": "foo=bar&hello=world"}'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(36)
        self.assertEqual(self.mock_modifier.querystring, 'foo=bar&hello=world')
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_delete_querystring_overrides(self):
        self.handler.path = 'http://seleniumwire/querystring_overrides'
        self.handler.command = 'DELETE'
        self.mock_modifier.querystring = 'foo=bar&hello=world'

        self.handler.handle_admin()

        self.assertFalse(hasattr(self.mock_modifier, 'querystring'))
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_querystring_overrides(self):
        self.handler.path = 'http://seleniumwire/querystring_overrides'
        self.mock_modifier.querystring = 'foo=bar&hello=world'

        self.handler.handle_admin()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 36)],
            body=b'{"overrides": "foo=bar&hello=world"}'
        )

    def test_set_rewrite_rules(self):
        self.handler.path = 'http://seleniumwire/rewrite_rules'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 20
        }
        self.mock_rfile.read.return_value = b'[["https?://)prod1.server.com(.*)", "\\\\1prod2.server.com\\\\2"]]'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(20)
        self.assertEqual(self.mock_modifier.rewrite_rules,
                         [["https?://)prod1.server.com(.*)", r"\1prod2.server.com\2"]])
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_delete_rewrite_rules(self):
        self.handler.path = 'http://seleniumwire/rewrite_rules'
        self.handler.command = 'DELETE'
        self.mock_modifier.rewrite_rules = [["https?://)prod1.server.com(.*)", r"\1prod2.server.com\2"]]

        self.handler.handle_admin()

        self.assertFalse(hasattr(self.mock_modifier, 'rewrite_rules'))
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_rewrite_rules(self):
        self.handler.path = 'http://seleniumwire/rewrite_rules'
        self.mock_modifier.rewrite_rules = [["https?://)prod1.server.com(.*)", r"\1prod2.server.com\2"]]

        self.handler.handle_admin()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 62)],
            body=b'[["https?://)prod1.server.com(.*)", "\\\\1prod2.server.com\\\\2"]]'
        )

    def test_set_scopes(self):
        self.handler.path = 'http://seleniumwire/scopes'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 35
        }
        self.mock_rfile.read.return_value = b'[".*stackoverflow.*", ".*github.*"]'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(35)
        self.assertEqual(self.handler.scopes, ['.*stackoverflow.*', '.*github.*'])
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_delete_scopes(self):
        self.handler.path = 'http://seleniumwire/scopes'
        self.handler.command = 'DELETE'
        self.scopes = ['.*stackoverflow.*', '.*github.*']

        self.handler.handle_admin()

        self.assertEqual(self.handler.scopes, [])
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_get_scopes(self):
        self.handler.path = 'http://seleniumwire/scopes'
        self.handler.scopes = ['.*stackoverflow.*', '.*github.*']

        self.handler.handle_admin()

        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 35)],
            body=b'[".*stackoverflow.*", ".*github.*"]'
        )

    def test_initialise(self):
        self.handler.initialise = Mock()
        self.handler.path = 'http://seleniumwire/initialise'
        self.handler.command = 'POST'
        self.handler.headers = {
            'Content-Length': 40
        }
        self.mock_rfile.read.return_value = b'{"port": 8080, "connection_timeout": 30}'

        self.handler.handle_admin()

        self.mock_rfile.read.assert_called_once_with(40)
        self.handler.initialise.assert_called_once_with({'port': 8080, 'connection_timeout': 30})
        self.assert_response_mocks_called(
            status=200,
            headers=[('Content-Type', 'application/json'),
                     ('Content-Length', 16)],
            body=b'{"status": "ok"}'
        )

    def test_no_handler(self):
        self.handler.path = 'http://seleniumwire/foobar'

        with self.assertRaises(RuntimeError):
            self.handler.handle_admin()

    def assert_response_mocks_called(self, status, headers, body):
        self.mock_send_response.assert_called_once_with(status)
        self.mock_send_header.assert_has_calls([call(k, v) for k, v in headers])
        self.mock_end_headers.assert_called_once_with()
        self.assertEqual(1, self.mock_wfile.write.call_count)
        try:
            body = json.loads(body.decode('utf-8'))
            rbody = json.loads(self.rbody.decode('utf-8'))
        except json.decoder.JSONDecodeError:
            rbody = self.rbody
        # Compare the dictionaries rather than the JSON strings which is
        # more reliable when dictionary insertion order isn't preserved.
        self.assertEqual(body, rbody)

    def setUp(self):
        CaptureRequestHandler.__init__ = Mock(return_value=None)
        self.mock_modifier = Mock()
        self.mock_storage = Mock()
        self.mock_send_response = Mock()
        self.mock_send_header = Mock()
        self.mock_end_headers = Mock()
        self.mock_rfile = Mock()
        self.mock_rfile.read.return_value = b'the body'
        self.mock_wfile = Mock()
        self.mock_wfile.write.side_effect = lambda body: setattr(self, 'rbody', body)

        self.handler = CaptureRequestHandler()
        self.handler.server = Mock()
        self.handler.modifier = self.mock_modifier
        self.handler.storage = self.mock_storage
        self.handler.options = {}
        self.handler.headers = {}
        self.handler.scopes = []
        self.handler.command = 'GET'
        self.handler.send_response = self.mock_send_response
        self.handler.send_header = self.mock_send_header
        self.handler.end_headers = self.mock_end_headers
        self.handler.rfile = self.mock_rfile
        self.handler.wfile = self.mock_wfile

from unittest import TestCase
from unittest.mock import Mock

from seleniumwire.handler import MitmProxyRequestHandler
from seleniumwire.thirdparty.mitmproxy.net.http.headers import Headers


class MitmProxyRequestHandlerTest(TestCase):

    def test_request_modifier_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b''

        self.handler.request(mock_flow)

        self.proxy.modifier.modify_request.assert_called_once_with(mock_flow.request, bodyattr='raw_content')

    def test_save_request(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b'foobar'
        saved_request = None

        def save_request(req):
            nonlocal saved_request
            req.id = '12345'
            saved_request = req

        self.proxy.storage.save_request.side_effect = save_request

        self.handler.request(mock_flow)

        self.assertEqual(1, self.proxy.storage.save_request.call_count)
        self.assertEqual('GET', saved_request.method)
        self.assertEqual('http://somewhere.com/some/path', saved_request.url)
        self.assertEqual({'Accept-Encoding': 'identity'}, dict(saved_request.headers))
        self.assertEqual(b'foobar', saved_request.body)
        self.assertEqual('12345', saved_request.id)
        self.assertEqual('12345', mock_flow.request.id)

    def test_disable_encoding(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'gzip')])
        mock_flow.request.raw_content = b''
        self.proxy.options['disable_encoding'] = True

        self.handler.request(mock_flow)

        self.assertEqual({'Accept-Encoding': 'identity'}, dict(mock_flow.request.headers))

    def test_response_modifier_called(self):
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.response.status_code = 200
        mock_flow.response.reason = 'OK'
        mock_flow.response.headers = Headers([(b'Content-Length', b'6')])
        mock_flow.response.raw_content = b'foobar'

        self.handler.response(mock_flow)

        self.proxy.modifier.modify_response.assert_called_once_with(mock_flow.response, mock_flow.request)

    def test_save_response(self):
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.response.status_code = 200
        mock_flow.response.reason = 'OK'
        mock_flow.response.headers = Headers([(b'Content-Length', b'6')])
        mock_flow.response.raw_content = b'foobar'
        saved_response = None

        def save_response(_, response):
            nonlocal saved_response
            saved_response = response

        self.proxy.storage.save_response.side_effect = save_response

        self.handler.response(mock_flow)

        self.proxy.storage.save_response.assert_called_once_with('12345', saved_response)
        self.assertEqual(200, saved_response.status_code)
        self.assertEqual('OK', saved_response.reason)
        self.assertEqual({'Content-Length': '6'}, dict(saved_response.headers))
        self.assertEqual(b'foobar', saved_response.body)

    def test_ignore_response_when_no_request(self):
        mock_flow = Mock()
        mock_flow.request = object()  # Make it a real object so hasattr() works as expected

        self.handler.response(mock_flow)

        self.assertEqual(0, self.proxy.storage.save_response.call_count)

    def test_ignore_request_url_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server2/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b'foobar'

        self.proxy.scopes = ['https://server1.*']

        # self.handler.requestheaders(mock_flow)
        self.handler.request(mock_flow)

        self.assertEqual(0, self.proxy.storage.save_request.call_count)

    def test_ignore_request_method_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server2/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b'foobar'

        self.proxy.options['ignore_http_methods'] = ['GET']

        self.handler.request(mock_flow)

        self.assertEqual(0, self.proxy.storage.save_request.call_count)

    def test_stream_request_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server2/some/path'
        mock_flow.request.stream = True

        self.proxy.scopes = ['https://server1.*']

        self.handler.requestheaders(mock_flow)

        self.assertTrue(mock_flow.request.stream)

    def test_stream_response_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server2/some/path'
        mock_flow.response.stream = True

        self.proxy.scopes = ['https://server1.*']

        self.handler.responseheaders(mock_flow)

        self.assertTrue(mock_flow.response.stream)

    def test_request_interceptor_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b''

        def intercept(req):
            req.method = 'POST'
            req.url = 'https://www.google.com/foo/bar?x=y'
            req.body = b'foobarbaz'
            req.headers['a'] = 'b'

        self.proxy.request_interceptor = intercept

        self.handler.request(mock_flow)

        self.assertEqual('POST', mock_flow.request.method)
        self.assertEqual('https://www.google.com/foo/bar?x=y', mock_flow.request.url)
        self.assertEqual({'Accept-Encoding': 'identity', 'a': 'b'}, dict(mock_flow.request.headers))
        self.assertEqual(b'foobarbaz', mock_flow.request.raw_content)

    def test_request_interceptor_creates_response(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b''

        def intercept(req):
            req.create_response(
                status_code=200,
                headers={'a': 'b'},
                body=b'foobarbaz'
            )

        self.proxy.request_interceptor = intercept

        self.handler.request(mock_flow)

        self.assertEqual(200, mock_flow.response.status_code)
        self.assertEqual({'a': 'b', 'content-length': '9'}, dict(mock_flow.response.headers))
        self.assertEqual(b'foobarbaz', mock_flow.response.content)

    def test_response_interceptor_called(self):
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.headers = Headers()
        mock_flow.request.raw_content = b''
        mock_flow.response.status_code = 200
        mock_flow.response.reason = 'OK'
        mock_flow.response.headers = Headers([(b'Content-Length', b'6')])
        mock_flow.response.raw_content = b'foobar'

        def intercept(req, res):
            if req.url == 'http://somewhere.com/some/path':
                res.status_code = 201
                res.reason = 'Created'
                res.headers['a'] = 'b'
                res.body = b'foobarbaz'

        self.proxy.response_interceptor = intercept

        self.handler.response(mock_flow)

        self.assertEqual(201, mock_flow.response.status_code)
        self.assertEqual('Created', mock_flow.response.reason)
        self.assertEqual({'Content-Length': '6', 'a': 'b'}, dict(mock_flow.response.headers))
        self.assertEqual(b'foobarbaz', mock_flow.response.raw_content)

    def setUp(self):
        self.proxy = Mock()
        self.proxy.storage = Mock()
        self.proxy.modifier = Mock()
        self.proxy.options = {}
        self.proxy.scopes = []
        self.proxy.request_interceptor = None
        self.proxy.response_interceptor = None
        self.handler = MitmProxyRequestHandler(self.proxy)

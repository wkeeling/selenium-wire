from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock, patch

from seleniumwire.handler import InterceptRequestHandler
from seleniumwire.request import WebSocketMessage
from seleniumwire.thirdparty.mitmproxy.net.http.headers import Headers


class InterceptRequestHandlerTest(TestCase):

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
        mock_cert = Mock()
        mock_cert.subject = [(b'C', b'US'), (b'O', b'Mozilla Corporation')]
        mock_cert.serial = 123456789
        mock_cert.keyinfo = ('RSA', 2048)
        mock_cert.x509.get_signature_algorithm.return_value = b'test_algo'
        mock_cert.has_expired = False
        mock_cert.issuer = [(b'CN', b'DigiCert SHA2 Secure Server CA')]
        mock_cert.organization = b'Mozilla Corporation'
        mock_cert.cn = b'*.cdn.mozilla.net'
        mock_cert.altnames = [b'*.cdn.mozilla.net', b'cdn.mozilla.net']
        notbefore = datetime.now()
        notafter = datetime.now()
        mock_cert.notbefore = notbefore
        mock_cert.notafter = notafter
        mock_flow.server_conn.cert = mock_cert
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
        self.assertEqual([(b'C', b'US'), (b'O', b'Mozilla Corporation')], saved_response.cert['subject'])
        self.assertEqual(123456789, saved_response.cert['serial'])
        self.assertEqual(('RSA', 2048), saved_response.cert['key'])
        self.assertEqual(b'test_algo', saved_response.cert['signature_algorithm'])
        self.assertFalse(saved_response.cert['expired'])
        self.assertEqual([(b'CN', b'DigiCert SHA2 Secure Server CA')], saved_response.cert['issuer'])
        self.assertEqual(notbefore, saved_response.cert['notbefore'])
        self.assertEqual(notafter, saved_response.cert['notafter'])
        self.assertEqual(b'Mozilla Corporation', saved_response.cert['organization'])
        self.assertEqual(b'*.cdn.mozilla.net', saved_response.cert['cn'])
        self.assertEqual([b'*.cdn.mozilla.net', b'cdn.mozilla.net'], saved_response.cert['altnames'])

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

    def test_save_websocket_message(self):
        mock_handshake_flow = Mock()
        mock_handshake_flow.request.id = '12345'
        mock_flow = Mock()
        mock_flow.handshake_flow = mock_handshake_flow
        mock_flow.messages = [Mock(
            from_client=True,
            content='test message',
            timestamp=1614069300.0
        )]

        self.handler.websocket_message(mock_flow)

        self.proxy.storage.save_ws_message.assert_called_once_with('12345', WebSocketMessage(
            from_client=True,
            content='test message',
            date=datetime.fromtimestamp(1614069300.0)
        ))

    def test_save_websocket_message_no_request(self):
        """If the handshake request was not saved (has no id) then
        we don't expect the websocket message to be saved.
        """
        mock_handshake_flow = Mock()
        mock_handshake_flow.request = Mock()
        mock_flow = Mock()
        mock_flow.handshake_flow = mock_handshake_flow

        with patch('seleniumwire.handler.hasattr') as mock_hasattr:
            mock_hasattr.return_value = False
            self.handler.websocket_message(mock_flow)

        self.assertEqual(0, self.proxy.storage.save_ws_message.call_count)

    @patch('seleniumwire.handler.har')
    def test_save_har_entry(self, mock_har):
        self.proxy.options['enable_har'] = True
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.response.headers = {}
        mock_flow.response.raw_content = b''
        mock_har.create_har_entry.return_value = {'name': 'test_har_entry'}

        self.handler.response(mock_flow)

        self.proxy.storage.save_har_entry.assert_called_once_with(
            '12345', {'name': 'test_har_entry'}
        )
        mock_har.create_har_entry.assert_called_once_with(mock_flow)

    @patch('seleniumwire.handler.har')
    def test_save_har_entry_disabled(self, mock_har):
        self.proxy.options['enable_har'] = False
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.response.headers = {}
        mock_flow.response.raw_content = b''
        mock_har.create_har_entry.return_value = {'name': 'test_har_entry'}

        self.handler.response(mock_flow)

        self.assertEqual(0, self.proxy.storage.save_har_entry.call_count)
        self.assertEqual(0, mock_har.create_har_entry.call_count)

    def setUp(self):
        self.proxy = Mock()
        self.proxy.storage = Mock()
        self.proxy.modifier = Mock()
        self.proxy.options = {}
        self.proxy.scopes = []
        self.proxy.request_interceptor = None
        self.proxy.response_interceptor = None
        self.handler = InterceptRequestHandler(self.proxy)

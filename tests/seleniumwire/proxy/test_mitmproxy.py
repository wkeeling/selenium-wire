from unittest import TestCase
from unittest.mock import ANY, Mock, call, patch

from mitmproxy.net.http.headers import Headers

from seleniumwire.proxy.mitmproxy import MitmProxy, MitmProxyRequestHandler


class MitmProxyRequestHandlerTest(TestCase):

    def test_request_modifier_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b''

        self.handler.request(mock_flow)

        self.server.modifier.modify_request.assert_called_once_with(mock_flow.request, bodyattr='raw_content')

    def test_capture_request_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'identity')])
        mock_flow.request.raw_content = b'foobar'
        captured_request = None

        def capture_request(req):
            nonlocal captured_request
            req.id = '12345'
            captured_request = req

        self.capture_request.side_effect = capture_request

        self.handler.request(mock_flow)

        self.assertEqual(1, self.capture_request.call_count)
        self.assertEqual('GET', captured_request.method)
        self.assertEqual('http://somewhere.com/some/path', captured_request.url)
        self.assertEqual({'Accept-Encoding': 'identity'}, dict(captured_request.headers))
        self.assertEqual(b'foobar', captured_request.body)
        self.assertEqual('12345', captured_request.id)
        self.assertEqual('12345', mock_flow.request.id)

    def test_disable_encoding(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = Headers([(b'Accept-Encoding', b'gzip')])
        mock_flow.request.raw_content = b''
        self.server.options['disable_encoding'] = True

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

        self.server.modifier.modify_response.assert_called_once_with(mock_flow.response, mock_flow.request)

    def test_capture_response_called(self):
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.response.status_code = 200
        mock_flow.response.reason = 'OK'
        mock_flow.response.headers = Headers([(b'Content-Length', b'6')])
        mock_flow.response.raw_content = b'foobar'
        captured_response = None

        def capture_response(*args):
            nonlocal captured_response
            captured_response = args[2]

        self.capture_response.side_effect = capture_response

        self.handler.response(mock_flow)

        self.capture_response.assert_called_once_with('12345', 'http://somewhere.com/some/path', ANY)
        self.assertEqual(200, captured_response.status_code)
        self.assertEqual('OK', captured_response.reason)
        self.assertEqual({'Content-Length': '6'}, dict(captured_response.headers))
        self.assertEqual(b'foobar', captured_response.body)

    def test_ignore_response_when_no_request(self):
        mock_flow = Mock()
        mock_flow.request = object()  # Make it a real object so hasattr() works as expected

        self.handler.response(mock_flow)

        self.assertEqual(0, self.capture_response.call_count)

    def test_stream_request_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server/some/path'
        mock_flow.request.stream = True

        self.handler.scopes = ['https://server']

        self.handler.requestheaders(mock_flow)

        self.assertFalse(mock_flow.request.stream)

    def test_stream_response_out_of_scope(self):
        mock_flow = Mock()
        mock_flow.request.url = 'https://server/some/path'
        mock_flow.response.stream = True

        self.handler.scopes = ['https://server']

        self.handler.responseheaders(mock_flow)

        self.assertFalse(mock_flow.response.stream)
        
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

        self.server.request_interceptor = intercept

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

        self.server.request_interceptor = intercept

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

        self.server.response_interceptor = intercept

        self.handler.response(mock_flow)

        self.assertEqual(201, mock_flow.response.status_code)
        self.assertEqual('Created', mock_flow.response.reason)
        self.assertEqual({'Content-Length': '6', 'a': 'b'}, dict(mock_flow.response.headers))
        self.assertEqual(b'foobarbaz', mock_flow.response.raw_content)

    def setUp(self):
        self.capture_request = Mock()
        self.capture_response = Mock()
        self.server = Mock()
        self.server.storage = Mock()
        self.server.modifier = Mock()
        self.server.options = {}
        self.server.scopes = []
        self.server.request_interceptor = None
        self.server.response_interceptor = None
        self.handler = MitmProxyRequestHandler(self.server)
        self.handler.capture_request = self.capture_request
        self.handler.capture_response = self.capture_response


class MitmProxyTest(TestCase):

    def test_creates_storage(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.assertEqual(self.mock_storage.return_value, proxy.storage)
        self.mock_storage.assert_called_once_with(base_dir='/some/dir')

    def test_creates_master(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })
        self.assertEqual(self.mock_master.return_value, proxy._master)
        self.mock_options.assert_called_once_with(
            listen_host='somehost',
            listen_port=12345
        )
        self.mock_master.assert_called_once_with(self.mock_options.return_value)
        self.assertEqual(self.mock_proxy_server.return_value, self.mock_master.return_value.server)
        self.mock_proxy_config.assert_called_once_with(self.mock_options.return_value)
        self.mock_proxy_server.assert_called_once_with(self.mock_proxy_config.return_value)
        self.mock_master.return_value.addons.add.assert_has_calls([
            call(),
            call(self.mock_handler.return_value)
        ])
        self.mock_addons.default_addons.assert_called_once_with()
        self.mock_handler.assert_called_once_with(proxy)

    def test_update_mitmproxy_options(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'mitm_test': 'foobar'
        })

        self.mock_options.return_value.update.has_calls([
            call(
                confdir='~/.mitmproxy',
                ssl_insecure=True,
                upstream_cert=False,
                stream_websockets=True,
            ),
            call(
                test='foobar'
            )
        ])

    def test_update_mitmproxy_options_with_override(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'mitm_test': 'foobar',
            'mitm_confdir': '/tmp/.mitmproxy'
        })

        self.mock_options.return_value.update.has_calls([
            call(
                confdir='~/.mitmproxy',
                ssl_insecure=True,
                upstream_cert=False,
                stream_websockets=True,
            ),
            call(
                test='foobar',
                confdir='/tmp/.mitmproxy'
            )
        ])

    def test_upstream_proxy(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'http': 'http://proxyserver:8080',
                # We pick https when both are specified and the same
                'https': 'https://proxyserver:8080'
            }
        })

        self.mock_options.return_value.update.has_calls([
            call(
                confdir='~/.mitmproxy',
                ssl_insecure=True,
                upstream_cert=False,
                stream_websockets=True,
                mode='upstream:https://proxyserver:8080'
            ),
            call()
        ])

    def test_upstream_proxy_single(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'http': 'http://proxyserver:8080',
            }
        })

        self.mock_options.return_value.update.has_calls([
            call(
                confdir='~/.mitmproxy',
                ssl_insecure=True,
                upstream_cert=False,
                stream_websockets=True,
                mode='upstream:http://proxyserver:8080'
            ),
            call()
        ])

    def test_upstream_proxy_auth(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'https': 'https://user:pass@proxyserver:8080',
            }
        })

        self.mock_options.return_value.update.has_calls([
            call(
                confdir='~/.mitmproxy',
                ssl_insecure=True,
                upstream_cert=False,
                stream_websockets=True,
                mode='upstream:https://proxyserver:8080',
                upstream_auth='user:pass'
            ),
            call()
        ])

    def test_upstream_proxy_different(self):
        with self.assertRaises(ValueError):
            MitmProxy('somehost', 12345, {
                'request_storage_base_dir': '/some/dir',
                'proxy': {
                    'http': 'http://proxyserver1:8080',
                    'https': 'https://proxyserver2:8080'
                }
            })

    def test_get_event_loop(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.assertEqual(self.mock_asyncio.get_event_loop.return_value, proxy._event_loop)
        self.mock_asyncio.get_event_loop.assert_called_once_with()

    def test_serve_forever(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        proxy.serve_forever()

        self.mock_asyncio.set_event_loop.assert_called_once_with(proxy._event_loop)
        self.mock_master.return_value.run_loop.assert_called_once_with(proxy._event_loop.run_forever)

    def test_address(self):
        self.mock_proxy_server.return_value.address = ('somehost', 12345)
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.assertEqual(('somehost', 12345), proxy.address())

    def test_shutdown(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        proxy.shutdown()

        self.mock_master.return_value.shutdown.assert_called_once_with()
        self.mock_storage.return_value.cleanup.assert_called_once_with()

    def setUp(self):
        patcher = patch('seleniumwire.proxy.mitmproxy.RequestStorage')
        self.mock_storage = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.Options')
        self.mock_options = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.Master')
        self.mock_master = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.ProxyConfig')
        self.mock_proxy_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.ProxyServer')
        self.mock_proxy_server = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.addons')
        self.mock_addons = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.MitmProxyRequestHandler')
        self.mock_handler = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.proxy.mitmproxy.asyncio')
        self.mock_asyncio = patcher.start()
        self.addCleanup(patcher.stop)

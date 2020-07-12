from unittest import TestCase
from unittest.mock import ANY, Mock, patch

from seleniumwire.proxy import mitmproxy


@patch('seleniumwire.proxy.mitmproxy.socket')
@patch('seleniumwire.proxy.mitmproxy.subprocess')
class StartMitmproxyTest(TestCase):

    def test_popen_defaults(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0

        mitmproxy.start('127.0.0.1', 9950, {})

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            *self._popen_args()
        ])

    def test_port(self, mock_subprocess, mock_socket):
        port = 8888
        mock_socket.socket.return_value.connect_ex.return_value = 0

        mitmproxy.start('127.0.0.1', port, {})

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            *self._popen_args(port=port)
        ])

    def test_confdir(self, mock_subprocess, mock_socket):
        confdir = '/tmp/.mitmproxy'
        mock_socket.socket.return_value.connect_ex.return_value = 0

        mitmproxy.start('127.0.0.1', 9950, {'mitmproxy_confdir': confdir})

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            *self._popen_args(confdir=confdir)
        ])

    def test_ssl_insecure(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0

        mitmproxy.start('127.0.0.1', 9950, {'verify_ssl': False})

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            *self._popen_args(ssl_insecure=False)
        ])

    def test_upstream_proxy(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0
        options = {
            'proxy': {
                'http': 'http://proxyserver:8080',
                # We pick https when both are specified and the same
                'https': 'https://proxyserver:8080'
            }
        }

        mitmproxy.start('127.0.0.1', 9950, options)

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            '--set',
            'mode=upstream:https://proxyserver:8080',
            *self._popen_args()
        ])

    def test_upstream_proxy_single(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0
        options = {
            'proxy': {
                'http': 'http://proxyserver:8080',
            }
        }

        mitmproxy.start('127.0.0.1', 9950, options)

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            '--set',
            'mode=upstream:http://proxyserver:8080',
            *self._popen_args()
        ])

    def test_upstream_proxy_auth(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0
        options = {
            'proxy': {
                'https': 'https://user:pass@proxyserver:8080'
            }
        }

        mitmproxy.start('127.0.0.1', 9950, options)

        mock_subprocess.Popen.assert_called_once_with([
            'mitmdump',
            '--set',
            'mode=upstream:https://proxyserver:8080',
            '--set',
            'upstream_auth=user:pass',
            *self._popen_args()
        ])

    def test_upstream_proxy_different(self, mock_subprocess, mock_socket):
        mock_socket.socket.return_value.connect_ex.return_value = 0
        options = {
            'proxy': {
                'http': 'http://proxyserver1:8080',
                'https': 'https://proxyserver2:8080'
            }
        }

        with self.assertRaises(ValueError):
            mitmproxy.start('127.0.0.1', 9950, options)

        self.assertEqual(0, mock_subprocess.Popen.call_count)

    def _popen_args(self, confdir='~/.mitmproxy', port=9950, ssl_insecure=True):
        return [
            '--set',
            'confdir={}'.format(confdir),
            '--set',
            'listen_port={}'.format(port),
            '--set',
            'ssl_insecure={}'.format(str(ssl_insecure).lower()),
            '--set',
            'upstream_cert=false',
            '--set',
            'stream_websockets=true',
            '--set',
            'termlog_verbosity=error',
            '--set',
            'flow_detail=0',
            '-s',
            mitmproxy.__file__
        ]


class MitmProxyRequestHandlerTest(TestCase):

    @patch('seleniumwire.proxy.mitmproxy.logging')
    @patch('seleniumwire.proxy.mitmproxy.RequestStorage')
    def test_initialise(self, mock_storage, mock_logging):
        mock_logging.INFO = 'INFO'

        self.handler.initialise(options={
            'request_storage_base_dir': '/tmp',
            'mitmproxy_log_level': 'INFO'
        })

        self.assertEqual({
            'request_storage_base_dir': '/tmp',
            'mitmproxy_log_level': 'INFO'
        }, self.handler.options)

        mock_storage.assert_called_once_with(base_dir='/tmp')
        mock_logging.basicConfig.assert_called_once_with(level='INFO')

    @patch('seleniumwire.proxy.mitmproxy.mitmproxy')
    def test_handle_admin(self, mock_mitmproxy):
        mock_flow = Mock()
        mock_flow.request.url = 'http://seleniumwire/requests'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = {'Accept-Encoding': 'application/json'}
        mock_flow.request.raw_content = b''
        mock_response = Mock()
        mock_response.body = b'{"status": "ok"}'
        mock_response.headers = {'Content-Length': 16}
        captured_request = None

        def dispatch_admin(req):
            nonlocal captured_request
            captured_request = req
            return mock_response

        self.mock_dispatch_admin.side_effect = dispatch_admin
        mock_mitmproxy.http.HTTPResponse.make.return_value = 'flowresponse'

        self.handler.request(mock_flow)

        self.assertEqual('GET', captured_request.method)
        self.assertEqual('http://seleniumwire/requests', captured_request.url)
        self.assertEqual({'Accept-Encoding': 'application/json'}, captured_request.headers)
        self.assertEqual(b'', captured_request.body)
        self.assertEqual('flowresponse', mock_flow.response)
        mock_mitmproxy.http.HTTPResponse.make.assert_called_once_with(
            status_code=200,
            content=b'{"status": "ok"}',
            headers={'Content-Length': b'16'}
        )

    def test_request_modifier_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = {'Accept-Encoding': 'identity'}
        mock_flow.request.raw_content = b''

        self.handler.request(mock_flow)

        self.mock_modifier.modify.assert_called_once_with(mock_flow.request, body='raw_content')

    def test_capture_request_called(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = {'Accept-Encoding': 'identity'}
        mock_flow.request.raw_content = b'foobar'
        captured_request = None

        def capture_request(req):
            nonlocal captured_request
            req.id = '12345'
            captured_request = req

        self.mock_capture_request.side_effect = capture_request

        self.handler.request(mock_flow)

        self.assertEqual(1, self.mock_capture_request.call_count)
        self.assertEqual('GET', captured_request.method)
        self.assertEqual('http://somewhere.com/some/path', captured_request.url)
        self.assertEqual({'Accept-Encoding': 'identity'}, captured_request.headers)
        self.assertEqual(b'foobar', captured_request.body)
        self.assertEqual('12345', captured_request.id)
        self.assertEqual('12345', mock_flow.request.id)

    def test_disable_encoding(self):
        mock_flow = Mock()
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.request.method = 'GET'
        mock_flow.request.headers = {'Accept-Encoding': 'gzip'}
        mock_flow.request.raw_content = b''
        self.handler.options['disable_encoding'] = True

        self.handler.request(mock_flow)

        self.assertEqual({'Accept-Encoding': 'identity'}, mock_flow.request.headers)

    def test_capture_response_called(self):
        mock_flow = Mock()
        mock_flow.request.id = '12345'
        mock_flow.request.url = 'http://somewhere.com/some/path'
        mock_flow.response.status_code = 200
        mock_flow.response.reason = 'OK'
        mock_flow.response.headers = {'Content-Length': 6}
        mock_flow.response.raw_content = b'foobar'
        captured_response = None

        def capture_response(*args):
            nonlocal captured_response
            captured_response = args[2]

        self.mock_capture_response.side_effect = capture_response

        self.handler.response(mock_flow)

        self.mock_capture_response.assert_called_once_with('12345', 'http://somewhere.com/some/path', ANY)
        self.assertEqual(200, captured_response.status_code)
        self.assertEqual('OK', captured_response.reason)
        self.assertEqual({'Content-Length': 6}, captured_response.headers)
        self.assertEqual(b'foobar', captured_response.body)

    def test_ignore_response_when_no_request(self):
        mock_flow = Mock()
        mock_flow.request = object()  # Make it a real object so hasattr() works as expected

        self.handler.response(mock_flow)

        self.assertEqual(0, self.mock_capture_response.call_count)

    def setUp(self):
        self.mock_storage = Mock()
        self.mock_modifier = Mock()
        self.mock_dispatch_admin = Mock()
        self.mock_capture_request = Mock()
        self.mock_capture_response = Mock()
        self.handler = mitmproxy.MitmProxyRequestHandler()
        self.handler.options = {}
        self.handler.storage = self.mock_storage
        self.handler.modifier = self.mock_modifier
        self.handler.dispatch_admin = self.mock_dispatch_admin
        self.handler.capture_request = self.mock_capture_request
        self.handler.capture_response = self.mock_capture_response


class MitmProxyTest(TestCase):

    def test_shutdown(self):
        mock_proc = Mock()
        proxy = mitmproxy.MitmProxy('somehost', 9950, mock_proc)

        proxy.shutdown()

        mock_proc.terminate.assert_called_once_with()
        mock_proc.wait.assert_called_once_with(timeout=10)

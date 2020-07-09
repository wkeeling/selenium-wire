from unittest import TestCase
from unittest.mock import patch

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

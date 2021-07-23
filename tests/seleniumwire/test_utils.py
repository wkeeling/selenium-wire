import contextlib
import gzip
import os
import zlib
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import call, mock_open, patch

from seleniumwire.utils import decode, extract_cert, extract_cert_and_key, get_upstream_proxy, urlsafe_address


class GetUpstreamProxyTest(TestCase):
    def test_get_config(self):
        options = {
            'proxy': {
                'http': 'http://username1:password1@server1:8888',
                'https': 'https://username2:password2@server2:8888',
                'no_proxy': 'localhost',
            }
        }

        proxy = get_upstream_proxy(options)

        http = proxy['http']
        self.assertEqual('http', http.scheme)
        self.assertEqual('username1', http.username)
        self.assertEqual('password1', http.password)
        self.assertEqual('server1:8888', http.hostport)

        https = proxy['https']
        self.assertEqual('https', https.scheme)
        self.assertEqual('username2', https.username)
        self.assertEqual('password2', https.password)
        self.assertEqual('server2:8888', https.hostport)

        self.assertEqual(['localhost'], proxy['no_proxy'])

    def test_get_from_env(self):
        with self.set_env(
            HTTP_PROXY='http://username1:password1@server1:8888',
            HTTPS_PROXY='https://username2:password2@server2:8888',
            NO_PROXY='localhost',
        ):

            proxy = get_upstream_proxy({})

            http = proxy['http']
            self.assertEqual('http', http.scheme)
            self.assertEqual('username1', http.username)
            self.assertEqual('password1', http.password)
            self.assertEqual('server1:8888', http.hostport)

            https = proxy['https']
            self.assertEqual('https', https.scheme)
            self.assertEqual('username2', https.username)
            self.assertEqual('password2', https.password)
            self.assertEqual('server2:8888', https.hostport)

            self.assertEqual(['localhost'], proxy['no_proxy'])

    def test_merge(self):
        options = {'proxy': {'https': 'https://username3:password3@server3:8888', 'no_proxy': 'localhost'}}

        with self.set_env(
            HTTP_PROXY='http://username1:password1@server1:8888',
            HTTPS_PROXY='https://username2:password2@server2:8888',
            NO_PROXY='127.0.0.1',
        ):

            proxy = get_upstream_proxy(options)

            http = proxy['http']
            self.assertEqual('http', http.scheme)
            self.assertEqual('username1', http.username)
            self.assertEqual('password1', http.password)
            self.assertEqual('server1:8888', http.hostport)

            # The dict config overrides that defined in env variables
            https = proxy['https']
            self.assertEqual('https', https.scheme)
            self.assertEqual('username3', https.username)
            self.assertEqual('password3', https.password)
            self.assertEqual('server3:8888', https.hostport)

            self.assertEqual(['localhost'], proxy['no_proxy'])

    def test_empty_password(self):
        options = {
            'proxy': {
                'https': 'https://username:@server:8888',
            }
        }

        proxy = get_upstream_proxy(options)

        https = proxy['https']
        self.assertEqual('https', https.scheme)
        self.assertEqual('username', https.username)
        self.assertEqual('', https.password)
        self.assertEqual('server:8888', https.hostport)

    def test_no_proxy(self):
        options = {
            'proxy': {
                'https': 'https://username:@server:8888',
                'no_proxy': 'localhost:8081, example.com  , test.com:80',
            }
        }

        proxy = get_upstream_proxy(options)

        self.assertEqual(['localhost:8081', 'example.com', 'test.com:80'], proxy['no_proxy'])

    def test_no_proxy_as_list(self):
        options = {
            'proxy': {
                'https': 'https://username:@server:8888',
                'no_proxy': ['localhost:8081', 'example.com', 'test.com:80'],
            }
        }

        proxy = get_upstream_proxy(options)

        self.assertEqual(['localhost:8081', 'example.com', 'test.com:80'], proxy['no_proxy'])

    def test_none(self):
        options = None

        proxy = get_upstream_proxy(options)

        self.assertEqual({}, proxy)

    @contextlib.contextmanager
    def set_env(self, **environ):
        """Context manager used to temporarily set environment vars."""
        old_environ = dict(os.environ)
        os.environ.update(environ)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old_environ)


class ExtractCertTest(TestCase):
    @patch('seleniumwire.utils.os.getcwd')
    @patch('seleniumwire.utils.pkgutil')
    def test_extract_cert(self, mock_pkgutil, mock_getcwd):
        mock_pkgutil.get_data.return_value = b'cert_data'
        mock_getcwd.return_value = 'cwd'
        m_open = mock_open()

        with patch('seleniumwire.utils.open', m_open):
            extract_cert()

        mock_pkgutil.get_data.assert_called_once_with('seleniumwire', 'ca.crt')
        m_open.assert_called_once_with(Path('cwd', 'ca.crt'), 'wb')
        m_open.return_value.write.assert_called_once_with(b'cert_data')

    @patch('seleniumwire.utils.pkgutil')
    def test_extract_cert_not_found(self, mock_pkgutil):
        mock_pkgutil.get_data.side_effect = FileNotFoundError
        m_open = mock_open()

        with patch('seleniumwire.utils.open', m_open):
            extract_cert('foo.crt')

        mock_pkgutil.get_data.assert_called_once_with('seleniumwire', 'foo.crt')
        m_open.assert_not_called()

    @patch('seleniumwire.utils.os')
    @patch('seleniumwire.utils.pkgutil')
    @patch('seleniumwire.utils.Path')
    def test_extract_cert_and_key(self, mock_path, mock_pkgutil, mock_os):
        mock_path.return_value.exists.return_value = False
        mock_pkgutil.get_data.side_effect = (b'cert_data', b'key_data')
        m_open = mock_open()

        with patch('seleniumwire.utils.open', m_open):
            extract_cert_and_key(Path('some', 'path'))

        mock_os.makedirs.assert_called_once_with(Path('some', 'path'), exist_ok=True)
        mock_path.assert_called_once_with(Path('some', 'path'), 'seleniumwire-ca.pem')
        mock_pkgutil.get_data.assert_has_calls([call('seleniumwire', 'ca.crt'), call('seleniumwire', 'ca.key')])
        m_open.assert_called_once_with(mock_path.return_value, 'wb')
        m_open.return_value.write.assert_called_once_with(b'cert_datakey_data')

    @patch('seleniumwire.utils.os')
    @patch('seleniumwire.utils.Path')
    def test_extract_cert_and_key_exists(self, mock_path, mock_os):
        mock_path.return_value.exists.return_value = True
        m_open = mock_open()

        with patch('seleniumwire.utils.open', m_open):
            extract_cert_and_key(Path('some', 'path'))

        m_open.assert_not_called()

    @patch('seleniumwire.utils.os')
    @patch('seleniumwire.utils.Path')
    def test_extract_cert_and_key_no_check(self, mock_path, mock_os):
        mock_path.return_value.exists.return_value = True
        m_open = mock_open()

        with patch('seleniumwire.utils.open', m_open):
            extract_cert_and_key(Path('some', 'path'), check_exists=False)

        m_open.assert_called_once()


def test_urlsafe_address_ipv4():
    assert urlsafe_address(('192.168.0.1', 9999)) == ('192.168.0.1', 9999)


def test_urlsafe_address_ipv6():
    assert urlsafe_address(('::ffff:127.0.0.1', 9999, 0, 0)) == ('[::ffff:127.0.0.1]', 9999)


class DecodeTest(TestCase):
    def test_decode_gzip_data(self):
        data = b'test response body'
        io = BytesIO()

        with gzip.GzipFile(fileobj=io, mode='wb') as f:
            f.write(data)

        self.assertEqual(decode(io.getvalue(), 'gzip'), data)

    def test_decode_zlib_data(self):
        data = zlib.compress(b'test response body')

        self.assertEqual(decode(data, 'zlib'), data)

    def test_decode_error(self):
        data = b'test response body'

        self.assertEqual(decode(data, 'gzip'), data)

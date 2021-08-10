import functools
from unittest import TestCase
from unittest.mock import call, patch

from seleniumwire.server import MitmProxy


class MitmProxyTest(TestCase):

    base_options_update = functools.partial(
        call,
        confdir='/some/dir',
        listen_host='somehost',
        listen_port=12345,
        ssl_insecure=True,
        stream_websockets=True,
        suppress_connection_errors=True,
    )

    def test_creates_storage(self):
        proxy = MitmProxy(
            'somehost',
            12345,
            {
                'request_storage_base_dir': '/some/dir',
            },
        )

        self.assertEqual(self.mock_storage.create.return_value, proxy.storage)
        self.mock_storage.create.assert_called_once_with(memory_only=False, base_dir='/some/dir', maxsize=None)

    def test_creates_in_memory_storage(self):
        proxy = MitmProxy(
            'somehost',
            12345,
            {'request_storage_base_dir': '/some/dir', 'request_storage': 'memory', 'request_storage_max_size': 10},
        )

        self.assertEqual(self.mock_storage.create.return_value, proxy.storage)
        self.mock_storage.create.assert_called_once_with(memory_only=True, base_dir='/some/dir', maxsize=10)

    def test_extracts_cert(self):
        self.mock_storage.create.return_value.home_dir = '/some/dir/.seleniumwire'
        MitmProxy(
            'somehost',
            12345,
            {},
        )

        self.mock_extract_cert_and_key.assert_called_once_with('/some/dir/.seleniumwire')

    def test_creates_master(self):
        self.mock_storage.create.return_value.home_dir = '/some/dir/.seleniumwire'
        proxy = MitmProxy(
            'somehost',
            12345,
            {},
        )
        self.assertEqual(self.mock_master.return_value, proxy._master)
        self.mock_options.assert_called_once()
        self.mock_options.return_value.update.assert_has_calls(
            [
                self.base_options_update(
                    confdir='/some/dir/.seleniumwire',
                )
            ]
        )
        self.mock_master.assert_called_once_with(
            self.mock_asyncio.new_event_loop.return_value, self.mock_options.return_value
        )
        self.assertEqual(self.mock_proxy_server.return_value, self.mock_master.return_value.server)
        self.mock_proxy_config.assert_called_once_with(self.mock_options.return_value)
        self.mock_proxy_server.assert_called_once_with(self.mock_proxy_config.return_value)
        self.mock_master.return_value.addons.add.assert_has_calls(
            [call(), call(self.mock_logger.return_value), call(self.mock_handler.return_value)]
        )
        self.mock_addons.default_addons.assert_called_once_with()
        self.mock_handler.assert_called_once_with(proxy)

    def test_update_mitmproxy_options(self):
        MitmProxy('somehost', 12345, {'mitm_test': 'foobar'})

        self.mock_options.return_value.update.assert_has_calls(
            [
                self.base_options_update(
                    test='foobar',
                ),
            ]
        )

    def test_upstream_proxy(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {
                    'http': 'http://proxyserver:8080',
                    # We pick https when both are specified and the same
                    'https': 'https://proxyserver:8080',
                },
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [self.base_options_update(mode='upstream:https://proxyserver:8080')]
        )

    def test_upstream_proxy_single(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {
                    'http': 'http://proxyserver:8080',
                },
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [self.base_options_update(mode='upstream:http://proxyserver:8080')]
        )

    def test_upstream_proxy_auth(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {
                    'https': 'https://user:pass@proxyserver:8080',
                },
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [self.base_options_update(mode='upstream:https://proxyserver:8080', upstream_auth='user:pass')]
        )

    def test_upstream_proxy_auth_empty_pass(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {
                    'https': 'https://user:@proxyserver:8080',
                },
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [self.base_options_update(mode='upstream:https://proxyserver:8080', upstream_auth='user:')]
        )

    def test_upstream_proxy_custom_auth(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {'https': 'https://proxyserver:8080', 'custom_authorization': 'Bearer 12345'},
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [
                self.base_options_update(
                    mode='upstream:https://proxyserver:8080', upstream_custom_auth='Bearer 12345'
                ),
            ]
        )

    def test_upstream_proxy_different(self):
        with self.assertRaises(ValueError):
            MitmProxy(
                'somehost',
                12345,
                {
                    'proxy': {'http': 'http://proxyserver1:8080', 'https': 'https://proxyserver2:8080'},
                },
            )

    def test_upstream_proxy_no_proxy(self):
        MitmProxy(
            'somehost',
            12345,
            {
                'proxy': {'https': 'https://proxyserver:8080', 'no_proxy': 'localhost:9090, example.com'},
            },
        )

        self.mock_options.return_value.update.assert_has_calls(
            [
                self.base_options_update(
                    mode='upstream:https://proxyserver:8080', no_proxy=['localhost:9090', 'example.com']
                ),
            ]
        )

    def test_disable_capture(self):
        proxy = MitmProxy('somehost', 12345, {'disable_capture': True})

        self.assertEqual(['$^'], proxy.scopes)

    def test_new_event_loop(self):
        proxy = MitmProxy(
            'somehost',
            12345,
            {},
        )

        self.assertEqual(self.mock_asyncio.new_event_loop.return_value, proxy._event_loop)
        self.mock_asyncio.new_event_loop.assert_called_once_with()

    def test_serve_forever(self):
        proxy = MitmProxy(
            'somehost',
            12345,
            {},
        )

        proxy.serve_forever()

        self.mock_asyncio.set_event_loop.assert_called_once_with(proxy._event_loop)
        self.mock_master.return_value.run_loop.assert_called_once_with(proxy._event_loop)

    def test_address(self):
        self.mock_proxy_server.return_value.address = ('somehost', 12345)
        proxy = MitmProxy(
            'somehost',
            12345,
            {},
        )

        self.assertEqual(('somehost', 12345), proxy.address())

    def test_shutdown(self):
        proxy = MitmProxy(
            'somehost',
            12345,
            {},
        )

        proxy.shutdown()

        self.mock_master.return_value.shutdown.assert_called_once_with()
        self.mock_storage.create.return_value.cleanup.assert_called_once_with()

    def setUp(self):
        patcher = patch('seleniumwire.server.storage')
        self.mock_storage = patcher.start()
        self.mock_storage.create.return_value.home_dir = '/some/dir'
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.Options')
        self.mock_options = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.Master')
        self.mock_master = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.ProxyConfig')
        self.mock_proxy_config = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.ProxyServer')
        self.mock_proxy_server = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.SendToLogger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.addons')
        self.mock_addons = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.InterceptRequestHandler')
        self.mock_handler = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.asyncio')
        self.mock_asyncio = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('seleniumwire.server.extract_cert_and_key')
        self.mock_extract_cert_and_key = patcher.start()
        self.addCleanup(patcher.stop)

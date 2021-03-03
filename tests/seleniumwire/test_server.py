import functools
from unittest import TestCase
from unittest.mock import call, patch

from seleniumwire.server import MitmProxy


class MitmProxyTest(TestCase):

    base_options_update = functools.partial(
        call,
        ssl_insecure=True,
        upstream_cert=False,
        stream_websockets=True,
        suppress_connection_errors=True,
    )

    def test_creates_storage(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.assertEqual(self.mock_storage.return_value, proxy.storage)
        self.mock_storage.assert_called_once_with(base_dir='/some/dir')

    def test_extracts_cert(self):
        self.mock_storage.return_value.home_dir = '/some/dir/.seleniumwire'
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.mock_extract_cert_and_key.assert_called_once_with('/some/dir/.seleniumwire')

    def test_creates_master(self):
        self.mock_storage.return_value.home_dir = '/some/dir/.seleniumwire'
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })
        self.assertEqual(self.mock_master.return_value, proxy._master)
        self.mock_options.assert_called_once_with(
            confdir='/some/dir/.seleniumwire',
            listen_host='somehost',
            listen_port=12345
        )
        self.mock_master.assert_called_once_with(
            self.mock_asyncio.new_event_loop.return_value,
            self.mock_options.return_value
        )
        self.assertEqual(self.mock_proxy_server.return_value, self.mock_master.return_value.server)
        self.mock_proxy_config.assert_called_once_with(self.mock_options.return_value)
        self.mock_proxy_server.assert_called_once_with(self.mock_proxy_config.return_value)
        self.mock_master.return_value.addons.add.assert_has_calls([
            call(),
            call(self.mock_logger.return_value),
            call(self.mock_handler.return_value)
        ])
        self.mock_addons.default_addons.assert_called_once_with()
        self.mock_handler.assert_called_once_with(proxy)

    def test_update_mitmproxy_options(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'mitm_test': 'foobar'
        })

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(),
            call(
                test='foobar'
            )
        ])

    def test_update_mitmproxy_options_with_override(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'mitm_test': 'foobar',
            'mitm_confdir': '/tmp/dir'
        })

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(),
            call(
                test='foobar',
                confdir='/tmp/dir'
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

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
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

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
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

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
                mode='upstream:https://proxyserver:8080',
                upstream_auth='user:pass'
            ),
            call()
        ])

    def test_upstream_proxy_auth_empty_pass(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'https': 'https://user:@proxyserver:8080',
            }
        })

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
                mode='upstream:https://proxyserver:8080',
                upstream_auth='user:'
            ),
            call()
        ])

    def test_upstream_proxy_custom_auth(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'https': 'https://proxyserver:8080',
                'custom_authorization': 'Bearer 12345'
            }
        })

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
                mode='upstream:https://proxyserver:8080',
                upstream_custom_auth='Bearer 12345'
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

    def test_upstream_proxy_no_proxy(self):
        MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'proxy': {
                'https': 'https://proxyserver:8080',
                'no_proxy': 'localhost:9090, example.com'
            }
        })

        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(
                mode='upstream:https://proxyserver:8080',
                no_proxy=['localhost:9090', 'example.com']
            ),
            call()
        ])

    def test_disable_capture(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
            'disable_capture': True
        })

        self.assertEqual(['$^'], proxy.scopes)
        self.mock_options.return_value.update.assert_has_calls([
            self.base_options_update(),
            call(
                ignore_hosts=['.*']
            )
        ])

    def test_new_event_loop(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        self.assertEqual(self.mock_asyncio.new_event_loop.return_value, proxy._event_loop)
        self.mock_asyncio.new_event_loop.assert_called_once_with()

    def test_serve_forever(self):
        proxy = MitmProxy('somehost', 12345, {
            'request_storage_base_dir': '/some/dir',
        })

        proxy.serve_forever()

        self.mock_asyncio.set_event_loop.assert_called_once_with(proxy._event_loop)
        self.mock_master.return_value.run_loop.assert_called_once_with(proxy._event_loop)

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
        patcher = patch('seleniumwire.server.RequestStorage')
        self.mock_storage = patcher.start()
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

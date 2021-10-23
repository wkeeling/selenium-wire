from unittest.mock import patch

import pytest
from selenium.webdriver.common.proxy import ProxyType

from seleniumwire.webdriver import Firefox


@pytest.fixture(autouse=True)
def mock_backend():
    with patch('seleniumwire.webdriver.backend') as mock_backend:
        mock_backend.create.return_value.address.return_value = ('127.0.0.1', 12345)
        yield mock_backend


@pytest.fixture(autouse=True)
def firefox_super_kwargs():
    with patch('seleniumwire.webdriver._Firefox.__init__') as base_init:
        kwargs = {}
        base_init.side_effect = lambda *a, **k: kwargs.update(k)
        yield kwargs


class TestFirefoxWebdriver:
    def test_create_backend(self, mock_backend):
        firefox = Firefox()

        assert firefox.backend
        mock_backend.create.assert_called_once_with(port=0, options={})
        mock_backend.create.return_value.address.assert_called_once_with()

    def test_allow_hijacking_localhost(self, firefox_super_kwargs):
        Firefox()

        firefox_options = firefox_super_kwargs['options']
        assert firefox_options.preferences['network.proxy.allow_hijacking_localhost'] is True

    def test_set_capabilities(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', False):
            Firefox()

        capabilties = firefox_super_kwargs['capabilities']

        assert capabilties['proxy']['proxyType'] == 'manual'
        assert capabilties['proxy']['httpProxy'] == '127.0.0.1:12345'
        assert capabilties['proxy']['sslProxy'] == '127.0.0.1:12345'
        assert 'noProxy' not in capabilties['proxy']
        assert capabilties['acceptInsecureCerts'] is True
        assert firefox_super_kwargs['options'].proxy is None

    def test_set_capabilities_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', True):
            Firefox()

        capabilties = firefox_super_kwargs['capabilities']
        proxy = firefox_super_kwargs['options'].proxy

        assert proxy.proxyType == ProxyType.MANUAL
        assert proxy.httpProxy == '127.0.0.1:12345'
        assert proxy.sslProxy == '127.0.0.1:12345'
        assert proxy.noProxy == ''
        assert capabilties['acceptInsecureCerts'] is True

    def test_no_proxy(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', False):
            Firefox(seleniumwire_options={'exclude_hosts': 'test_host'})

        capabilties = firefox_super_kwargs['capabilities']

        assert capabilties['proxy']['noProxy'] == 'test_host'

    def test_no_proxy_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', True):
            Firefox(seleniumwire_options={'exclude_hosts': 'test_host'})

        proxy = firefox_super_kwargs['options'].proxy

        assert proxy.noProxy == 'test_host'

    def test_existing_capability(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', False):
            Firefox(desired_capabilities={'test': 'capability'})

        capabilties = firefox_super_kwargs['capabilities']

        assert 'proxy' in capabilties
        assert capabilties['test'] == 'capability'

    def test_no_auto_config(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.USING_SELENIUM_V4', False):
            Firefox(seleniumwire_options={'auto_config': False}, capabilities={'test': 'capability'})

            capabilties = firefox_super_kwargs['capabilities']

            assert 'proxy' not in capabilties
            assert capabilties['test'] == 'capability'

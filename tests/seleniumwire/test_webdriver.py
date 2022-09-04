from unittest.mock import patch

import pytest
from selenium.webdriver import chrome
from selenium.webdriver.common.proxy import ProxyType

from seleniumwire.webdriver import Chrome, ChromeOptions, Firefox, Safari


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


@pytest.fixture(autouse=True)
def chrome_super_kwargs():
    with patch('seleniumwire.webdriver._Chrome.__init__') as base_init:
        kwargs = {}
        base_init.side_effect = lambda *a, **k: kwargs.update(k)
        yield kwargs


class TestFirefoxWebDriver:
    def test_create_backend(self, mock_backend):
        firefox = Firefox()

        assert firefox.backend
        mock_backend.create.assert_called_once_with(addr='127.0.0.1', port=0, options={})
        mock_backend.create.return_value.address.assert_called_once_with()

    def test_pass_backend(self):
        from seleniumwire import backend
        with patch.object(backend, "create") as mock_create:
            mock_create.return_value.address.return_value = ('127.0.0.1', 12345)
            mitm_proxy = backend.create(addr='127.0.0.1', port=0, options={})
            firefox = Firefox(mitm_proxy=mitm_proxy)

        assert firefox.backend
        mock_create.assert_called_once_with(addr='127.0.0.1', port=0, options={})
        mock_create.return_value.address.assert_called_once_with()

    def test_allow_hijacking_localhost(self, firefox_super_kwargs):
        Firefox()

        firefox_options = firefox_super_kwargs['options']
        assert firefox_options.preferences['network.proxy.allow_hijacking_localhost'] is True

    def test_accept_insecure_certs(self, firefox_super_kwargs):
        Firefox()

        firefox_options = firefox_super_kwargs['options']
        assert firefox_options.accept_insecure_certs is True

    def test_set_proxy_config(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', False):
            Firefox()

        capabilties = firefox_super_kwargs['capabilities']

        assert capabilties['proxy']['proxyType'] == 'manual'
        assert capabilties['proxy']['httpProxy'] == '127.0.0.1:12345'
        assert capabilties['proxy']['sslProxy'] == '127.0.0.1:12345'
        assert 'noProxy' not in capabilties['proxy']
        assert capabilties['acceptInsecureCerts'] is True
        assert firefox_super_kwargs['options'].proxy is None

    def test_set_proxy_config_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', True):
            Firefox()

        proxy = firefox_super_kwargs['options'].proxy

        assert proxy.proxyType == ProxyType.MANUAL
        assert proxy.httpProxy == '127.0.0.1:12345'
        assert proxy.sslProxy == '127.0.0.1:12345'
        assert proxy.noProxy == ''

    def test_no_proxy(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', False):
            Firefox(seleniumwire_options={'exclude_hosts': 'test_host'})

        capabilties = firefox_super_kwargs['capabilities']

        assert capabilties['proxy']['noProxy'] == 'test_host'

    def test_no_proxy_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', True):
            Firefox(seleniumwire_options={'exclude_hosts': 'test_host'})

        proxy = firefox_super_kwargs['options'].proxy

        assert proxy.noProxy == 'test_host'

    def test_existing_capability(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', False):
            Firefox(desired_capabilities={'test': 'capability'})

        capabilties = firefox_super_kwargs['capabilities']

        assert capabilties['test'] == 'capability'

    def test_existing_capability_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', True):
            Firefox(desired_capabilities={'test': 'capability'})

        capabilties = firefox_super_kwargs['desired_capabilities']

        assert capabilties['test'] == 'capability'

    def test_no_auto_config(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', False):
            Firefox(seleniumwire_options={'auto_config': False}, capabilities={'test': 'capability'})

            capabilties = firefox_super_kwargs['capabilities']

            assert 'proxy' not in capabilties

    def test_no_auto_config_v4(self, firefox_super_kwargs):
        with patch('seleniumwire.webdriver.SELENIUM_V4', True):
            Firefox(seleniumwire_options={'auto_config': False}, capabilities={'test': 'capability'})

            assert firefox_super_kwargs['options'].proxy is None


class TestChromeWebDriver:
    def test_create_backend(self, mock_backend):
        chrome = Chrome()

        assert chrome.backend
        mock_backend.create.assert_called_once_with(addr='127.0.0.1', port=0, options={})
        mock_backend.create.return_value.address.assert_called_once_with()

    def test_pass_backend(self):
        from seleniumwire import backend
        with patch.object(backend, "create") as mock_create:
            mock_create.return_value.address.return_value = ('127.0.0.1', 12345)
            mitm_proxy = backend.create(addr='127.0.0.1', port=0, options={})
            chrome = Chrome(mitm_proxy=mitm_proxy)

        assert chrome.backend
        mock_create.assert_called_once_with(addr='127.0.0.1', port=0, options={})
        mock_create.return_value.address.assert_called_once_with()

    def test_proxy_bypass_list(self, chrome_super_kwargs):
        Chrome()

        chrome_options = chrome_super_kwargs['options']
        assert '--proxy-bypass-list=<-loopback>' in chrome_options.arguments

    def test_accept_insecure_certs(self, chrome_super_kwargs):
        Chrome()

        chrome_options = chrome_super_kwargs['options']
        assert 'acceptInsecureCerts' in chrome_options.capabilities

    def test_set_proxy_config(self, chrome_super_kwargs):
        Chrome()

        options = chrome_super_kwargs['options']

        assert options.capabilities['proxy']['proxyType'] == 'manual'
        assert options.capabilities['proxy']['httpProxy'] == '127.0.0.1:12345'
        assert options.capabilities['proxy']['sslProxy'] == '127.0.0.1:12345'
        assert 'noProxy' not in options.capabilities['proxy']
        assert options.capabilities['acceptInsecureCerts'] is True

    def test_no_proxy(self, chrome_super_kwargs):
        Chrome(seleniumwire_options={'exclude_hosts': 'test_host'})

        options = chrome_super_kwargs['options']

        assert options.capabilities['proxy']['noProxy'] == 'test_host'

    def test_existing_capability(self, chrome_super_kwargs):
        Chrome(desired_capabilities={'test': 'capability'})

        capabilties = chrome_super_kwargs['desired_capabilities']

        assert capabilties['test'] == 'capability'

    def test_no_auto_config(self, chrome_super_kwargs):
        Chrome(seleniumwire_options={'auto_config': False}, capabilities={'test': 'capability'})

        assert 'proxy' not in chrome_super_kwargs['options'].capabilities

    def test_chrome_options(self, chrome_super_kwargs):
        options = ChromeOptions()
        Chrome(chrome_options=options, seleniumwire_options={})

        assert 'chrome_options' not in chrome_super_kwargs
        assert chrome_super_kwargs['options'] == options

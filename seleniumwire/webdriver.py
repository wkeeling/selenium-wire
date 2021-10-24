from typing import Any, Dict

import selenium
from packaging import version
from selenium.webdriver import ActionChains  # noqa
from selenium.webdriver import FirefoxOptions  # noqa
from selenium.webdriver import FirefoxProfile  # noqa
from selenium.webdriver import Proxy  # noqa
from selenium.webdriver import TouchActions  # noqa
from selenium.webdriver import Chrome as _Chrome
from selenium.webdriver import ChromeOptions, DesiredCapabilities
from selenium.webdriver import Edge as _Edge
from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver import Remote as _Remote
from selenium.webdriver import Safari as _Safari

from seleniumwire import backend
from seleniumwire.inspect import InspectRequestsMixin
from seleniumwire.utils import build_proxy_args, get_upstream_proxy, urlsafe_address

SELENIUM_V4 = version.parse(getattr(selenium, '__version__', '0')) >= version.parse('4.0.0')


class DriverCommonMixin:
    """Operations common to all webdriver types."""

    def _setup_backend(self, seleniumwire_options: Dict[str, Any]) -> Dict[str, Any]:
        """Create the backend proxy server and return its configuration
        in a dictionary.
        """
        self.backend = backend.create(
            addr=seleniumwire_options.pop('addr', '127.0.0.1'),
            port=seleniumwire_options.get('port', 0),
            options=seleniumwire_options,
        )

        addr, port = urlsafe_address(self.backend.address())

        config = {
            'proxy': {
                'proxyType': 'manual',
                'httpProxy': '{}:{}'.format(addr, port),
                'sslProxy': '{}:{}'.format(addr, port),
            }
        }

        if 'exclude_hosts' in seleniumwire_options:
            # Only pass noProxy when we have a value to pass
            config['proxy']['noProxy'] = seleniumwire_options['exclude_hosts']

        config['acceptInsecureCerts'] = True

        return config

    def quit(self):
        """Shutdown Selenium Wire and then quit the webdriver."""
        self.backend.shutdown()
        super().quit()

    @property
    def proxy(self) -> Dict[str, Any]:
        """Get the proxy configuration for the driver."""

        conf = {}
        mode = getattr(self.backend.master.options, 'mode')

        if mode and mode.startswith('upstream'):
            upstream = mode.split('upstream:')[1]
            scheme, *rest = upstream.split('://')

            auth = getattr(self.backend.master.options, 'upstream_auth')

            if auth:
                conf[scheme] = f'{scheme}://{auth}@{rest[0]}'
            else:
                conf[scheme] = f'{scheme}://{rest[0]}'

        no_proxy = getattr(self.backend.master.options, 'no_proxy')

        if no_proxy:
            conf['no_proxy'] = ','.join(no_proxy)

        custom_auth = getattr(self.backend.master.options, 'upstream_custom_auth')

        if custom_auth:
            conf['custom_authorization'] = custom_auth

        return conf

    @proxy.setter
    def proxy(self, proxy_conf: Dict[str, Any]):
        """Set the proxy configuration for the driver.

        The configuration should be a dictionary:

        webdriver.proxy = {
            'https': 'https://user:pass@server:port',
            'no_proxy': 'localhost,127.0.0.1',
        }

        Args:
            proxy_conf: The proxy configuration.
        """
        self.backend.master.options.update(**build_proxy_args(get_upstream_proxy({'proxy': proxy_conf})))


class Firefox(InspectRequestsMixin, DriverCommonMixin, _Firefox):
    """Extends the Firefox webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Firefox WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        try:
            firefox_options = kwargs['options']
        except KeyError:
            firefox_options = FirefoxOptions()
            kwargs['options'] = firefox_options

        # Prevent Firefox from bypassing the Selenium Wire proxy
        # for localhost addresses.
        firefox_options.set_preference('network.proxy.allow_hijacking_localhost', True)
        firefox_options.accept_insecure_certs = True

        config = self._setup_backend(seleniumwire_options)

        if seleniumwire_options.get('auto_config', True):
            if SELENIUM_V4:
                # From Selenium v4.0.0 the browser's proxy settings can no longer
                # be passed using desired capabilities and we must use the options
                # object instead.
                proxy = Proxy()
                proxy.http_proxy = config['proxy']['httpProxy']
                proxy.ssl_proxy = config['proxy']['sslProxy']

                try:
                    proxy.no_proxy = config['proxy']['noProxy']
                except KeyError:
                    pass

                firefox_options.proxy = proxy
            else:
                # Earlier versions of Selenium use capabilities to pass the settings.
                capabilities = kwargs.get('capabilities', kwargs.get('desired_capabilities'))
                if capabilities is None:
                    capabilities = DesiredCapabilities.FIREFOX
                capabilities = capabilities.copy()

                capabilities.update(config)
                kwargs['capabilities'] = capabilities

        super().__init__(*args, **kwargs)


class Chrome(InspectRequestsMixin, DriverCommonMixin, _Chrome):
    """Extends the Chrome webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Chrome WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        try:
            chrome_options = kwargs['options']
        except KeyError:
            chrome_options = ChromeOptions()

        # Prevent Chrome from bypassing the Selenium Wire proxy
        # for localhost addresses.
        chrome_options.add_argument('--proxy-bypass-list=<-loopback>')
        kwargs['options'] = chrome_options

        config = self._setup_backend(seleniumwire_options)

        if seleniumwire_options.get('auto_config', True):
            for key, value in config.items():
                chrome_options.set_capability(key, value)

        super().__init__(*args, **kwargs)


class Safari(InspectRequestsMixin, DriverCommonMixin, _Safari):
    """Extends the Safari webdriver to provide additional methods for inspecting requests."""

    def __init__(self, seleniumwire_options=None, *args, **kwargs):
        """Initialise a new Safari WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        # Safari does not support automatic proxy configuration through the
        # DesiredCapabilities API, and thus has to be configured manually.
        # Whatever port number is chosen for that manual configuration has to
        # be passed in the options.
        assert 'port' in seleniumwire_options, 'You must set a port number in the seleniumwire_options'

        self._setup_backend(seleniumwire_options)

        super().__init__(*args, **kwargs)


class Edge(InspectRequestsMixin, DriverCommonMixin, _Edge):
    """Extends the Edge webdriver to provide additional methods for inspecting requests."""

    def __init__(self, seleniumwire_options=None, *args, **kwargs):
        """Initialise a new Edge WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        # Edge does not support automatic proxy configuration through the
        # DesiredCapabilities API, and thus has to be configured manually.
        # Whatever port number is chosen for that manual configuration has to
        # be passed in the options.
        assert 'port' in seleniumwire_options, 'You must set a port number in the seleniumwire_options'

        self._setup_backend(seleniumwire_options)

        super().__init__(*args, **kwargs)


class Remote(InspectRequestsMixin, DriverCommonMixin, _Remote):
    """Extends the Remote webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Firefox WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        config = self._setup_backend(seleniumwire_options)

        if seleniumwire_options.get('auto_config', True):
            capabilities = kwargs.get('desired_capabilities')
            if capabilities is None:
                capabilities = DesiredCapabilities.FIREFOX.copy()
            else:
                capabilities = capabilities.copy()

            capabilities.update(config)

            kwargs['desired_capabilities'] = capabilities

        super().__init__(*args, **kwargs)

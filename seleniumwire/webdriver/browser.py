from selenium.webdriver import Chrome as _Chrome
from selenium.webdriver import Edge as _Edge
from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver import Safari as _Safari
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from ..proxy.client import AdminClient
from .request import InspectRequestsMixin


class Firefox(InspectRequestsMixin, _Firefox):
    """Extends the Firefox webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Firefox WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        self._client = AdminClient()
        addr, port = self._client.create_proxy(
            port=seleniumwire_options.pop('port', 0),
            proxy_config=seleniumwire_options.pop('proxy', None),
            options=seleniumwire_options
        )

        if 'port' not in seleniumwire_options:  # Auto config mode
            try:
                capabilities = kwargs.pop('desired_capabilities')
            except KeyError:
                capabilities = DesiredCapabilities.FIREFOX.copy()

            capabilities['proxy'] = {
                'proxyType': 'manual',
                'httpProxy': '{}:{}'.format(addr, port),
                'sslProxy': '{}:{}'.format(addr, port),
                'noProxy': [],
            }
            capabilities['acceptInsecureCerts'] = True

            kwargs['capabilities'] = capabilities

        super().__init__(*args, **kwargs)

    def quit(self):
        self._client.destroy_proxy()
        super().quit()


class Chrome(InspectRequestsMixin, _Chrome):
    """Extends the Chrome webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Chrome WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        self._client = AdminClient()
        addr, port = self._client.create_proxy(
            port=seleniumwire_options.pop('port', 0),
            proxy_config=seleniumwire_options.pop('proxy', None),
            options=seleniumwire_options
        )

        if 'port' not in seleniumwire_options:  # Auto config mode
            try:
                capabilities = kwargs.pop('desired_capabilities')
            except KeyError:
                capabilities = DesiredCapabilities.CHROME.copy()

            capabilities['proxy'] = {
                'proxyType': 'manual',
                'httpProxy': '{}:{}'.format(addr, port),
                'sslProxy': '{}:{}'.format(addr, port),
                'noProxy': ''
            }
            capabilities['acceptInsecureCerts'] = True

            kwargs['desired_capabilities'] = capabilities

        super().__init__(*args, **kwargs)

    def quit(self):
        self._client.destroy_proxy()
        super().quit()


class Safari(InspectRequestsMixin, _Safari):
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

        self._client = AdminClient()
        self._client.create_proxy(
            port=seleniumwire_options.pop('port', 0),
            proxy_config=seleniumwire_options.pop('proxy', None),
            options=seleniumwire_options
        )

        super().__init__(*args, **kwargs)

    def quit(self):
        self._client.destroy_proxy()
        super().quit()


class Edge(InspectRequestsMixin, _Edge):
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

        self._client = AdminClient()
        self._client.create_proxy(
            port=seleniumwire_options.pop('port', 0),
            proxy_config=seleniumwire_options.pop('proxy', None),
            options=seleniumwire_options
        )

        super().__init__(*args, **kwargs)

    def quit(self):
        self._client.destroy_proxy()
        super().quit()

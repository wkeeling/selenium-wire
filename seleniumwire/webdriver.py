from selenium.webdriver import Chrome as _Chrome
from selenium.webdriver import ChromeOptions
from selenium.webdriver import Edge as _Edge
from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver import Remote as _Remote
from selenium.webdriver import Safari as _Safari
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from . import backend
from .inspect import InspectRequestsMixin


class DriverCommonMixin:
    """Operations common to all webdriver types."""

    def quit(self):
        """Shutdown Selenium Wire and then quit the webdriver."""
        self.proxy.shutdown()
        super().quit()


class Firefox(InspectRequestsMixin, DriverCommonMixin, _Firefox):
    """Extends the Firefox webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, seleniumwire_options=None, **kwargs):
        """Initialise a new Firefox WebDriver instance.

        Args:
            seleniumwire_options: The seleniumwire options dictionary.
        """
        if seleniumwire_options is None:
            seleniumwire_options = {}

        self.proxy = backend.create(
            port=seleniumwire_options.get('port', 0),
            options=seleniumwire_options
        )

        if 'port' not in seleniumwire_options:  # Auto config mode
            try:
                capabilities = dict(kwargs.pop('desired_capabilities'))
            except KeyError:
                capabilities = DesiredCapabilities.FIREFOX.copy()

            addr, port = urlsafe_address(self.proxy.address())

            capabilities['proxy'] = {
                'proxyType': 'manual',
                'httpProxy': '{}:{}'.format(addr, port),
                'sslProxy': '{}:{}'.format(addr, port),
                'noProxy': seleniumwire_options.pop('exclude_hosts', []),
            }
            capabilities['acceptInsecureCerts'] = True

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

        self.proxy = backend.create(
            port=seleniumwire_options.get('port', 0),
            options=seleniumwire_options
        )

        if 'port' not in seleniumwire_options:  # Auto config mode
            try:
                capabilities = dict(kwargs.pop('desired_capabilities'))
            except KeyError:
                capabilities = DesiredCapabilities.CHROME.copy()

            addr, port = urlsafe_address(self.proxy.address())

            capabilities['proxy'] = {
                'proxyType': 'manual',
                'httpProxy': '{}:{}'.format(addr, port),
                'sslProxy': '{}:{}'.format(addr, port),
                'noProxy': ','.join(seleniumwire_options.pop('exclude_hosts', []))
            }
            capabilities['acceptInsecureCerts'] = True

            kwargs['desired_capabilities'] = capabilities

        try:
            chrome_options = kwargs.pop('options')
        except KeyError:
            chrome_options = ChromeOptions()

        # Prevent Chrome from bypassing the Selenium Wire proxy
        # for localhost addresses.
        chrome_options.add_argument('proxy-bypass-list=<-loopback>')
        kwargs['options'] = chrome_options

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

        self.proxy = backend.create(
            port=seleniumwire_options.pop('port', 0),
            options=seleniumwire_options
        )

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

        self.proxy = backend.create(
            port=seleniumwire_options.pop('port', 0),
            options=seleniumwire_options
        )

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

        self.proxy = backend.create(
            addr=seleniumwire_options.pop('addr'),
            port=seleniumwire_options.get('port', 0),
            options=seleniumwire_options
        )

        if "port" not in seleniumwire_options:  # Auto config mode
            try:
                capabilities = dict(kwargs.pop("desired_capabilities"))
            except KeyError:
                capabilities = DesiredCapabilities.FIREFOX.copy()

            addr, port = urlsafe_address(self.proxy.address())

            capabilities["proxy"] = {
                "proxyType": "manual",
                "httpProxy": "{}:{}".format(addr, port),
                "sslProxy": "{}:{}".format(addr, port),
                "noProxy": seleniumwire_options.pop('exclude_hosts', []),
            }
            capabilities["acceptInsecureCerts"] = True

            kwargs["desired_capabilities"] = capabilities

        super().__init__(*args, **kwargs)


def urlsafe_address(address):
    """Make an address safe to use in a URL.

    Args:
        address: A tuple of address information.
    Returns:
        A 2-tuple of url-safe (address, port)
    """
    addr, port, *rest = address

    if rest:
        # An IPv6 address needs to be surrounded by square brackets
        addr = f'[{addr}]'

    return addr, port

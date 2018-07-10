from selenium.webdriver import Chrome as _Chrome
from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver import Safari as _Safari
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .request import InspectRequestsMixin


class Firefox(InspectRequestsMixin, _Firefox):
    """Wraps the Firefox webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, **kwargs):
        try:
            port = kwargs.pop('seleniumwire_port')
        except KeyError:
            port = 0

        host, port = self._client.create_proxy(port)

        try:
            capabilities = kwargs.pop('capabilities')
        except KeyError:
            capabilities = DesiredCapabilities.FIREFOX.copy()

        capabilities['proxy'] = {
            'proxyType': 'manual',
            'httpProxy': '{}:{}'.format(host, port),
            'sslProxy': '{}:{}'.format(host, port),
            'noProxy': [],
        }
        capabilities['acceptInsecureCerts'] = True

        super().__init__(*args, capabilities=capabilities, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()


class Chrome(InspectRequestsMixin, _Chrome):
    """Wraps the Chrome webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, **kwargs):
        try:
            port = kwargs.pop('seleniumwire_port')
        except KeyError:
            port = 0

        host, port = self._client.create_proxy(port)

        try:
            capabilities = kwargs.pop('capabilities')
        except KeyError:
            capabilities = DesiredCapabilities.CHROME.copy()

        capabilities['proxy'] = {
            'proxyType': 'manual',
            'httpProxy': '{}:{}'.format(host, port),
            'sslProxy': '{}:{}'.format(host, port),
            'noProxy': ''
        }
        capabilities['acceptInsecureCerts'] = True

        super().__init__(*args, desired_capabilities=capabilities, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()


class Safari(InspectRequestsMixin, _Safari):
    """Wraps the Safari webdriver to provide additional methods for inspecting requests."""

    def __init__(self, seleniumwire_port, *args, **kwargs):
        """Initialise a new Safari WebDriver instance with the port number to use
        for the selenium wire proxy server.

        Safari does not support automatic proxy configuration through the
        DesiredCapabilities API, and thus it is necessary to do this manually
        with a specific port number. Whatever port number was chosen is then
        passed in here.

        Args:
            seleniumwire_port: The port number that selenium wire should use.
                Safari must have its proxy configured manually using this
                same port number.
        """
        self._client.create_proxy(seleniumwire_port)

        super().__init__(*args, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()

from selenium.webdriver import Chrome as _Chrome
from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .request import InspectRequestsMixin
from seleniumwire.proxy.client import AdminClient


class Firefox(InspectRequestsMixin, _Firefox):
    """Wraps the Firefox webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, **kwargs):
        self._client = AdminClient()
        host, port = self._create_proxy()

        try:
            capabilities = kwargs.pop('capabilities')
        except KeyError:
            capabilities = DesiredCapabilities.FIREFOX.copy()

        capabilities['proxy'] = {
            'proxyType': 'manual',
            'httpProxy': '{}:{}'.format(host, port),
            'sslProxy': '{}:{}'.format(host, port),
            'noProxy': []
        }

        super().__init__(*args, capabilities=capabilities, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()


class Chrome(InspectRequestsMixin, _Chrome):
    """Wraps the Chrome webdriver to provide additional methods for inspecting requests."""

    def __init__(self, *args, **kwargs):
        self._client = AdminClient()
        host, port = self._create_proxy()

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

        super().__init__(*args, desired_capabilities=capabilities, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()

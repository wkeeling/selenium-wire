from selenium.webdriver import Firefox as _Firefox
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .request import InspectRequestsMixin


class Firefox(InspectRequestsMixin, _Firefox):

    def __init__(self, *args, **kwargs):
        addr, port = self._create_proxy()

        capabilities = DesiredCapabilities.FIREFOX.copy()
        capabilities['proxy'] = {
            'proxyType': 'manual',
            'httpProxy': '{}:{}'.format(addr, port),
            'sslProxy': '{}:{}'.format(addr, port),
            'noProxy': []
        }

        super().__init__(*args, capabilities=capabilities, **kwargs)

    def quit(self):
        self._destroy_proxy()
        super().quit()


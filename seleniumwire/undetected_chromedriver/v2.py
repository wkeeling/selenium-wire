import logging

from selenium.webdriver import DesiredCapabilities
import undetected_chromedriver.v2 as uc

from seleniumwire import backend
from seleniumwire.inspect import InspectRequestsMixin
from seleniumwire.utils import urlsafe_address
from seleniumwire.webdriver import DriverCommonMixin

log = logging.getLogger(__name__)


class Chrome(InspectRequestsMixin, DriverCommonMixin, uc.Chrome):
    """Extends the undetected_chrome Chrome webdriver to provide additional
    methods for inspecting requests."""

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

        if seleniumwire_options.get('auto_config', True):
            capabilities = kwargs.get('desired_capabilities')
            if capabilities is None:
                capabilities = DesiredCapabilities.CHROME

            capabilities = self._configure(capabilities, seleniumwire_options)

            kwargs['desired_capabilities'] = capabilities

        try:
            chrome_options = kwargs['options']
        except KeyError:
            chrome_options = ChromeOptions()

        # Prevent Chrome from bypassing the Selenium Wire proxy
        # for localhost addresses.
        chrome_options.add_argument('--proxy-bypass-list=<-loopback>')

        log.info('Using undetected_chromedriver.v2')

        # We need to point Chrome back to Selenium Wire since the executable
        # will be started separately by undetected_chromedriver.
        addr, port = urlsafe_address(self.proxy.address())
        chrome_options.add_argument(f'--proxy-server={addr}:{port}')

        kwargs['options'] = chrome_options

        super().__init__(*args, **kwargs)


ChromeOptions = uc.ChromeOptions  # noqa: F811

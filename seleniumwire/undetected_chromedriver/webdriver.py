import logging

from selenium.webdriver import DesiredCapabilities

try:
    import undetected_chromedriver as uc
except ImportError as e:
    raise ImportError(
        'undetected_chromedriver not found. ' 'Install it with `pip install undetected_chromedriver`.'
    ) from e

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

        config = self._setup_backend(seleniumwire_options)

        if seleniumwire_options.get('auto_config', True):
            capabilities = kwargs.get('desired_capabilities')
            if capabilities is None:
                capabilities = DesiredCapabilities.CHROME
            capabilities = capabilities.copy()

            capabilities.update(config)

            kwargs['desired_capabilities'] = capabilities

        try:
            chrome_options = kwargs['options']
        except KeyError:
            chrome_options = ChromeOptions()

        log.info('Using undetected_chromedriver')

        # We need to point Chrome back to Selenium Wire since the executable
        # will be started separately by undetected_chromedriver.
        addr, port = urlsafe_address(self.backend.address())
        chrome_options.add_argument(f'--proxy-server={addr}:{port}')
        chrome_options.add_argument(
            f"--proxy-bypass-list={','.join(seleniumwire_options.get('exclude_hosts', ['<-loopback>']))}"
        )

        kwargs['options'] = chrome_options

        super().__init__(*args, **kwargs)


ChromeOptions = uc.ChromeOptions  # noqa: F811

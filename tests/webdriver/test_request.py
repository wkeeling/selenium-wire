from unittest import TestCase
from unittest.mock import Mock, patch

from seleniumwire.webdriver.request import RequestMixin


class Driver(RequestMixin):
    pass


class RequestMixinTest(TestCase):

    @patch('seleniumwire.webdriver.request.client')
    def test_capture_requests(self, mock_client):
        driver = Driver()
        driver.capture_requests()

        mock_client.capture_requests.assert_called_once_with()



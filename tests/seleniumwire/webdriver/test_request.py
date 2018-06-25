import uuid
from unittest import TestCase
from unittest.mock import Mock, patch

from seleniumwire.webdriver.request import InspectRequestsMixin, Request


class Driver(InspectRequestsMixin):
    pass


class InspectRequestsMixinTest(TestCase):

    @patch('seleniumwire.webdriver.request.client')
    def test_request_property(self, mock_client):
        driver = Driver()
        driver.requests

        mock_client.capture_requests.assert_called_once_with()


class RequestTest(TestCase):

    def test_initialise(self):
        data = {
            'id': uuid.uuid4(),
            'method': 'GET',
            'path': 'http://www.example.com/some/path/',
            'headers': {
                'Content-Type': 'application/json',
                'Content-Length': 200
            },
            'response': uuid.uuid4()
        }

        request = Request(data)

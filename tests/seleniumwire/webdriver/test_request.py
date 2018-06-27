import uuid
from unittest import TestCase
from unittest.mock import patch

from seleniumwire.webdriver.request import InspectRequestsMixin, Request, Response


class Driver(InspectRequestsMixin):
    pass


class InspectRequestsMixinTest(TestCase):

    @patch('seleniumwire.webdriver.request.client')
    def test_request_property(self, mock_client):
        driver = Driver()
        driver.requests

        mock_client.capture_requests.assert_called_once_with()


class RequestTest(TestCase):

    def test_create_request(self):
        data = self._request_data()

        request = Request(data)

        self.assertEqual(request.method, 'GET'),
        self.assertEqual(request.path, 'http://www.example.com/some/path/')
        self.assertEqual(len(request.headers), 3)
        self.assertEqual(request.headers['Host'], 'www.example.com')
        self.assertIsNone(request.response)

    def test_request_repr(self):
        data = self._request_data()

        request = Request(data)

        self.assertEqual(repr(request), 'Request({})'.format(data))

    def test_request_str(self):
        data = self._request_data()

        request = Request(data)

        self.assertEqual(str(request), 'http://www.example.com/some/path/'.format(data))

    def test_create_request_with_response(self):
        data = self._request_data()
        data['response'] = self._response_data()

        request = Request(data)

        self.assertIsInstance(request.response, Response)

    @patch('seleniumwire.webdriver.request.client')
    def test_load_request_body(self, mock_client):
        mock_client.request_body.return_value = b'the body'
        data = self._request_data()

        request = Request(data)
        body = request.body

        self.assertEqual(body, b'the body')
        mock_client.request_body.assert_called_once_with(data['id'])

    @patch('seleniumwire.webdriver.request.client')
    def test_load_request_body_uses_cached_data(self, mock_client):
        mock_client.request_body.return_value = b'the body'
        data = self._request_data()

        request = Request(data)
        request.body  # Retrieves the body
        body = request.body  # Uses the previously retrieved body

        self.assertEqual(body, b'the body')
        mock_client.request_body.assert_called_once_with(data['id'])

    def _request_data(self):
        data = {
            'id': uuid.uuid4(),
            'method': 'GET',
            'path': 'http://www.example.com/some/path/',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
            },
            'response': None
        }

        return data

    def _response_data(self):
        data = {
            'status_code': 200,
            'reason': 'OK',
            'headers': {
                'Content-Type': 'application/json',
                'Content-Length': 120
            },
        }

        return data


class ResponseTest(TestCase):

    def test_create_response(self):
        data = self._response_data()

        response = Response(uuid.uuid4(), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, 'OK')
        self.assertEqual(len(response.headers), 2)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

    def test_response_repr(self):
        request_id = uuid.uuid4()
        data = self._response_data()

        response = Response(request_id, data)

        self.assertEqual(repr(response), "Response('{}', {})".format(request_id, data))

    def test_response_str(self):
        data = self._response_data()

        response = Response(uuid.uuid4(), data)

        self.assertEqual(str(response), '200 OK'.format(data))

    @patch('seleniumwire.webdriver.request.client')
    def test_load_response_body(self, mock_client):
        mock_client.response_body.return_value = b'the body'
        data = self._response_data()
        request_id = uuid.uuid4()

        response = Response(request_id, data)
        body = response.body

        self.assertEqual(body, b'the body')
        mock_client.response_body.assert_called_once_with(request_id)

    @patch('seleniumwire.webdriver.request.client')
    def test_load_response_body_uses_cached_data(self, mock_client):
        mock_client.response_body.return_value = b'the body'
        data = self._response_data()
        request_id = uuid.uuid4()

        response = Response(request_id, data)
        response.body  # Retrieves the body
        body = response.body  # Uses the previously retrieved body

        self.assertEqual(body, b'the body')
        mock_client.response_body.assert_called_once_with(request_id)

    def _response_data(self):
        data = {
            'status_code': 200,
            'reason': 'OK',
            'headers': {
                'Content-Type': 'application/json',
                'Content-Length': 120
            },
        }

        return data

import uuid
from unittest import TestCase
from unittest.mock import Mock, call

from seleniumwire.webdriver.request import (InspectRequestsMixin, Request, Response,
                                            TimeoutException)


class Driver(InspectRequestsMixin):
    def __init__(self, client):
        self._client = client


class InspectRequestsMixinTest(TestCase):

    def setUp(self):
        self.mock_client = Mock()
        self.driver = Driver(self.mock_client)

    def test_get_requests(self):
        self.mock_client.get_requests.return_value = [{
            'id': '12345',
            'method': 'GET',
            'path': 'http://www.example.com/some/path',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '15012'
                }
            }
        }]

        requests = self.driver.requests

        self.mock_client.get_requests.assert_called_once_with()
        self.assertEqual(requests[0].path, 'http://www.example.com/some/path')
        self.assertEqual(requests[0].response.headers['Content-Type'], 'text/plain')

    def test_set_requests(self):
        driver = Driver(Mock())

        with self.assertRaises(AttributeError):
            driver.requests = ['some request']

    def test_delete_requests(self):
        mock_client = Mock()
        driver = Driver(mock_client)
        del driver.requests

        mock_client.clear_requests.assert_called_once_with()

    def test_last_request(self):
        self.mock_client.get_last_request.return_value = {
            'id': '98765',
            'method': 'GET',
            'path': 'http://www.example.com/different/path?foo=bar',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '98425'
                }
            }
        }

        last_request = self.driver.last_request

        self.mock_client.get_last_request.assert_called_once_with()
        self.assertEqual(last_request.path, 'http://www.example.com/different/path?foo=bar')
        self.assertEqual(last_request.response.headers['Content-Length'], '98425')

    def test_last_request_none(self):
        self.mock_client.get_last_request.return_value = None

        last_request = self.driver.last_request

        self.mock_client.get_last_request.assert_called_once_with()
        self.assertIsNone(last_request)

    def test_wait_for_request(self):
        mock_client = Mock()
        mock_client.find.return_value = {
            'id': '98765',
            'method': 'GET',
            'path': 'http://www.example.com/some/path?foo=bar',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '98425'
                }
            }
        }
        driver = Driver(mock_client)

        request = driver.wait_for_request('/some/path')

        mock_client.find.assert_called_once_with('/some/path')
        self.assertEqual(request.path, 'http://www.example.com/some/path?foo=bar')

    def test_wait_for_request_timeout(self):
        mock_client = Mock()
        mock_client.find.return_value = None
        driver = Driver(mock_client)

        with self.assertRaises(TimeoutException):
            driver.wait_for_request('/some/path', timeout=1)

        mock_client.find.assert_has_calls([call('/some/path')] * 5)

    def test_set_header_overrides(self):
        mock_client = Mock()
        driver = Driver(mock_client)
        header_overrides = {
            'User-Agent': 'Test_User_Agent_String'
        }

        driver.header_overrides = header_overrides

        mock_client.set_header_overrides.assert_called_once_with(header_overrides)

    def test_delete_header_overrides(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        del driver.header_overrides

        mock_client.clear_header_overrides.assert_called_once_with()

    def test_get_header_overrides(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        driver.header_overrides

        mock_client.get_header_overrides.assert_called_once_with()

    def test_set_rewrite_rules(self):
        mock_client = Mock()
        driver = Driver(mock_client)
        rewrite_rules = [
            ('http://somewhere.com/', 'https://www.somewhere.com'),
            ('http://otherplace.com/', 'http://otherplace.com/api/')
        ]

        driver.rewrite_rules = rewrite_rules

        mock_client.set_rewrite_rules.assert_called_once_with(rewrite_rules)

    def test_delete_rewrite_rules(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        del driver.rewrite_rules

        mock_client.clear_rewrite_rules.assert_called_once_with()

    def test_get_rewrite_rules(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        driver.rewrite_rules

        mock_client.get_rewrite_rules.assert_called_once_with()

    def test_set_scopes(self):
        mock_client = Mock()
        driver = Driver(mock_client)
        scopes = [
            '.*stackoverflow.*',
            '.*github.*'
        ]

        driver.scopes = scopes

        mock_client.set_scopes.assert_called_once_with(scopes)

    def test_delete_scopes(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        del driver.scopes

        mock_client.reset_scopes.assert_called_once_with()

    def test_get_scopes(self):
        mock_client = Mock()
        driver = Driver(mock_client)

        driver.scopes

        mock_client.get_scopes.assert_called_once_with()


class RequestTest(TestCase):

    def test_create_request(self):
        data = self._request_data()

        request = Request(data, Mock())

        self.assertEqual(request.method, 'GET'),
        self.assertEqual(request.path, 'http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=')
        self.assertEqual(len(request.headers), 3)
        self.assertEqual(request.headers['Host'], 'www.example.com')
        self.assertIsNone(request.response)

    def test_get_header_case_insensitive(self):
        data = self._request_data()

        request = Request(data, Mock())

        self.assertEqual(request.headers['host'], 'www.example.com')

    def test_request_repr(self):
        data = self._request_data()

        request = Request(data, Mock())

        self.assertEqual(repr(request), 'Request({})'.format(data))

    def test_request_str(self):
        data = self._request_data()

        request = Request(data, Mock())

        self.assertEqual('http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=', str(request))

    def test_create_request_with_response(self):
        data = self._request_data()
        data['response'] = self._response_data()

        request = Request(data, Mock())

        self.assertIsInstance(request.response, Response)

    def test_load_request_body(self):
        mock_client = Mock()
        mock_client.get_request_body.return_value = b'the body'
        data = self._request_data()

        request = Request(data, mock_client)
        body = request.body

        self.assertEqual(body, b'the body')
        mock_client.get_request_body.assert_called_once_with(data['id'])

    def test_load_request_body_uses_cached_data(self):
        mock_client = Mock()
        mock_client.get_request_body.return_value = b'the body'
        data = self._request_data()

        request = Request(data, mock_client)
        request.body  # Retrieves the body
        body = request.body  # Uses the previously retrieved body

        self.assertEqual(body, b'the body')
        mock_client.get_request_body.assert_called_once_with(data['id'])

    def test_querystring(self):
        data = self._request_data()

        request = Request(data, Mock())

        self.assertEqual(request.querystring, 'foo=bar&hello=world&foo=baz&other=')

    def test_GET_params(self):
        data = self._request_data()

        request = Request(data, Mock())

        params = request.params
        self.assertEqual(params['hello'], 'world')
        self.assertEqual(params['foo'], ['bar', 'baz'])
        self.assertEqual(params['other'], '')

    def test_POST_params(self):
        data = self._request_data()
        data['method'] = 'POST'
        data['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
        mock_client = Mock()
        mock_client.get_request_body.return_value = b'foo=bar&hello=world&foo=baz&other='

        request = Request(data, mock_client)

        params = request.params
        self.assertEqual(params['hello'], 'world')
        self.assertEqual(params['foo'], ['bar', 'baz'])
        self.assertEqual(params['other'], '')

    def _request_data(self):
        data = {
            'id': uuid.uuid4(),
            'method': 'GET',
            'path': 'http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=',
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

        response = Response(uuid.uuid4(), data, Mock())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, 'OK')
        self.assertEqual(len(response.headers), 2)
        self.assertEqual(response.headers['Content-Type'], 'application/json')

    def test_get_header_case_insensitive(self):
        data = self._response_data()

        response = Response(uuid.uuid4(), data, Mock())

        self.assertEqual(response.headers['content-type'], 'application/json')

    def test_response_repr(self):
        request_id = uuid.uuid4()
        data = self._response_data()

        response = Response(request_id, data, Mock())

        self.assertEqual(repr(response), "Response('{}', {})".format(request_id, data))

    def test_response_str(self):
        data = self._response_data()

        response = Response(uuid.uuid4(), data, Mock())

        self.assertEqual(str(response), '200 OK'.format(data))

    def test_load_response_body(self):
        mock_client = Mock()
        mock_client.get_response_body.return_value = b'the body'
        data = self._response_data()
        request_id = uuid.uuid4()

        response = Response(request_id, data, mock_client)
        body = response.body

        self.assertEqual(body, b'the body')
        mock_client.get_response_body.assert_called_once_with(request_id)

    def test_load_response_body_uses_cached_data(self):
        mock_client = Mock()
        mock_client.get_response_body.return_value = b'the body'
        data = self._response_data()
        request_id = uuid.uuid4()

        response = Response(request_id, data, mock_client)
        response.body  # Retrieves the body
        body = response.body  # Uses the previously retrieved body

        self.assertEqual(body, b'the body')
        mock_client.get_response_body.assert_called_once_with(request_id)

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

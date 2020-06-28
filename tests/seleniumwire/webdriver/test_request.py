import uuid
from unittest import TestCase
from unittest.mock import Mock, call

from seleniumwire.webdriver.request import (InspectRequestsMixin, LazyRequest, LazyResponse,
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
                'status': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '15012'
                }
            }
        }]

        requests = self.driver.requests

        self.mock_client.get_requests.assert_called_once_with()
        self.assertEqual(1, len(requests))
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
            'method': 'GET',
            'path': 'http://www.example.com/different/path?foo=bar',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status': 200,
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
            'method': 'GET',
            'path': 'http://www.example.com/some/path?foo=bar',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status': 200,
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


class LazyRequestTest(TestCase):

    def test_load_request_body(self):
        mock_client = Mock()
        mock_client.get_request_body.return_value = b'the body'

        request = self._create_request(mock_client)
        body = request.body

        self.assertEqual(body, b'the body')
        mock_client.get_request_body.assert_called_once_with(request.id)

    def test_from_dict(self):
        mock_client = Mock()
        request = LazyRequest.from_dict({
            'id': '12345',
            'method': 'GET',
            'path': 'http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
            },
            'response': {
                'status': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'application/json',
                    'Content-Length': 120
                },
            }
        }, mock_client)

        self.assertEqual('12345', request.id)
        self.assertEqual('GET', request.method)
        self.assertEqual('http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=', request.path)
        self.assertEqual({
                'Accept': '*/*',
                'Host': 'www.example.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
            }, request.headers)
        self.assertIsInstance(request.response, LazyResponse)

    def _create_request(self, client):
        request = LazyRequest(
            client,
            method='GET',
            path='http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=',
            headers={
                'Accept': '*/*',
                'Host': 'www.example.com',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
            }
        )

        return request


class ResponseTest(TestCase):

    def test_load_response_body(self):
        mock_client = Mock()
        mock_client.get_response_body.return_value = b'the body'

        response = self._create_response('12345', mock_client)
        body = response.body

        self.assertEqual(body, b'the body')
        mock_client.get_response_body.assert_called_once_with('12345')

    def test_from_dict(self):
        mock_client = Mock()
        response = LazyResponse.from_dict({
            'status': 200,
            'reason': 'OK',
            'headers': {
                'Content-Type': 'application/json',
                'Content-Length': 120
            },
            'body': 'foobar'
        }, mock_client, '12345')

        self.assertEqual(200, response.status)
        self.assertEqual('OK', response.reason)
        self.assertEqual({
            'Content-Type': 'application/json',
            'Content-Length': 120
        }, response.headers)

    def _create_response(self, request_id, client):
        response = LazyResponse(
            request_id,
            client,
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'application/json',
                'Content-Length': 120
            },
        )
        return response

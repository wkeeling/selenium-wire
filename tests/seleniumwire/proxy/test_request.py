from unittest import TestCase

from seleniumwire.proxy.request import Request, Response


class RequestTest(TestCase):

    def test_create_request(self):
        request = self._create_request()

        self.assertEqual('GET', request.method),
        self.assertEqual('http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=', request.url)
        self.assertEqual(3, len(request.headers))
        self.assertEqual('www.example.com', request.headers['Host'])
        self.assertIsNone(request.response)

    def test_get_header_case_insensitive(self):
        request = self._create_request()

        self.assertEqual('www.example.com', request.headers['host'])

    def test_no_body(self):
        request = self._create_request(body=None)

        self.assertEqual(b'', request.body)

    def test_str_body(self):
        request = self._create_request(body='foobar')

        self.assertEqual(b'foobar', request.body)

    def test_invalid_body(self):
        with self.assertRaises(TypeError):
            self._create_request(body=object())

    def test_querystring(self):
        request = self._create_request()

        self.assertEqual('foo=bar&hello=world&foo=baz&other=', request.querystring)

    def test_set_querystring(self):
        qs = 'x=y&a=b'
        request = self._create_request()

        request.querystring = qs

        self.assertEqual(qs, request.querystring)

    def test_GET_params(self):
        request = self._create_request()

        params = request.params
        self.assertEqual(params['hello'], 'world')
        self.assertEqual(params['foo'], ['bar', 'baz'])
        self.assertEqual(params['other'], '')

    def test_POST_params(self):
        request = self._create_request(body=b'foo=bar&hello=world&foo=baz&other=')
        request.method = 'POST'
        request.url = 'http://www.example.com/some/path/'
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'

        params = request.params
        self.assertEqual(params['hello'], 'world')
        self.assertEqual(params['foo'], ['bar', 'baz'])
        self.assertEqual(params['other'], '')

    def test_set_GET_params(self):
        request = self._create_request()

        request.params = {'a': 'b'}

        self.assertEqual('a=b', request.querystring)

    def test_set_POST_params(self):
        request = self._create_request()
        request.method = 'POST'
        request.url = 'http://www.example.com/some/path/'
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'

        request.params = {'a': 'b'}

        self.assertEqual('a=b', request.body.decode('utf-8'))

    def test_path(self):
        request = self._create_request()

        self.assertEqual('/some/path/', request.path)

    def test_set_path(self):
        request = self._create_request()

        request.path = '/some/other/path'

        self.assertEqual('/some/other/path', request.path)

    def test_create_response(self):
        request = self._create_request()

        request.create_response(
            200, {'header-name': 'header-val'}, b'test body'
        )

        self.assertEqual(200, request.response.status_code)
        self.assertEqual({'header-name': 'header-val'}, dict(request.response.headers))
        self.assertEqual(b'test body', request.response.body)

    def test_create_response_invalid_status(self):
        request = self._create_request()

        with self.assertRaises(ValueError):
            request.create_response(900)

    def test_create_abort(self):
        request = self._create_request()

        request.abort(403)

        self.assertEqual(403, request.response.status_code)
        self.assertEqual({}, dict(request.response.headers))
        self.assertEqual(b'', request.response.body)

    def test_request_repr(self):
        request = self._create_request()

        request2 = eval(repr(request))

        self.assertEqual('GET', request2.method)
        self.assertEqual('http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=', request2.url)
        self.assertEqual({'Accept': '*/*', 'Host': 'www.example.com',
                          'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'},
                         dict(request2.headers))
        self.assertEqual(b'', request2.body)

    def test_request_str(self):
        request = self._create_request()

        self.assertEqual('http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=', str(request))

    def _create_request(self, body=None):
        request = Request(
            method='GET',
            url='http://www.example.com/some/path/?foo=bar&hello=world&foo=baz&other=',
            headers=[
                ('Accept', '*/*'),
                ('Host', 'www.example.com'),
                ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0')
            ],
            body=body
        )

        return request


class ResponseTest(TestCase):

    def test_create_response(self):
        response = self._create_response()

        self.assertEqual(200, response.status_code)
        self.assertEqual('OK', response.reason)
        self.assertEqual(len(response.headers), 2)
        self.assertEqual('application/json', response.headers['Content-Type'])

    def test_get_header_case_insensitive(self):
        response = self._create_response()

        self.assertEqual('application/json', response.headers['content-type'])

    def test_no_body(self):
        request = self._create_response(body=None)

        self.assertEqual(b'', request.body)

    def test_str_body(self):
        request = self._create_response(body='foobar')

        self.assertEqual(b'foobar', request.body)

    def test_invalid_body(self):
        with self.assertRaises(TypeError):
            self._create_response(body=object())

    def test_response_repr(self):
        response = self._create_response()

        response2 = eval(repr(response))

        self.assertEqual(200, response2.status_code)
        self.assertEqual('OK', response2.reason)
        self.assertEqual({
            'Content-Type': 'application/json',
            'Content-Length': '120'
        }, dict(response2.headers))
        self.assertEqual(b'', response2.body)

    def test_response_str(self):
        response = self._create_response()

        self.assertEqual('200 OK', str(response))

    def _create_response(self, body=None):
        response = Response(
            status_code=200,
            reason='OK',
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Length', '120'),
            ],
            body=body
        )
        return response

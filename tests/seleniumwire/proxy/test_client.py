import socket
from unittest import TestCase
import urllib.request

from seleniumwire.proxy.client import AdminClient


class AdminClientTest(TestCase):

    def setUp(self):
        self.client = AdminClient()

    def test_create_proxy(self):
        host, port = self.client.create_proxy()
        self._configure_proxy(host, port)

        html = self._make_request('http://python.org')

        self.assertIn(b'Welcome to Python.org', html)

    def test_destroy_proxy(self):
        host, port = self.client.create_proxy()
        self._configure_proxy(host, port)
        self.client.destroy_proxy()

        with self.assertRaises(socket.timeout):
            self._make_request('http://python.org')

    def test_requests_single(self):
        host, port = self.client.create_proxy()
        # self._configure_proxy('localhost', 8080)
        self._configure_proxy(host, port)
        # print(host, port)

        self._make_request('http://fa-svr-ariaweb01')

        # requests = self.client.requests()
        # print(requests)

        # self.assertEqual(len(requests), 1)
        # request = requests[0]
        # self.assertEqual(request['method'], 'GET')
        # self.assertEqual(request['path'], 'http://fa-svr-ariaweb01')
        # self.assertIn('headers', request)
        # self.assertEqual(request['response']['status_code'], 200)

    def test_requests_multiple(self):
        self.fail('Implement')

    def test_requests_https(self):
        self.fail('Implement')

    def test_request_body(self):
        self.fail('Implement')

    def test_response_body(self):
        self.fail('Implement')

    def _configure_proxy(self, host, port):
        handler = urllib.request.ProxyHandler({
            'http': 'http://{}:{}'.format(host, port)
        })
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

    def _make_request(self, url):
        with urllib.request.urlopen(url, timeout=1) as response:
            html = response.read()

        return html

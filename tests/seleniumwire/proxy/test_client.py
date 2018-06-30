import socket
from unittest import TestCase
import urllib.request

from seleniumwire.proxy.client import AdminClient


class AdminClientTest(TestCase):

    def setUp(self):
        self.client = AdminClient()

    def test_create_proxy(self):
        host, port = self.client.create_proxy()

        html = self._make_request(host, port)

        self.assertIn(b'Welcome to Python.org', html)

    def test_destroy_proxy(self):
        host, port = self.client.create_proxy()
        self.client.destroy_proxy()

        with self.assertRaises(socket.timeout):
            self._make_request(host, port)

    def test_requests(self):
        host, port = self.client.create_proxy()

        self._make_request(host, port)

        requests = self.client.requests()

        self.assertEqual(len(requests), 1)
        request = requests[0]
        print(request)
        self.assertEqual(request['method'], 'GET')
        self.assertEqual(request['path'], 'http://python.org')
        self.assertIn('headers', request)
        self.assertEqual(request['response']['status_code'], 200)

    def _make_request(self, host, port):
        handler = urllib.request.ProxyHandler({
            'http': 'http://{}:{}'.format(host, port)
        })
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

        with urllib.request.urlopen('http://python.org', timeout=1) as response:
            html = response.read()

        return html

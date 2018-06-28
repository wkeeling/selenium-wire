import socket
from unittest import TestCase

from seleniumwire.proxy.client import AdminClient


class AdminClientTest(TestCase):

    def setUp(self):
        self.client = AdminClient()

    def test_create_proxy(self):
        host, port = self.client.create_proxy()

        socket.create_connection((host, port))

    def test_destroy_proxy(self):
        host, port = self.client.create_proxy()

        self.client.destroy_proxy()

        with self.assertRaises(ConnectionError):
            socket.create_connection((host, port))

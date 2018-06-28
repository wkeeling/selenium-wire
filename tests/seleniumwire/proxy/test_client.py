import socket
from unittest import TestCase

from seleniumwire.proxy.client import AdminClient


class AdminClientIntegrationTest(TestCase):

    def setUp(self):
        self.client = AdminClient()

    def test_create_proxy(self):
        host, port = self.client.create_proxy()

        try:
            conn = socket.create_connection((host, port))
        finally:
            conn.close()

    def test_destroy_proxy(self):
        host, port = self.client.create_proxy()

        self.client.destroy_proxy()

        socket.create_connection((host, port))

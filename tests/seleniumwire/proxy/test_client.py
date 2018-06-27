import socket
from unittest import TestCase

from seleniumwire.proxy import client


class AdminClientTest(TestCase):

    def test_create_proxy(self):
        host, port = client.create_proxy()

        socket.create_connection((host, port))

    def test_destroy_proxy(self):
        host, port = client.create_proxy()

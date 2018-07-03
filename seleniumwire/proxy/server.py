import threading

from seleniumwire.proxy.handler import CaptureRequestHandler
from seleniumwire.proxy.proxy2 import ThreadingHTTPServer
from seleniumwire.proxy.storage import RequestStorage


class ProxyHTTPServer(ThreadingHTTPServer):

    def server_activate(self):
        # Each server instance gets its own storage
        self.storage = RequestStorage()
        super().server_activate()

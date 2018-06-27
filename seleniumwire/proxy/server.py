from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage


class ProxyHTTPServer(ThreadingHTTPServer):

    def server_activate(self):
        self.storage = RequestStorage()


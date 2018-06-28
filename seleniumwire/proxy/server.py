from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage


class ProxyHTTPServer(ThreadingHTTPServer):

    def server_activate(self):
        # Each server instance gets its own storage
        self.storage = RequestStorage()
        super().server_activate()

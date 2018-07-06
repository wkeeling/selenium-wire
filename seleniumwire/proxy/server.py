from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage
from .util import RequestModifier


class ProxyHTTPServer(ThreadingHTTPServer):

    def server_activate(self):
        # Each server instance gets its own storage
        self.storage = RequestStorage()
        # Each server instance gets a request modifier
        self.modifier = RequestModifier()
        super().server_activate()

    def shutdown(self):
        super().shutdown()
        self.storage.clear_requests()

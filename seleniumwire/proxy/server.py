from urllib.request import _parse_proxy

from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage
from .util import RequestModifier


class ProxyHTTPServer(ThreadingHTTPServer):

    def __init__(self, options, *args, **kwargs):
        # The seleniumwire options
        self.options = options
        try:
            # Parse the proxy URL into (proxy_type, user, password, hostport)
            self.options['proxy'] = _parse_proxy(options['proxy'])
        except KeyError:
            pass
        # Each server instance gets its own storage
        self.storage = RequestStorage()
        # Each server instance gets a request modifier
        self.modifier = RequestModifier()

        super().__init__(*args, **kwargs)

    def shutdown(self):
        super().shutdown()
        self.storage.clear_requests()

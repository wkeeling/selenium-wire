from http.client import HTTPConnection, HTTPSConnection
from urllib.request import _parse_proxy

from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage
from .util import RequestModifier


class ProxyHTTPServer(ThreadingHTTPServer):

    def __init__(self, options, *args, **kwargs):
        # The seleniumwire options
        self.options = options
        # Check for upstream proxy configuration
        for proxy_type in ('http', 'https'):
            try:
                # Parse the upstream proxy URL into (scheme, user, password, hostport)
                # for ease of access.
                proxy = _parse_proxy(options['proxy'][proxy_type])
                proxy += (HTTPConnection,) if proxy[0] == 'http' else (HTTPSConnection,)
                self.options['proxy'][proxy_type] = proxy
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

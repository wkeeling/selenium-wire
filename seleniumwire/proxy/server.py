from http.client import HTTPConnection, HTTPSConnection
from urllib.request import _parse_proxy

from .proxy2 import ThreadingHTTPServer
from .storage import RequestStorage
from .util import RequestModifier


class ProxyHTTPServer(ThreadingHTTPServer):

    def __init__(self, *args, proxy_config=None, **kwargs):
        self.proxy_config = proxy_config or {}

        if proxy_config:
            # Check for upstream proxy configuration
            for proxy_type in ('http', 'https'):
                try:
                    # Parse the upstream proxy URL into (scheme, user, password, hostport)
                    # for ease of access.
                    parsed = _parse_proxy(proxy_config[proxy_type])
                    parsed += (HTTPConnection,) if parsed[0] == 'http' else (HTTPSConnection,)
                    self.proxy_config[proxy_type] = parsed
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

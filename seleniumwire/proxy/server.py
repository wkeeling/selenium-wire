import os
import socket
import ssl
import sys
import threading
from collections import namedtuple
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from urllib.request import _parse_proxy

from .modifier import RequestModifier
from .storage import RequestStorage


class BoundedThreadingMixin(ThreadingMixIn):
    """Mix-in class that allows for a maximum number of threads to handle requests."""

    def __init__(self, max_threads, *args, **kwargs):
        self.sema = threading.BoundedSemaphore(value=max_threads)
        super().__init__(*args, **kwargs)

    def process_request_thread(self, request, client_address):
        super().process_request_thread(request, client_address)
        self.sema.release()

    def process_request(self, request, client_address):
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        t.daemon = self.daemon_threads
        if not t.daemon and self._block_on_close:
            if self._threads is None:
                self._threads = []
            self._threads.append(t)
        self.sema.acquire()
        t.start()


class ProxyHTTPServer(BoundedThreadingMixin, HTTPServer):
    address_family = socket.AF_INET
    daemon_threads = True

    def __init__(self, *args, proxy_config=None, options=None, **kwargs):
        # The server's upstream proxy configuration (if any)
        self.proxy_config = self._sanitise_proxy_config(
            self._merge_with_env(proxy_config or {}))

        # Additional configuration
        self.options = options or {}

        # Used to stored captured requests
        self.storage = RequestStorage(
            base_dir=self.options.pop('request_storage_base_dir', None)
        )

        # Used to modify requests/responses passing through the server
        self.modifier = RequestModifier()

        # The scope of requests we're interested in capturing.
        self.scopes = []

        super().__init__(self.options.get('max_threads', 9999), *args, **kwargs)

    def _merge_with_env(self, proxy_config):
        """Merge upstream proxy configuration with configuration loaded
        from the environment.
        """
        http_proxy = os.environ.get('HTTP_PROXY')
        https_proxy = os.environ.get('HTTPS_PROXY')
        no_proxy = os.environ.get('NO_PROXY')

        merged = {}

        if http_proxy:
            merged['http'] = http_proxy
        if https_proxy:
            merged['https'] = https_proxy
        if no_proxy:
            merged['no_proxy'] = no_proxy

        merged.update(proxy_config)

        return merged

    def _sanitise_proxy_config(self, proxy_config):
        """Parse the proxy configuration into something more usable."""
        conf = namedtuple('ProxyConf', 'scheme username password hostport')

        for proxy_type in ('http', 'https'):
            # Parse the upstream proxy URL into (scheme, username, password, hostport)
            # for ease of access.
            if proxy_config.get(proxy_type) is not None:
                proxy_config[proxy_type] = conf(*_parse_proxy(proxy_config[proxy_type]))

        return proxy_config

    def shutdown(self):
        super().shutdown()
        self.storage.cleanup()

    def handle_error(self, request, client_address):
        # Suppress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if issubclass(cls, socket.error) or issubclass(cls, ssl.SSLError):
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)

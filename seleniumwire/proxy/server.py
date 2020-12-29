import socket
import ssl
import sys
import threading
from http.server import HTTPServer
from socketserver import ThreadingMixIn

from . import utils
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

    def __init__(self, host, port, *args, options=None, **kwargs):
        # The server's upstream proxy configuration (if any)
        self.proxy_config = utils.get_upstream_proxy(options)

        # Additional configuration
        self.options = options or {}

        # Used to stored captured requests
        self.storage = RequestStorage(
            base_dir=self.options.pop('request_storage_base_dir', None)
        )

        # Used to modify requests/responses passing through the server
        # Deprecated. Will be superceded by request/response interceptors.
        self.modifier = RequestModifier()

        # The scope of requests we're interested in capturing.
        self.scopes = []

        self.request_interceptor = None
        self.response_interceptor = None

        super().__init__(self.options.get('max_threads', 9999), (host, port), *args, **kwargs)

    def address(self):
        """Get a tuple of the address and port the server is listening on."""
        return self.socket.getsockname()

    def shutdown(self):
        super().shutdown()
        super().server_close()  # Closes the server socket
        self.storage.cleanup()

    def handle_error(self, request, client_address):
        # Suppress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if issubclass(cls, socket.error) or issubclass(cls, ssl.SSLError):
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)

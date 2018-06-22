import http.client
import threading

from .handler import ADMIN_PATH, CaptureRequestHandler
from .proxy2 import ThreadingHTTPServer


class AdministrationClient:

    def __init__(self):
        self._proxy = None
        self._proxy_host = 'localhost'
        self._proxy_port = 0

    def create_proxy(self):
        # This at some point may interact with a remote service
        # to create the proxy and retrieve its address details.
        CaptureRequestHandler.protocol_version = 'HTTP/1.1'
        self._proxy = ThreadingHTTPServer((self._proxy_host, self._proxy_port), CaptureRequestHandler)

        t = threading.Thread(name='Selenium Wire Proxy Server', target=self._proxy.serve_forever)
        t.daemon = True
        t.start()

        # self._proxy_host = self._proxy.socket.gethostname()
        self._proxy_port = self._proxy.socket.getsockname()[1]

        return self._proxy_host, self._proxy_port

    def destroy_proxy(self):
        self._proxy.shutdown()

    def start_capture(self):
        conn = http.client.HTTPConnection(self._proxy_host, self._proxy_port)
        conn.request('GET', '{}/start_capture'.format(ADMIN_PATH))
        response = conn.getresponse()
        conn.close()

        if response.status != 200:
            raise ProxyException('Proxy returned status code {} for start_capture'.format(response.status))


class ProxyException(Exception):
    """Raised when there is a problem communicating with the proxy server."""



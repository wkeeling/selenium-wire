import http.client
import json
import threading

from .handler import ADMIN_PATH, CaptureRequestHandler
from .proxy2 import ThreadingHTTPServer


class AdminClient:

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
        # TODO: should this also remove request data folders? But these folders would have to be per-proxy instance.
        self._proxy.shutdown()

    def requests(self):
        url = '{}/requests'.format(ADMIN_PATH)
        conn = http.client.HTTPConnection(self._proxy_host, self._proxy_port)
        conn.request('GET', url)
        try:
            response = conn.getresponse()
            if response.status != 200:
                raise ProxyException('Proxy returned status code {} for {}'.format(response.status, url))
            return json.load(response)
        except ProxyException:
            raise
        except Exception as e:
            raise ProxyException('Unable to retrieve data from proxy: {}'.format(e))
        finally:
            try:
                conn.close()
            except ConnectionError:
                pass


class ProxyException(Exception):
    """Raised when there is a problem communicating with the proxy server."""

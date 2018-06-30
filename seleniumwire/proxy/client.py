import http.client
import json
import threading

from .handler import ADMIN_PATH, CaptureRequestHandler
from .server import ProxyHTTPServer


class AdminClient:
    """Provides the means to communicate with the proxy server and ask it for information
    and tell it to do certain things.

    This implementation starts a proxy server instance in a separate thread.
    """

    def __init__(self):
        self._proxy = None
        self._proxy_host = 'localhost'
        self._proxy_port = 0

    def create_proxy(self):
        """Creates a new proxy server and returns the host and port number that the
        server was started on.

        Returns:
            A tuple of the host and port number of the created proxy server.
        """
        # This at some point may interact with a remote service
        # to create the proxy and retrieve its address details.
        CaptureRequestHandler.protocol_version = 'HTTP/1.1'
        self._proxy = ProxyHTTPServer((self._proxy_host, self._proxy_port), CaptureRequestHandler)

        t = threading.Thread(name='Selenium Wire Proxy Server', target=self._proxy.serve_forever)
        t.daemon = True
        t.start()

        # self._proxy_host = self._proxy.socket.gethostname()
        self._proxy_port = self._proxy.socket.getsockname()[1]

        return self._proxy_host, self._proxy_port

    def destroy_proxy(self):
        """Stops the proxy server and performs any clean up actions."""
        self._proxy.shutdown()

    def requests(self):
        """Returns the requests currently captured by the proxy server.

        The data is returned as a list of dictionaries in the format:

        [{
            'id': 'request id',
            'method': 'GET',
            'path': 'http://www.example.com/some/path',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            }
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': 15012
                }
            }
        }, ...]

        Returns:
            A list of request dictionaries.
        """
        url = '{}/requests'.format(ADMIN_PATH)
        conn = http.client.HTTPConnection(self._proxy_host, self._proxy_port)
        conn.request('GET', url)
        try:
            response = conn.getresponse()
            if response.status != 200:
                raise ProxyException('Proxy returned status code {} for {}'.format(response.status, url))
            data = response.read()
            return json.loads(data.decode(encoding='utf-8'))
        except ProxyException:
            raise
        except Exception as e:
            raise ProxyException('Unable to retrieve data from proxy: {}'.format(e))
        finally:
            try:
                conn.close()
            except ConnectionError:
                pass

    def clear_requests(self):
        pass

    def request_body(self, request_id):
        pass

    def response_body(self, request_id):
        pass


class ProxyException(Exception):
    """Raised when there is a problem communicating with the proxy server."""

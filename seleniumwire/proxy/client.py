import http.client
import json

from .handler import ADMIN_PATH
from .server import ProxyHTTPServer


class AdminClient:
    """Provides the means to communicate with the proxy server and ask it for information
    and tell it to do certain things.
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
        # For the time being, we create a local proxy.
        return ProxyHTTPServer.start()

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
                    'Content-Length': '15012'
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

    def last_request(self):
        pass

    def clear_requests(self):
        pass

    def request_body(self, request_id):
        pass

    def response_body(self, request_id):
        pass


class ProxyException(Exception):
    """Raised when there is a problem communicating with the proxy server."""

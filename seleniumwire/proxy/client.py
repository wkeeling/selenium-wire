import http.client
import json
import logging
import threading
from urllib.parse import quote_plus

from .handler import ADMIN_PATH, CaptureRequestHandler, create_custom_capture_request_handler
from .server import ProxyHTTPServer

log = logging.getLogger(__name__)


class AdminClient:
    """Provides an API for sending commands to a remote proxy server."""

    def __init__(self, proxy_mgr_addr=None, proxy_mgr_port=None):
        # The address of the proxy manager if set
        self._proxy_mgr_addr = proxy_mgr_addr
        self._proxy_mgr_port = proxy_mgr_port

        # Reference to a created proxy instance and its address/port
        self._proxy = None
        self._proxy_addr = None
        self._proxy_port = None
        self._capture_request_handler = None

    def create_proxy(self, addr='127.0.0.1', port=0, options=None):
        """Creates a new proxy server and returns the address and port number that the
        server was started on.

        Args:
            addr: The address the proxy server will listen on. Default 127.0.0.1.
            port: The port the proxy server will listen on. Default 0 - which means
                use the first available port.
            options: Additional options to configure the proxy.

        Returns:
            A tuple of the address and port number of the created proxy server.
        """
        if self._proxy_mgr_addr is not None and self._proxy_mgr_port is not None:
            # TODO: ask the proxy manager to create a proxy and return that
            pass

        if options is None:
            options = {}

        if options.get('backend', 'default') == 'default':
            # Use the default backend
            custom_response_handler = options.get('custom_response_handler')
            if custom_response_handler is not None:
                self._capture_request_handler = create_custom_capture_request_handler(custom_response_handler)
            else:
                self._capture_request_handler = CaptureRequestHandler
                # Set the timeout here before the handler starts executing
                self._capture_request_handler.timeout = options.get('connection_timeout', 5)
            self._proxy = ProxyHTTPServer((addr, port), self._capture_request_handler, options=options)

            t = threading.Thread(name='Selenium Wire Proxy Server', target=self._proxy.serve_forever)
            t.daemon = not options.get('standalone')
            t.start()

            socketname = self._proxy.socket.getsockname()
            self._proxy_addr = socketname[0]
            self._proxy_port = socketname[1]
        elif options.get('backend') == 'mitmproxy':
            # Use mitmproxy if installed
            from . import mitmproxy

            self._proxy = mitmproxy.run(addr, port, options)
            self._proxy_addr = addr
            self._proxy_port = port
            self._proxy.wait()
        else:
            raise TypeError(
                "Invalid backend '{}'. "
                "Valid values are 'default' or 'mitmproxy'."
                .format(options['backend'])
            )

        self.initialise_proxy(options)

        log.info('Created proxy listening on {}:{}'.format(self._proxy_addr, self._proxy_port))
        return self._proxy_addr, self._proxy_port

    def initialise_proxy(self, options):
        """Initialise the proxy with any options.

        Args:
            options: The selenium wire options.
        """
        self._make_request('POST', '/initialise', data=options)

    def destroy_proxy(self):
        """Stops the proxy server and performs any clean up actions."""
        log.info('Destroying proxy')
        # If proxy manager set, we would ask it to do this
        self._proxy.shutdown()

    def get_requests(self):
        """Returns the requests currently captured by the proxy server.

        The data is returned as a list of dictionaries in the format:

        [{
            'id': 'request id',
            'method': 'GET',
            'path': 'http://www.example.com/some/path',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            },
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '15012'
                }
            }
        }, ...]

        Note that the value of the 'response' key may be None where no response
        is associated with a given request.

        Returns:
            A list of request dictionaries.
        """
        return self._make_request('GET', '/requests')

    def get_last_request(self):
        """Returns the last request captured by the proxy server.

        This is more efficient than running get_requests()[-1]

        Returns:
            The last request as a dictionary or None if no requests have been
            made.
        """
        return self._make_request('GET', '/last_request')

    def clear_requests(self):
        """Clears any previously captured requests from the proxy server."""
        self._make_request('DELETE', '/requests')

    def find(self, path):
        """Find the first request that contains the specified path.

        Requests are searched in chronological order.

        Args:
            path: The request path which can be any part of the request URL.
        """
        return self._make_request('GET', '/find?path={}'.format(quote_plus(str(path))))

    def get_request_body(self, request_id):
        """Returns the body of the request with the specified request_id.

        Args:
            request_id: The request identifier.
        Returns:
            The binary request body, or None if the request has no body.
        """
        return self._make_request('GET', '/request_body?request_id={}'.format(request_id)) or None

    def get_response_body(self, request_id):
        """Returns the body of the response associated with the request with the
        specified request_id.

        Args:
            request_id: The request identifier.
        Returns:
            The binary response body, or None if the response has no body.
        """
        return self._make_request('GET', '/response_body?request_id={}'.format(request_id)) or None

    def set_header_overrides(self, headers):
        """Sets the header overrides.

        Args:
            headers: A dictionary of headers to be used as overrides. Where the value
                of a header is set to None, this header will be filtered out.
        """
        self._make_request('POST', '/header_overrides', data=headers)

    def clear_header_overrides(self):
        """Clears any previously set header overrides."""
        self._make_request('DELETE', '/header_overrides')

    def get_header_overrides(self):
        """Gets any previously set header overrides"""
        return self._make_request('GET', '/header_overrides')

    def set_rewrite_rules(self, rewrite_rules):
        """Sets the rewrite rules.

        Args:
            rewrite_rules: A list of rewrite rules. Each rule is a sublist (or 2-tuple)
                containing the pattern and replacement.
        """
        self._make_request('POST', '/rewrite_rules', data=rewrite_rules)

    def clear_rewrite_rules(self):
        """Clears any previously set rewrite rules."""
        self._make_request('DELETE', '/rewrite_rules')

    def get_rewrite_rules(self):
        """Gets any previously set rewrite rules"""
        return self._make_request('GET', '/rewrite_rules')

    def set_scopes(self, scopes):
        """Sets the scopes for the seleniumwire to log/modify request and response.

        Args:
            scopes: a regex string or list of regex string.
        """
        self._make_request('POST', '/scopes', data=scopes)

    def reset_scopes(self):
        """Reset scopes to let proxy capture all requests."""
        self._make_request('DELETE', '/scopes')

    def get_scopes(self):
        """Gets any previously set scopes"""
        return self._make_request('GET', '/scopes')

    def _make_request(self, command, path, data=None):
        url = '{}{}'.format(ADMIN_PATH, path)
        conn = http.client.HTTPConnection(self._proxy_addr, self._proxy_port)

        args = {}
        if data is not None:
            args['body'] = json.dumps(data).encode('utf-8')

        conn.request(command, url, **args)

        try:
            response = conn.getresponse()

            if response.status != 200:
                raise ProxyException('Proxy returned status code {} for {}'.format(response.status, url))

            data = response.read()
            try:
                if response.getheader('Content-Type') == 'application/json':
                    data = json.loads(data.decode(encoding='utf-8'))
            except (UnicodeDecodeError, ValueError):
                pass
            return data
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

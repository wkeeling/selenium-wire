import json
import logging
import socket
from urllib.parse import parse_qs, urlparse

from .proxy2 import ProxyRequestHandler

log = logging.getLogger(__name__)

ADMIN_PATH = 'http://seleniumwire'


class AdminMixin:
    """Mixin class that allows remote admin clients to interact with the proxy server.

    This class intercepts administration requests and dispatches them to
    relevant handler methods.
    """

    admin_path = ADMIN_PATH

    def admin_handler(self):
        parse_result = urlparse(self.path)
        path, params = parse_result.path, parse_qs(parse_result.query)

        if path == '/requests':
            if self.command == 'GET':
                self._get_requests()
            elif self.command == 'DELETE':
                self._clear_requests()
        elif path == '/last_request':
            self._get_last_request()
        elif path == '/request_body':
            self._get_request_body(**params)
        elif path == '/response_body':
            self._get_response_body(**params)
        elif path == '/find':
            self._find_request(**params)
        elif path == '/header_overrides':
            if self.command == 'POST':
                self._set_header_overrides()
            elif self.command == 'DELETE':
                self._clear_header_overrides()
            elif self.command == 'GET':
                self._get_header_overrides()
        else:
            raise RuntimeError('No handler configured for: {} {}'.format(self.command, self.path))

    def _get_requests(self):
        self._send_response(json.dumps(self.server.storage.load_requests()).encode('utf-8'), 'application/json')

    def _get_last_request(self):
        self._send_response(json.dumps(self.server.storage.load_last_request()).encode('utf-8'), 'application/json')

    def _clear_requests(self):
        self.server.storage.clear_requests()
        self._send_response(json.dumps({'status': 'ok'}).encode('utf-8'), 'application/json')

    def _get_request_body(self, request_id):
        body = self.server.storage.load_request_body(request_id[0])
        self._send_body(body)

    def _get_response_body(self, request_id):
        body = self.server.storage.load_response_body(request_id[0])
        self._send_body(body)

    def _send_body(self, body):
        if body is None:
            body = b''
        self._send_response(body, 'application/octet-stream')

    def _find_request(self, path):
        self._send_response(json.dumps(self.server.storage.find(path[0])).encode('utf-8'), 'application/json')

    def _set_header_overrides(self):
        content_length = int(self.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length)
        headers = json.loads(req_body.decode('utf-8'))
        self.server.modifier.headers = headers
        self._send_response(json.dumps({'status': 'ok'}).encode('utf-8'), 'application/json')

    def _clear_header_overrides(self):
        del self.server.modifier.headers
        self._send_response(json.dumps({'status': 'ok'}).encode('utf-8'), 'application/json')

    def _get_header_overrides(self):
        self._send_response(json.dumps(self.server.modifier.headers).encode('utf-8'), 'application/json')

    def _send_response(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


class CaptureRequestHandler(AdminMixin, ProxyRequestHandler):
    """Specialisation of ProxyRequestHandler that captures requests and responses
    that pass through the proxy server and allows admin clients to access that data.
    """

    def do_GET(self):
        try:
            super().do_GET()
        except (socket.timeout, BrokenPipeError) as e:
            # Log tracebacks at debug level to prevent these often harmless
            # exceptions from alarming users.
            log.debug(e, exc_info=True)

    def request_handler(self, req, req_body):
        """Captures a request and its body.

        Args:
            req: The request (an instance of CaptureRequestHandler).
            req_body: The binary request body.
        """
        log.info('Capturing request: %s', req.path)

        # First make any modifications to the request
        self.server.modify_request(req)

        # Save the request to our storage
        self.server.storage.save_request(req, req_body)

    def response_handler(self, req, req_body, res, res_body):
        """Captures a response and its body that relate to a previous request.

        Args:
            req: The original request (an instance of CaptureRequestHandler).
            req_body: The body of the original request.
            res: The response (a http.client.HTTPResponse instance) that corresponds to the request.
            res_body: The binary response body.
        """
        log.info('Capturing response: %s %s %s', req.path, res.status, res.reason)
        self.server.storage.save_response(req.id, res, res_body)

        # Although we didn't modify the response body, we return it here to trigger
        # proxy2 to re-encode it. Otherwise it seems that that browser (Firefox/Chrome)
        # takes a lot longer to decode the body, for reasons unknown.
        return res_body

    def save_handler(self, req, req_body, res, res_body):
        # Override this to prevent our superclass from pumping out logging info.
        pass

    @property
    def certdir(self):
        """Overrides the certdir attribute to retrieve the storage-specific certificate directory."""
        return self.server.storage.get_cert_dir()

    def log_request(self, code='-', size='-'):
        # Send server log messages through our own logging config.
        try:
            log.debug('%s %s', self.path, code)
        except AttributeError:
            pass

    def log_message(self, format_, *args):
        # Send messages through our own logging config.
        log.debug(format_, *args)

    def log_error(self, format_, *args):
        # suppress "Request timed out: timeout('timed out',)"
        if isinstance(args[0], socket.timeout):
            return
        # Send server error messages through our own logging config.
        log.debug(format_, *args, exc_info=True)

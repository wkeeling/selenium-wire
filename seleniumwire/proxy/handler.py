import json
import logging
import re
import socket
from urllib.parse import parse_qs, urlparse

from .proxy2 import ProxyRequestHandler
from .request import Request, Response
from .utils import is_list_alike

log = logging.getLogger(__name__)

ADMIN_PATH = 'http://seleniumwire'


class AdminMixin:
    """Mixin class that allows remote admin clients to interact with the proxy server.

    This class intercepts administration requests and dispatches them to
    relevant handler methods.
    """
    def dispatch_admin(self, request):
        """Dispatch the admin request for processing.

        Args:
            request: The request object.
        Returns: A response object.
        """
        parse_result = urlparse(request.path)
        path, params = parse_result.path, parse_qs(parse_result.query)
        response = None

        if path == '/requests':
            if request.method == 'GET':
                response = self._get_requests()
            elif request.method == 'DELETE':
                response = self._clear_requests()
        elif path == '/last_request':
            response = self._get_last_request()
        elif path == '/request_body':
            response = self._get_request_body(**params)
        elif path == '/response_body':
            response = self._get_response_body(**params)
        elif path == '/find':
            response = self._find_request(**params)
        elif path == '/header_overrides':
            if request.method == 'POST':
                response = self._set_header_overrides(request)
            elif request.method == 'DELETE':
                response = self._clear_header_overrides()
            elif request.method == 'GET':
                response = self._get_header_overrides()
        elif path == '/rewrite_rules':
            if request.method == 'POST':
                response = self._set_rewrite_rules(request)
            elif request.method == 'DELETE':
                response = self._clear_rewrite_rules()
            elif request.method == 'GET':
                response = self._get_rewrite_rules()
        elif path == '/scopes':
            if request.method == 'POST':
                response = self._set_scopes(request)
            elif request.method == 'DELETE':
                response = self._reset_scopes()
            elif request.method == 'GET':
                response = self._get_scopes()

        if response is None:
            raise RuntimeError(
                'No handler configured for: {} {}'.format(request.method, request.path)
            )

        return response

    def _get_requests(self):
        return self._create_response(json.dumps(
            [r.to_dict() for r in self.storage.load_requests()]
        ).encode('utf-8'))

    def _get_last_request(self):
        request = self.storage.load_last_request()
        if request is not None:
            request = request.to_dict()
        return self._create_response(json.dumps(request).encode('utf-8'))

    def _clear_requests(self):
        self.storage.clear_requests()
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_request_body(self, request_id):
        body = self.storage.load_request_body(request_id[0])
        return self._create_response(body, 'application/octet-stream')

    def _get_response_body(self, request_id):
        body = self.storage.load_response_body(request_id[0])
        return self._create_response(body, 'application/octet-stream')

    def _find_request(self, path):
        request = self.storage.find(path[0])
        if request is not None:
            request = request.to_dict()
        return self._create_response(json.dumps(request).encode('utf-8'))

    def _set_header_overrides(self, request):
        headers = json.loads(request.body.decode('utf-8'))
        self.modifier.headers = headers
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_header_overrides(self):
        del self.modifier.headers
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_header_overrides(self):
        return self._create_response(json.dumps(self.modifier.headers).encode('utf-8'))

    def _set_rewrite_rules(self, request):
        rewrite_rules = json.loads(request.body.decode('utf-8'))
        self.modifier.rewrite_rules = rewrite_rules
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_rewrite_rules(self):
        del self.modifier.rewrite_rules
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_rewrite_rules(self):
        return self._create_response(json.dumps(self.modifier.rewrite_rules).encode('utf-8'))

    def _set_scopes(self, request):
        scopes = json.loads(request.body.decode('utf-8'))
        self.scopes = scopes
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _reset_scopes(self):
        self.scopes = []
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_scopes(self):
        return self._create_response(json.dumps(self.scopes).encode('utf-8'))

    def _create_response(self, body, content_type='application/json'):
        response = Response(
            status=200,
            reason='OK',
            headers={
                'Content-Type': content_type,
            },
            body=body
        )

        return response


class CaptureMixin:
    """Mixin that handles the capturing of requests and responses."""

    def capture_request(self, request):
        """Capture a request and save the unique id associated with the
        captured request in the id field.

        Args:
            request: The request to capture.
        Returns: The captured request id.
        """
        ignore_method = request.method in self.options.get(
            'ignore_http_methods', ['OPTIONS'])
        not_in_scope = not self._in_scope(self.scopes, request.path)
        if ignore_method or not_in_scope:
            log.debug('Not capturing %s request: %s', request.method, request.path)
            return

        log.info('Capturing request: %s', request.path)

        # First make any modifications to the request
        self.modifier.modify(request)

        # Save the request to our storage
        self.storage.save_request(request)

    def capture_response(self, request_id, path, response):
        """Capture a response and its body that relate to a previous request.

        Args:
            request_id: The id of the original request.
            path: The request path.
            response: The response to capture.
        """
        log.info('Capturing response: %s %s %s', path, response.status, response.reason)
        self.storage.save_response(request_id, response)

    def _in_scope(self, scopes, path):
        if not scopes:
            return True
        elif not is_list_alike(scopes):
            scopes = [scopes]
        for scope in scopes:
            match = re.search(scope, path)
            if match:
                return True
        return False


class CaptureRequestHandler(CaptureMixin, AdminMixin, ProxyRequestHandler):
    """Specialisation of ProxyRequestHandler that captures requests and responses
    that pass through the proxy server and allows admin clients to access that data.
    """
    admin_path = ADMIN_PATH

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except (ConnectionError, socket.timeout, FileNotFoundError) as e:
            # Suppress connectivity related tracebacks to prevent these normally
            # harmless exceptions from alarming users. These exceptions can often
            # occur during server shutdown.
            if self.server.options.get('suppress_connection_errors', True):
                log.debug(str(e))
            else:
                raise e

    def handle_request(self, req, req_body):
        """Captures a request and its body.

        Args:
            req: The request (an instance of CaptureRequestHandler).
            req_body: The binary request body.
        """
        # Convert the implementation specific request to one of our requests
        # for handling.
        request = self._create_request(req, req_body)

        self.capture_request(request)
        req.id = request.id

    def handle_response(self, req, req_body, res, res_body):
        """Captures a response and its body that relate to a previous request.

        Args:
            req: The original request (an instance of CaptureRequestHandler).
            req_body: The body of the original request.
            res: The response (a http.client.HTTPResponse instance) that corresponds to the request.
            res_body: The binary response body.
        """
        if not hasattr(req, 'id'):
            # Request was not stored
            return

        # Convert the implementation specific response to one of our responses
        # for handling.
        response = Response(
            status=res.status,
            reason=res.reason,
            headers=dict(res.headers),
            body=res_body
        )

        self.capture_response(req.id, req.path, response)

    def handle_admin(self):
        """Handle an admin request."""
        content_length = int(self.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length)
        request = self._create_request(self, req_body)

        response = self.dispatch_admin(request)

        self.send_response(response.status)

        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()

        self.wfile.write(response.body)

    def _create_request(self, req, req_body):
        request = Request(
            method=req.command,
            path=req.path,
            headers=dict(req.headers),
            body=req_body
        )

        return request

    @property
    def options(self):
        return self.server.options

    @options.setter
    def options(self, options):
        self.server.options = options

    @property
    def scopes(self):
        return self.server.scopes

    @scopes.setter
    def scopes(self, scopes):
        self.server.scopes = scopes

    @property
    def modifier(self):
        return self.server.modifier

    @modifier.setter
    def modifier(self, modifier):
        self.server.modifier = modifier

    @property
    def storage(self):
        return self.server.storage

    @storage.setter
    def storage(self, storage):
        self.server.storage = storage

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
        # Suppress "Request timed out: timeout('timed out',)"
        if args and isinstance(args[0], socket.timeout):
            return
        # Send server error messages through our own logging config.
        log.error(format_, *args, exc_info=True)


def create_custom_capture_request_handler(custom_response_handler):
    """Creates a custom class derived from CaptureRequestHandler with the
    response_handler method overwritten to return
    custom_response_handler after running super().response_handler
    """
    class CustomCaptureRequestHandler(CaptureRequestHandler):
        def handle_response(self, *args, **kwargs):
            super().handle_response(*args, **kwargs)
            return custom_response_handler(*args, **kwargs)
    return CustomCaptureRequestHandler

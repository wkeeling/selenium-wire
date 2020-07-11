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

        request_mappings = {
            '/requests': {
                'GET': self._get_requests,
                'DELETE': self._clear_requests
            },
            '/last_request': {
                'GET': self._get_last_request
            },
            '/request_body': {
                'GET': self._get_request_body
            },
            '/response_body': {
                'GET': self._get_response_body
            },
            '/find': {
                'GET': self._find_request
            },
            '/header_overrides': {
                'GET': self._get_header_overrides,
                'POST': self._set_header_overrides,
                'DELETE': self._clear_header_overrides
            },
            '/param_overrides': {
                'GET': self._get_param_overrides,
                'POST': self._set_param_overrides,
                'DELETE': self._clear_param_overrides
            },
            '/querystring_overrides': {
                'GET': self._get_querystring_overrides,
                'POST': self._set_querystring_overrides,
                'DELETE': self._clear_querystring_overrides
            },
            '/rewrite_rules': {
                'GET': self._get_rewrite_rules,
                'POST': self._set_rewrite_rules,
                'DELETE': self._clear_rewrite_rules
            },
            '/scopes': {
                'GET': self._get_scopes,
                'POST': self._set_scopes,
                'DELETE': self._reset_scopes
            },
            '/initialise': {
                'POST': self._initialise
            }
        }

        try:
            func = request_mappings[path][request.method]
        except KeyError:
            raise RuntimeError(
                'No handler configured for: {} {}'.format(request.method, request.path)
            )

        return func(request, **params)

    def _get_requests(self, _):
        return self._create_response(json.dumps(
            [r.to_dict() for r in self.storage.load_requests()]
        ).encode('utf-8'))

    def _get_last_request(self, _):
        request = self.storage.load_last_request()
        if request is not None:
            request = request.to_dict()
        return self._create_response(json.dumps(request).encode('utf-8'))

    def _clear_requests(self, _):
        self.storage.clear_requests()
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_request_body(self, _, request_id):
        body = self.storage.load_request_body(request_id[0])
        return self._create_response(body, 'application/octet-stream')

    def _get_response_body(self, _, request_id):
        body = self.storage.load_response_body(request_id[0])
        return self._create_response(body, 'application/octet-stream')

    def _find_request(self, _, path):
        request = self.storage.find(path[0])
        if request is not None:
            request = request.to_dict()
        return self._create_response(json.dumps(request).encode('utf-8'))

    def _set_header_overrides(self, request):
        headers = json.loads(request.body.decode('utf-8'))
        self.modifier.headers = headers
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_header_overrides(self, _):
        del self.modifier.headers
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_header_overrides(self, _):
        return self._create_response(json.dumps(self.modifier.headers).encode('utf-8'))

    def _set_param_overrides(self, request):
        params = json.loads(request.body.decode('utf-8'))
        self.modifier.params = params
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_param_overrides(self, _):
        del self.modifier.params
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_param_overrides(self, _):
        return self._create_response(json.dumps(self.modifier.params).encode('utf-8'))

    def _set_querystring_overrides(self, request):
        querystring = json.loads(request.body.decode('utf-8'))['overrides']
        self.modifier.querystring = querystring
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_querystring_overrides(self, _):
        del self.modifier.querystring
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_querystring_overrides(self, _):
        return self._create_response(json.dumps({
            'overrides': self.modifier.querystring}
        ).encode('utf-8'))

    def _set_rewrite_rules(self, request):
        rewrite_rules = json.loads(request.body.decode('utf-8'))
        self.modifier.rewrite_rules = rewrite_rules
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _clear_rewrite_rules(self, _):
        del self.modifier.rewrite_rules
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_rewrite_rules(self, _):
        return self._create_response(json.dumps(self.modifier.rewrite_rules).encode('utf-8'))

    def _set_scopes(self, request):
        scopes = json.loads(request.body.decode('utf-8'))
        self.scopes = scopes
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _reset_scopes(self, _):
        self.scopes = []
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _get_scopes(self, _):
        return self._create_response(json.dumps(self.scopes).encode('utf-8'))

    def _initialise(self, request):
        options = json.loads(request.body.decode('utf-8'))
        self.initialise(options)
        return self._create_response(json.dumps({'status': 'ok'}).encode('utf-8'))

    def _create_response(self, body, content_type='application/json'):
        response = Response(
            status_code=200,
            reason='OK',
            headers={
                'Content-Type': content_type,
            },
            body=body
        )

        response.headers['Content-Length'] = len(response.body)

        return response

    def initialise(self, options):
        """Perform any initialisation actions.

        Args:
            options: The selenium wire options.
        """
        pass


class CaptureMixin:
    """Mixin that handles the capturing of requests and responses."""

    def capture_request(self, request):
        """Capture a request and save the unique id associated with the
        captured request in the id field.

        If any modification rules are set, the request will be modified
        before capture.

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

        # Save the request to our storage
        self.storage.save_request(request)

    def capture_response(self, request_id, url, response):
        """Capture a response and its body that relate to a previous request.

        Args:
            request_id: The id of the original request.
            url: The request url.
            response: The response to capture.
        """
        log.info('Capturing response: %s %s %s', url, response.status_code, response.reason)
        self.storage.save_response(request_id, response)

    def _in_scope(self, scopes, url):
        if not scopes:
            return True
        elif not is_list_alike(scopes):
            scopes = [scopes]
        for scope in scopes:
            match = re.search(scope, url)
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
        # First make any modifications to the request
        self.modifier.modify(req, url_attr='path')

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
            status_code=res.status,
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

        self.send_response(response.status_code)

        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()

        self.wfile.write(response.body)

    def _create_request(self, req, req_body):
        request = Request(
            method=req.command,
            url=req.path,
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
    handle_response method overwritten to return
    custom_response_handler after running super().handle_response
    """
    class CustomCaptureRequestHandler(CaptureRequestHandler):
        def handle_response(self, *args, **kwargs):
            super().handle_response(*args, **kwargs)
            return custom_response_handler(*args, **kwargs)
    return CustomCaptureRequestHandler

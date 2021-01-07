import logging
import re
import socket
from http.client import HTTPMessage

from .proxy2 import ProxyRequestHandler
from .request import Request, Response
from .utils import is_list_alike

log = logging.getLogger(__name__)


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
        ignore_method = request.method in self.server.options.get(
            'ignore_http_methods', ['OPTIONS'])
        not_in_scope = not self.in_scope(self.server.scopes, request.url)
        if ignore_method or not_in_scope:
            log.debug('Not capturing %s request: %s', request.method, request.url)
            return

        log.info('Capturing request: %s', request.url)

        # Save the request to our storage
        self.server.storage.save_request(request)

    def capture_response(self, request_id, url, response):
        """Capture a response and its body that relate to a previous request.

        Args:
            request_id: The id of the original request.
            url: The request url.
            response: The response to capture.
        """
        log.info('Capturing response: %s %s %s', url, response.status_code, response.reason)

        self.server.storage.save_response(request_id, response)

    def in_scope(self, scopes, url):
        if not scopes:
            return True
        elif not is_list_alike(scopes):
            scopes = [scopes]
        for scope in scopes:
            match = re.search(scope, url)
            if match:
                return True
        return False


class CaptureRequestHandler(CaptureMixin, ProxyRequestHandler):
    """Specialisation of ProxyRequestHandler that captures requests and responses
    that pass through the proxy server.
    """
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
        # DEPRECATED. This will be replaced by request_interceptor
        req.body = req_body  # Temporarily attach the body to the request for modification
        self.server.modifier.modify_request(req, urlattr='path', methodattr='command')
        req_body = req.body

        # Convert the implementation specific request to one of our requests
        # for handling.
        request = self._create_request(req, req_body)

        # Call the request interceptor if set
        if self.server.request_interceptor is not None:
            self.server.request_interceptor(request)

            if request.response:
                # The interceptor has created a response for us to send back immediately
                self.commit_response(
                    request.response.status_code,
                    request.response.reason,
                    request.response.headers,
                    request.response.body
                )
                return False  # Signals that we've committed the response ourselves

            # Transfer any modifications to the original request
            req.command = request.method
            req.path = request.url
            req.headers = HTTPMessage()

            for name, val in request.headers.items():
                req.headers.add_header(name, val)

            if request.body:
                req_body = request.body

        self.capture_request(request)

        if request.id is not None:  # Will not be None when captured
            req.id = request.id

        return req_body

    def handle_response(self, req, req_body, res, res_body):
        """Captures a response and its body that relate to a previous request.

        Args:
            req: The original request (an instance of CaptureRequestHandler).
            req_body: The body of the original request.
            res: The response (a http.client.HTTPResponse instance) that corresponds to the request.
            res_body: The binary response body.
        """
        # Make any modifications to the response
        # DEPRECATED. This will be replaced by response_interceptor.
        self.server.modifier.modify_response(res, req, urlattr='path')

        if not hasattr(req, 'id'):
            # Request was not captured
            return

        # Convert the implementation specific response to one of our responses
        # for handling.
        response = Response(
            status_code=res.status,
            reason=res.reason,
            headers=res.headers.items(),
            body=res_body
        )

        # Call the response interceptor if set
        if self.server.response_interceptor is not None:
            self.server.response_interceptor(self._create_request(req, req_body, response), response)
            # Transfer any modifications to the original response
            res.status = response.status_code
            res.reason = response.reason
            res.headers = HTTPMessage()

            for name, val in response.headers.items():
                res.headers.add_header(name, val)

            if response.body:
                res_body = response.body

        self.capture_response(req.id, req.path, response)

        return res_body

    def _create_request(self, req, req_body, response=None):
        request = Request(
            method=req.command,
            url=req.path,
            headers=req.headers.items(),
            body=req_body
        )
        request.response = response

        return request

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

    DEPRECATED. Use response_interceptor.
    """
    class CustomCaptureRequestHandler(CaptureRequestHandler):
        def handle_response(self, *args, **kwargs):
            super().handle_response(*args, **kwargs)
            return custom_response_handler(*args, **kwargs)
    return CustomCaptureRequestHandler

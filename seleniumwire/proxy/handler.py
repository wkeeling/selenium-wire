import logging

from .proxy2 import ProxyRequestHandler

log = logging.getLogger(__name__)

ADMIN_PATH = 'http://seleniumwire'


class AdminMixin:
    """Mixin class that allows remote clients to interact with the proxy server.

    This class intercepts administration requests and dispatches them to
    relevant handler methods.
    """

    admin_path = ADMIN_PATH

    def admin_handler(self):
        if self._is_path('/requests'):
            self._get_captured_requests()

    def _is_path(self, path):
        return self.path == '{}{}'.format(self.admin_path, path)

    def _get_captured_requests(self):
        self._send_response('OK')

    def _send_response(self, body, is_json=False):
        content_type = 'application/json' if is_json else 'text/plain'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))


class CaptureRequestHandler(AdminMixin, ProxyRequestHandler):

    def request_handler(self, req, req_body):
        log.info('Capturing request: {}'.format(req.path))

    def save_handler(self, req, req_body, res, res_body):
        pass

    def log_request(self, code='-', size='-'):
        log.debug('{} {}'.format(self.path, code))

    def log_error(self, format_, *args):
        log.debug('{} {}'.format(self.path, format_ % args))



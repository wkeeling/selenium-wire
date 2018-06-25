import json
import logging

from .proxy2 import ProxyRequestHandler
from .storage import storage

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
            self._captured_requests()

    def _is_path(self, path):
        return self.path == '{}{}'.format(self.admin_path, path)

    def _captured_requests(self):
        self._send_response(json.dumps(storage.load_requests()).encode('utf-8'), 'application/json')

    def _send_response(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


class CaptureRequestHandler(AdminMixin, ProxyRequestHandler):

    def request_handler(self, req, req_body):
        log.info('Capturing request: {}'.format(req.path))
        storage.save_request(req, req_body)

    def save_handler(self, req, req_body, res, res_body):
        pass

    def log_request(self, code='-', size='-'):
        log.debug('{} {}'.format(self.path, code))

    def log_error(self, format_, *args):
        log.debug(format_ % args)


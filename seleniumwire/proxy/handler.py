import logging
import threading

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
        if self._is_path('/start_capture'):
            self._start_capture()

    def _is_path(self, path):
        return self.path == '{}{}'.format(self.admin_path, path)

    def _start_capture(self):
        self.capture.set()
        self._send_response('OK')

    def _send_response(self, body, is_json=False):
        content_type = 'application/json' if is_json else 'text/plain'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))


class CaptureRequestHandler(AdminMixin, ProxyRequestHandler):

    capture = threading.Event()

    def request_handler(self, req, req_body):
        if self.capture.is_set():
            log.info('Capturing request: {}'.format(req.path))
        else:
            log.info('Not capturing request: {}'.format(req.path))

    def save_handler(self, req, req_body, res, res_body):
        pass

    def log_request(self, code='-', size='-'):
        log.debug('{} {}'.format(self.path, code))

    def log_error(self, format_, *args):
        log.debug('{} {}'.format(self.path, format_ % args))



import logging
import threading

from .proxy2 import ProxyRequestHandler

log = logging.getLogger(__name__)

ADMIN_PATH = 'http://seleniumwire'


class AdministrationMixin:
    """Mixin class that allows remote clients to interact with the proxy server.

    This class intercepts administration requests and dispatches them to
    relevant handler methods.
    """

    admin_path = ADMIN_PATH

    def admin_handler(self):
        if self._is_path('/capture'):
            self._start_capture()

    def _is_path(self, path):
        return self.path == '{}{}'.format(self.admin_path, path)

    def _start_capture(self):
        self.capture.set()


class CaptureRequestHandler(AdministrationMixin, ProxyRequestHandler):

    capture = threading.Event()

    def request_handler(self, req, req_body):
        if self.capture.is_set():
            log.info('Capturing request: {}'.format(req.path))
        else:
            log.info('Not capturing request: {}'.format(req.path))

    def save_handler(self, req, req_body, res, res_body):
        pass


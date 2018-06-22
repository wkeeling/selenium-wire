import logging
import threading

from .proxy2 import ProxyRequestHandler

log = logging.getLogger(__name__)
admin_path = 'http://seleniumwire'


class AdministrationMixin:
    """Mixin class that allows remote clients to interact with the proxy server,
    exposing an API of administrative functions.
    """

    @classmethod
    def start_capture(cls):
        cls.capture.set()

    @classmethod
    def path(cls, path):
        return '{}{}'.format(cls.admin_path, path)

    mappings = {
        path('/capture_requests'): start_capture
    }

    def admin_handler(self):
        handler = self.mappings.get(self.path)

        if handler is not None:
            handler()


class CaptureRequestHandler(AdministrationMixin, ProxyRequestHandler):

    capture = threading.Event()

    def request_handler(self, req, req_body):
        if self.capture.is_set():
            print('Capturing request')


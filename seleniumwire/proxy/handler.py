from .proxy2 import ProxyRequestHandler


class AdministrationMixin:

    admin_path = 'http://seleniumwire'

    def admin_handler(self):
        pass


class CaptureRequestHandler(AdministrationMixin, ProxyRequestHandler):
    pass


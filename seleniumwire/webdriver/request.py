from seleniumwire.proxy import client


class RequestMixin:
    """Mixin class that provides the capture and manipulation of browser reqeusts."""

    def capture_requests(self):
        client.capture_requests()

    def end_capture_requests(self):
        pass

    @property
    def requests(self):
        pass

    @property
    def last_request(self):
        pass

    def requests_for(self, path):
        pass

    def header_overrides(self, headers):
        pass


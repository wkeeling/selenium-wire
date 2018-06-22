from seleniumwire.proxy import client


class InspectRequestsMixin:
    """Mixin class that provides functions to capture and inspect browser requests."""

    def capture_requests(self):
        client.start_capture()

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

    def _create_proxy(self):
        return client.create_proxy()

    def _destroy_proxy(self):
        client.destroy_proxy()

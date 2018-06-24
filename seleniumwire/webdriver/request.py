from seleniumwire.proxy import client


class InspectRequestsMixin:
    """Mixin class that provides functions to capture and inspect browser requests."""

    @property
    def requests(self):
        # Want to be able to support:
        #
        # webdriver.requests -> []  (list of all requests)
        # webdriver.requests['/path/of/some/request'] -> []  (list of all requests that match)
        # del webdriver.requests (clears the requests from the proxy)
        return client.requests()

    @requests.deleter
    def requests(self):
        pass

    @property
    def last_request(self):
        pass

    def requests_for(self, path):
        pass

    @property
    def header_overrides(self):
        # Support del firefox.header_overrides to clear all overrides?
        pass

    @header_overrides.setter
    def header_overrides(self, headers):
        pass

    @header_overrides.deleter
    def header_overrides(self):
        pass

    def _create_proxy(self):
        return client.create_proxy()

    def _destroy_proxy(self):
        client.destroy_proxy()

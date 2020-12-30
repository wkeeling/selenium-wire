import inspect
import time
from typing import List, Union

from selenium.common.exceptions import TimeoutException

from ..proxy.request import Request


class InspectRequestsMixin:
    """Mixin class that provides functions to inspect and modify browser requests."""

    @property
    def requests(self) -> List[Request]:
        """Retrieves the requests made between the browser and server.

        Captured requests can be cleared with 'del', e.g:

            del firefox.requests

        Returns:
            A list of Request instances representing the requests made
            between the browser and server.
        """
        return self.proxy.storage.load_requests()

    @requests.deleter
    def requests(self):
        self.proxy.storage.clear_requests()

    @property
    def last_request(self) -> Union[Request, None]:
        """Retrieve the last request made between the browser and server.

        Note that this is more efficient than running requests[-1]

        Returns:
            A Request instance representing the last request made, or
            None if no requests have been made.
        """
        return self.proxy.storage.load_last_request()

    def wait_for_request(self, path: str, timeout: int = 10) -> Request:
        """Wait up to the timeout period for a request with the specified
        path to be seen.

        The path attribute can be can be a regex that will be searched in the
        full request URL. If a request is not seen before the timeout then a
        TimeoutException is raised. Only requests with corresponding responses
        are considered.

        Given that path can be a regex, ensure that any special characters
        (e.g. question marks) are escaped.

        Args:
            path: The path of the request to look for. A regex can be supplied.
            timeout: The maximum time to wait in seconds. Default 10s.

        Returns:
            The request.
        Raises:
            TimeoutException if a request is not seen within the timeout
                period.
        """
        start = time.time()

        while time.time() - start < timeout:
            request = self.proxy.storage.find(path)

            if request is None:
                time.sleep(0.2)
            else:
                return request

        raise TimeoutException('Timed out after {}s waiting for request {}'.format(timeout, path))

    @property
    def header_overrides(self):
        """The header overrides for outgoing browser requests.

        DEPRECATED. Use request_interceptor and response_interceptor.

        The value of the headers can be a dictionary or list of sublists,
        with each sublist having two elements - a URL pattern and headers.
        Where a header in the dictionary exists in the request, the dictionary
        value will overwrite the one in the request. Where a header in the dictionary
        does not exist in the request, it will be added to the request as a
        new header. To filter out a header from the request, set that header
        in the dictionary to None. Header names are case insensitive.
        For response headers, prefix the header name with 'response:'.

        For example:

            header_overrides = {
                'User-Agent': 'Firefox',
                'response:Cache-Control': 'none'
            }
            header_overrides = [
                ('.*somewhere.com.*', {'User-Agent': 'Firefox', 'response:Cache-Control': 'none'}),
                ('*.somewhere-else.com.*', {'User-Agent': 'Chrome'})
            ]
        """
        return self.proxy.modifier.headers

    @header_overrides.setter
    def header_overrides(self, headers):
        if isinstance(headers, list):
            for _, h in headers:
                self._validate_headers(h)
        else:
            self._validate_headers(headers)

        self.proxy.modifier.headers = headers

    def _validate_headers(self, headers):
        for v in headers.values():
            if v is not None:
                assert isinstance(v, str), 'Header values must be strings'

    @header_overrides.deleter
    def header_overrides(self):
        del self.proxy.modifier.headers

    @property
    def param_overrides(self):
        """The parameter overrides for outgoing browser requests.

        DEPRECATED. Use request_interceptor.

        For POST requests, the parameters are assumed to be encoded in the
        request body.

        The value of the params can be a dictionary or list of sublists,
        with each sublist having two elements - a URL pattern and params.
        Where a param in the dictionary exists in the request, the dictionary
        value will overwrite the one in the request. Where a param in the dictionary
        does not exist in the request, it will be added to the request as a
        new param. To filter out a param from the request, set that param
        in the dictionary to None.

        For example:
            param_overrides = {'foo': 'bar'}
            param_overrides = [
                ('.*somewhere.com.*', {'foo': 'bar'}),
                ('*.somewhere-else.com.*', {'x': 'y'}),
            ]
        """
        return self.proxy.modifier.params

    @param_overrides.setter
    def param_overrides(self, params):
        self.proxy.modifier.params = params

    @param_overrides.deleter
    def param_overrides(self):
        del self.proxy.modifier.params

    @property
    def body_overrides(self):
        """The body overrides for outgoing browser requests.

        DEPRECATED. Use request_interceptor and response_interceptor.

        For 'not GET' requests, the parameters are assumed to be encoded in the
        request body.

        The value of the body can be a string value or list of sublists,
        with each sublist having two elements - a URL pattern and string value.
        The string value will be encoded, then replace whole http body.
        And body_overrides has higher priority than param_overrides When they conflict.
        For example:
            body_overrides = '{"foo":"bar"}'
            body_overrides = [
                ('.*somewhere.com.*', '{"foo":"bar"}'),
                ('*.somewhere-else.com.*', '{"x":"y"}'),
            ]
        """
        return self.proxy.modifier.bodies

    @body_overrides.setter
    def body_overrides(self, bodies):
        self.proxy.modifier.bodies = bodies

    @body_overrides.deleter
    def body_overrides(self):
        del self.proxy.modifier.bodies

    @property
    def querystring_overrides(self):
        """The querystring overrides for outgoing browser requests.

        DEPRECATED. Use request_interceptor.

        The value of the querystring override can be a string or a list of sublists,
        with each sublist having two elements, a URL pattern and the querystring.
        The querystring override will overwrite the querystring in the request
        or will be added to the request if the request has no querystring. To
        remove a querystring from the request, set the value to empty string.

        For example:
            querystring_overrides = 'foo=bar&x=y'
            querystring_overrides = [
                ('.*somewhere.com.*', 'foo=bar&x=y'),
                ('*.somewhere-else.com.*', 'a=b&c=d'),
            ]
        """
        return self.proxy.modifier.querystring

    @querystring_overrides.setter
    def querystring_overrides(self, querystrings):
        self.proxy.modifier.querystring = querystrings

    @querystring_overrides.deleter
    def querystring_overrides(self):
        del self.proxy.modifier.querystring

    @property
    def rewrite_rules(self):
        """The rules used to rewrite request URLs.

        DEPRECATED. Use request_interceptor.

        The value of the rewrite rules should be a list of sublists (or tuples)
        with each sublist containing the pattern and replacement.

        For example:
            rewrite_rules = [
                (r'(https?://)www.google.com/', r'\1www.bing.com/'),
                (r'https://docs.python.org/2/', r'https://docs.python.org/3/'),
            ]
        """
        return self.proxy.modifier.rewrite_rules

    @rewrite_rules.setter
    def rewrite_rules(self, rewrite_rules):
        self.proxy.modifier.rewrite_rules = rewrite_rules

    @rewrite_rules.deleter
    def rewrite_rules(self):
        del self.proxy.modifier.rewrite_rules

    @property
    def scopes(self) -> List[str]:
        """The URL patterns used to scope request capture.

        The value of the scopes should be a list (or tuple) of
        regular expressions.

        For example:
            scopes = [
                '.*stackoverflow.*',
                '.*github.*'
            ]
        """
        return self.proxy.scopes

    @scopes.setter
    def scopes(self, scopes: List[str]):
        self.proxy.scopes = scopes

    @scopes.deleter
    def scopes(self):
        self.proxy.scopes = []

    @property
    def request_interceptor(self) -> callable:
        """A callable that will be used to intercept/modify requests.

        The callable must accept a single argument for the request
        being intercepted.
        """
        return self.proxy.request_interceptor

    @request_interceptor.setter
    def request_interceptor(self, interceptor: callable):
        self.proxy.request_interceptor = interceptor

    @request_interceptor.deleter
    def request_interceptor(self):
        self.proxy.request_interceptor = None

    @property
    def response_interceptor(self) -> callable:
        """A callable that will be used to intercept/modify responses.

        The callable must accept two arguments: the response being
        intercepted and the originating request.
        """
        return self.proxy.response_interceptor

    @response_interceptor.setter
    def response_interceptor(self, interceptor: callable):
        if len(inspect.signature(interceptor).parameters) != 2:
            raise RuntimeError('A response interceptor takes two parameters: the request and response')
        self.proxy.response_interceptor = interceptor

    @response_interceptor.deleter
    def response_interceptor(self):
        self.proxy.response_interceptor = None

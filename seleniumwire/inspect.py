import inspect
import time
from typing import Callable, Iterator, List, Optional, Union

from selenium.common.exceptions import TimeoutException  # type: ignore

from seleniumwire import har
from seleniumwire.request import Request


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
        return self.backend.storage.load_requests()  # type: ignore

    @requests.deleter
    def requests(self):
        self.backend.storage.clear_requests()  # type: ignore

    def iter_requests(self) -> Iterator[Request]:
        """Return an iterator of requests.

        Returns: An iterator.
        """
        yield from self.backend.storage.iter_requests()  # type: ignore

    @property
    def last_request(self) -> Optional[Request]:
        """Retrieve the last request made between the browser and server.

        Note that this is more efficient than running requests[-1]

        Returns:
            A Request instance representing the last request made, or
            None if no requests have been made.
        """
        return self.backend.storage.load_last_request()  # type: ignore

    def wait_for_request(self, pat: str, timeout: Union[int, float] = 10) -> Request:
        """Wait up to the timeout period for a request matching the specified
        pattern to be seen.

        The pat attribute can be can be a simple substring or a regex that will
        be searched in the full request URL. If a request is not seen before the
        timeout then a TimeoutException is raised. Only requests with corresponding
        responses are considered.

        Given that pat can be a regex, ensure that any special characters
        (e.g. question marks) are escaped.

        Args:
            pat: The pat of the request to look for. A regex can be supplied.
            timeout: The maximum time to wait in seconds. Default 10s.

        Returns:
            The request.
        Raises:
            TimeoutException if a request is not seen within the timeout
                period.
        """
        start = time.time()

        while time.time() - start < timeout:
            request = self.backend.storage.find(pat)  # type: ignore

            if request is None:
                time.sleep(1 / 5)
            else:
                return request

        raise TimeoutException('Timed out after {}s waiting for request matching {}'.format(timeout, pat))

    @property
    def har(self) -> str:
        """Get a HAR archive of HTTP transactions that have taken place.

        Note that the enable_har option needs to be set before HAR
        data will be captured.

        Returns: A JSON string of HAR data.
        """
        return har.generate_har(self.backend.storage.load_har_entries())  # type: ignore

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
        return self.backend.modifier.headers  # type: ignore

    @header_overrides.setter
    def header_overrides(self, headers):
        if isinstance(headers, list):
            for _, h in headers:
                self._validate_headers(h)
        else:
            self._validate_headers(headers)

        self.backend.modifier.headers = headers  # type: ignore

    def _validate_headers(self, headers):
        for v in headers.values():
            if v is not None:
                assert isinstance(v, str), 'Header values must be strings'

    @header_overrides.deleter  # type: ignore
    def header_overrides(self):
        del self.backend.modifier.headers  # type: ignore

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
        return self.backend.modifier.params  # type: ignore

    @param_overrides.setter
    def param_overrides(self, params):
        self.backend.modifier.params = params  # type: ignore

    @param_overrides.deleter
    def param_overrides(self):
        del self.backend.modifier.params  # type: ignore

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
        return self.backend.modifier.bodies  # type: ignore

    @body_overrides.setter
    def body_overrides(self, bodies):
        self.backend.modifier.bodies = bodies  # type: ignore

    @body_overrides.deleter
    def body_overrides(self):
        del self.backend.modifier.bodies  # type: ignore

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
        return self.backend.modifier.querystring  # type: ignore

    @querystring_overrides.setter
    def querystring_overrides(self, querystrings):
        self.backend.modifier.querystring = querystrings  # type: ignore

    @querystring_overrides.deleter
    def querystring_overrides(self):
        del self.backend.modifier.querystring  # type: ignore

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
        return self.backend.modifier.rewrite_rules  # type: ignore

    @rewrite_rules.setter
    def rewrite_rules(self, rewrite_rules):
        self.backend.modifier.rewrite_rules = rewrite_rules  # type: ignore

    @rewrite_rules.deleter
    def rewrite_rules(self):
        del self.backend.modifier.rewrite_rules  # type: ignore

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
        return self.backend.scopes  # type: ignore

    @scopes.setter
    def scopes(self, scopes: List[str]):
        self.backend.scopes = scopes  # type: ignore

    @scopes.deleter
    def scopes(self):
        self.backend.scopes = []  # type: ignore

    @property
    def request_interceptor(self) -> Callable:
        """A callable that will be used to intercept/modify requests.

        The callable must accept a single argument for the request
        being intercepted.
        """
        return self.backend.request_interceptor  # type: ignore

    @request_interceptor.setter
    def request_interceptor(self, interceptor: Callable):
        self.backend.request_interceptor = interceptor  # type: ignore

    @request_interceptor.deleter
    def request_interceptor(self):
        self.backend.request_interceptor = None  # type: ignore

    @property
    def response_interceptor(self) -> Callable:
        """A callable that will be used to intercept/modify responses.

        The callable must accept two arguments: the response being
        intercepted and the originating request.
        """
        return self.backend.response_interceptor  # type: ignore

    @response_interceptor.setter
    def response_interceptor(self, interceptor: Callable):
        if len(inspect.signature(interceptor).parameters) != 2:
            raise RuntimeError('A response interceptor takes two parameters: the request and response')
        self.backend.response_interceptor = interceptor  # type: ignore

    @response_interceptor.deleter
    def response_interceptor(self):
        self.backend.response_interceptor = None  # type: ignore

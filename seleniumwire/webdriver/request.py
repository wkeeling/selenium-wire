import time

from selenium.common.exceptions import TimeoutException

from ..proxy.request import Request, Response


class InspectRequestsMixin:
    """Mixin class that provides functions to inspect and modify browser requests."""

    @property
    def requests(self):
        """Retrieves the requests made between the browser and server.

        Captured requests can be cleared with 'del', e.g:

            del firefox.requests

        Returns:
            A list of Request instances representing the requests made
            between the browser and server.
        """
        return [LazyRequest.from_dict(r, self._client) for r in self._client.get_requests()]

    @requests.deleter
    def requests(self):
        self._client.clear_requests()

    @property
    def last_request(self):
        """Retrieve the last request made between the browser and server.

        Note that this is more efficient than running requests[-1]

        Returns:
            A Request instance representing the last request made, or
            None if no requests have been made.
        """
        data = self._client.get_last_request()

        if data is not None:
            return LazyRequest.from_dict(data, self._client)

        return None

    def wait_for_request(self, path, timeout=10):
        """Wait up to the timeout period for a request with the specified
        path to be seen.

        The path attribute can be can be a regex that will be searched in the
        full request URL. If a request is not seen before the timeout then a
        TimeoutException is raised. Only requests with corresponding responses
        are considered.

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
            data = self._client.find(path)

            if data is not None:
                return LazyRequest.from_dict(data, self._client)
            else:
                time.sleep(0.2)

        raise TimeoutException('Timed out after {}s waiting for request {}'.format(timeout, path))

    @property
    def header_overrides(self):
        """The header overrides for outgoing browser requests.

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
        return self._client.get_header_overrides()

    @header_overrides.setter
    def header_overrides(self, headers):
        if isinstance(headers, list):
            for _, h in headers:
                self._validate_headers(h)
        else:
            self._validate_headers(headers)

        self._client.set_header_overrides(headers)

    def _validate_headers(self, headers):
        for v in headers.values():
            if v is not None:
                assert isinstance(v, str), 'Header values must be strings'

    @header_overrides.deleter
    def header_overrides(self):
        self._client.clear_header_overrides()

    @property
    def param_overrides(self):
        """The parameter overrides for outgoing browser requests.

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
        return self._client.get_param_overrides()

    @param_overrides.setter
    def param_overrides(self, params):
        self._client.set_param_overrides(params)

    @param_overrides.deleter
    def param_overrides(self):
        self._client.clear_param_overrides()

    @property
    def body_overrides(self):
        return self._client.get_body_overrides()

    @body_overrides.setter
    def body_overrides(self, bodies):
        self._client.set_body_overrides(bodies)

    @body_overrides.deleter
    def body_overrides(self):
        self._client.clear_body_overrides()

    @property
    def querystring_overrides(self):
        """The querystring overrides for outgoing browser requests.

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
        return self._client.get_querystring_overrides()

    @querystring_overrides.setter
    def querystring_overrides(self, querystrings):
        self._client.set_querystring_overrides(querystrings)

    @querystring_overrides.deleter
    def querystring_overrides(self):
        self._client.clear_querystring_overrides()

    @property
    def rewrite_rules(self):
        """The rules used to rewrite request URLs.

        The value of the rewrite rules should be a list of sublists (or tuples)
        with each sublist containing the pattern and replacement.

        For example:
            rewrite_rules = [
                (r'(https?://)www.google.com/', r'\1www.bing.com/'),
                (r'https://docs.python.org/2/', r'https://docs.python.org/3/'),
            ]
        """
        return self._client.get_rewrite_rules()

    @rewrite_rules.setter
    def rewrite_rules(self, rewrite_rules):
        self._client.set_rewrite_rules(rewrite_rules)

    @rewrite_rules.deleter
    def rewrite_rules(self):
        self._client.clear_rewrite_rules()

    @property
    def scopes(self):
        """The URL patterns used to scope request capture.

        The value of the scopes should be a list (or tuple) of
        regular expressions.

        For example:
            scopes = [
                '.*stackoverflow.*',
                '.*github.*'
            ]
        """
        return self._client.get_scopes()

    @scopes.setter
    def scopes(self, scopes):
        self._client.set_scopes(scopes)

    @scopes.deleter
    def scopes(self):
        self._client.reset_scopes()


class LazyRequest(Request):
    """Specialisation of Request that allows for lazy retrieval of the request body."""

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @Request.body.getter
    def body(self):
        """Lazily retrieves the request body when it is asked for.

        Returns:
            The request body as bytes.
        """
        return self._client.get_request_body(self.id)

    @classmethod
    def from_dict(cls, d, client):
        response = d.pop('response', None)
        request_id = d.pop('id', None)
        request = cls(client, **d)

        if request_id is not None:
            request.id = request_id

        if response is not None:
            request.response = LazyResponse.from_dict(response, client, request_id)

        return request


class LazyResponse(Response):
    """Specialisation of Response that allows for lazy retrieval of the response body."""

    def __init__(self, request_id, client, **kwargs):
        super().__init__(**kwargs)
        self._request_id = request_id
        self._client = client

    @Request.body.getter
    def body(self):
        """Lazily retrieves the response body when it is asked for.

        Returns:
            The response body as bytes.
        """
        return self._client.get_response_body(self._request_id)

    @classmethod
    def from_dict(cls, d, client, request_id):
        return cls(request_id, client, **d)

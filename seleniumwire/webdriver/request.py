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
        return [LazyRequest.from_dict({'client': self._client, **r})
                for r in self._client.get_requests()]

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
            return LazyRequest.from_dict({'client': self._client, **data})

        return None

    def wait_for_request(self, path, timeout=10):
        """Wait up to the timeout period for a request with the specified
        path to be seen.

        The path can be can be any substring of the full request URL.
        If a request is not seen before the timeout then a TimeoutException
        is raised. Only requests with corresponding responses are considered.

        Args:
            path: The path of the request to look for.
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
                return LazyRequest.from_dict({'client': self._client, **data})
            else:
                time.sleep(0.2)

        raise TimeoutException('Timed out after {}s waiting for request {}'.format(timeout, path))

    @property
    def header_overrides(self):
        """The header overrides for outgoing browser requests.

        The value of the headers should be a dictionary. Where a header in
        the dictionary exists in the request, the dictionary value will
        overwrite the one in the request. Where a header in the dictionary
        does not exist in the request, it will be added to the request as a
        new header. To filter out a header from the request, set that header
        in the dictionary with a value of None. Header names are case insensitive.
        """
        return self._client.get_header_overrides()

    @header_overrides.setter
    def header_overrides(self, headers):
        self._client.set_header_overrides(headers)

    @header_overrides.deleter
    def header_overrides(self):
        self._client.clear_header_overrides()

    @property
    def rewrite_rules(self):
        """The rules used to rewrite request URLs.

        The value of the rewrite rules should be a list of sublists (or tuples)
        with each sublist containing the pattern and replacement.

        i.e:
            rewrite_rules = [
                ('pattern', 'replacement'),
                ('pattern', 'replacement'),
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

    @property
    def body(self):
        """Lazily retrieves the request body when it is asked for.

        Returns:
            The request body as bytes.
        """
        if super().body is None:
            super().body = self._client.get_request_body(self.id)

        return super().body


class LazyResponse(Response):
    """Specialisation of Response that allows for lazy retrieval of the request body."""

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self._client = client

    @property
    def body(self):
        """Lazily retrieves the response body when it is asked for.

        Returns:
            The response body as bytes.
        """
        if super().body is None:
            super().body = self._client.get_response_body(self._request_id)

        return super().body

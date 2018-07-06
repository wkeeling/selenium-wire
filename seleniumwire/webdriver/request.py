
class InspectRequestsMixin:
    """Mixin class that provides functions to capture and inspect browser requests."""

    @property
    def requests(self):
        """Retrieves the requests made between the browser and server.

        Captured requests can be cleared with 'del', e.g:

            del firefox.requests

        Returns:
            The requests made between the browser and server.
        """
        return self._client.get_requests()

    @requests.deleter
    def requests(self):
        self._client.clear_requests()

    @property
    def last_request(self):
        """Retrieve the last request made between the browser and server.

        Note that this is more efficient than running requests[-1]

        Returns:
            The last request.
        """
        self._client.get_last_request()

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

    def wait_for_request(self, path, timeout):
        pass

    def _create_proxy(self):
        return self._client.create_proxy()

    def _destroy_proxy(self):
        self._client.destroy_proxy()


class Request:
    """An HTTP request made by the browser to the server.

    This acts as a facade, hiding the details of the underlying proxy
    whilst provding a user friendly API to clients.
    """

    def __init__(self, data, client):
        """Initialises a new Request object with a dictionary of data and a
        proxy client instance.

        See the proxy client doc for the dictionary structure.

        Note that the response attribute may be None where no response is associated
        with a given request.

        Args:
            data: The dictionary of data.
            client: The proxy client instance.
        """
        self._data = data
        self._client = client
        self.method = data['method']
        self.path = data['path']
        self.headers = data['headers']
        if data['response'] is not None:
            self.response = Response(self._data['id'], data['response'], client)
        else:
            self.response = None

    @property
    def body(self):
        """Lazily retrieves the request body when it is asked for.

        Returns:
            The response bytes.
        """
        if self._data.get('body') is None:
            self._data['body'] = self._client.get_request_body(self._data['id'])

        return self._data['body']

    def __repr__(self):
        return 'Request({})'.format(self._data)

    def __str__(self):
        return self.path


class Response:
    """An HTTP response returned from the server to the browser."""

    def __init__(self, request_id, data, client):
        """Initialise a new Response object with a request id, a dictionary
        of data and a proxy client instance.

        See the proxy client doc for the dictionary structure.

        Args:
            request_id: The request id.
            data: The dictionary of data.
            client: The proxy client instance.
        """
        self._request_id = request_id
        self._client = client
        self._data = data
        self.status_code = data['status_code']
        self.reason = data['reason']
        self.headers = data['headers']

    @property
    def body(self):
        """Lazily retrieves the response body when it is asked for.

        Returns:
            The response bytes.
        """
        if self._data.get('body') is None:
            self._data['body'] = self._client.get_response_body(self._request_id)

        return self._data['body']

    def __repr__(self):
        return "Response('{}', {})".format(self._request_id, self._data)

    def __str__(self):
        return '{} {}'.format(self.status_code, self.reason)

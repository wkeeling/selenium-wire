"""Houses the classes used to transfer request and response data between components. """


class Request:
    """Represents an inbound HTTP request."""

    def __init__(self, *, method, path, headers, body=None):
        """Initialise a new Request object.

        Args:
            method: The request method - GET, POST etc.
            path: The request path.
            headers: The request headers as a dictionary.
            body: The request body as bytes.
        """
        self.id = None  # The id is set for captured requests
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.response = None

        if isinstance(self.body, str):
            self.body = self.body.encode('utf-8')

    def to_dict(self):
        d = vars(self)

        if self.response is not None:
            d['response'] = self.response.to_dict()


class Response:
    """Represents an HTTP response."""

    def __init__(self, *, status, reason, headers, body=None):
        """Initialise a new Response object.

        Args:
            status: The status code.
            reason: The reason message (e.g. "OK" or "Not Found").
            headers: The response headers as a dictionary.
            body: The response body as bytes.
        """
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body

        if isinstance(self.body, str):
            self.body = self.body.encode('utf-8')

    def to_dict(self):
        return vars(self)

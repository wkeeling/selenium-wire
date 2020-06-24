"""Houses the classes used to transfer request and response data between components. """


class Request:
    """Represents an inbound HTTP request."""

    def __init__(self, method, path, headers, body=None):
        """Initialise a new Request object.

        Args:
            method: The request method - GET, POST etc.
            path: The request path.
            headers: The request headers as a list of tuples.
            body: The request body as bytes.
        """
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body

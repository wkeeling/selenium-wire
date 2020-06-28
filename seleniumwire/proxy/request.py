"""Houses the classes used to transfer request and response data between components. """

from urllib.parse import parse_qs, urlsplit

from .utils import CaseInsensitiveDict


class Request:
    """Represents an HTTP request."""

    def __init__(self, *, method, path, headers, body=b''):
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
        self.headers = CaseInsensitiveDict(headers)
        self.body = body
        self.response = None

    @property
    def body(self):
        """Get the request body.

        Returns: The request body as bytes.
        """
        return self._body

    @body.setter
    def body(self, b):
        if b is None:
            self._body = b''
        elif isinstance(b, str):
            self._body = b.encode('utf-8')
        elif not isinstance(b, bytes):
            raise TypeError('body must be of type bytes')
        else:
            self._body = b

    @property
    def querystring(self):
        """Get the query string from the request.

        Returns:
            The query string.
        """
        return urlsplit(self.path).query

    @property
    def params(self):
        """Get the request parameters.

        Parameters are returned as a dictionary. Each dictionary entry will have a single
        string value, unless a parameter happens to occur more than once in the request,
        in which case the value will be a list of strings.

        Returns:
            A dictionary of request parameters.
        """
        qs = self.querystring

        if self.headers.get('Content-Type') == 'application/x-www-form-urlencoded' and self.body:
            qs = self.body.decode('utf-8', errors='replace')

        return {name: val[0] if len(val) == 1 else val
                for name, val in parse_qs(qs, keep_blank_values=True).items()}

    def to_dict(self):
        """Return a dictionary representation of the request, without the body.

        Returns: A dictionary.
        """
        d = vars(self)
        d.pop('id')
        d.pop('_body')
        d['headers'] = dict(d['headers'])

        if self.response is not None:
            d['response'] = self.response.to_dict()

        return d

    @classmethod
    def from_dict(cls, d):
        response = d.pop('response', None)
        request = cls(**d)

        if response is not None:
            request.response = Response.from_dict(response)

        return request

    def __repr__(self):
        return 'Request(method={method!r}, path={path!r}, headers={headers!r}, body={_body!r})' \
            .format(**vars(self))

    def __str__(self):
        return self.path


class Response:
    """Represents an HTTP response."""

    def __init__(self, *, status, reason, headers, body=b''):
        """Initialise a new Response object.

        Args:
            status: The status code.
            reason: The reason message (e.g. "OK" or "Not Found").
            headers: The response headers as a dictionary.
            body: The response body as bytes.
        """
        self.status = status
        self.reason = reason
        self.headers = CaseInsensitiveDict(headers)
        self.body = body

    @property
    def body(self):
        """Get the response body.

        Returns: The response body as bytes.
        """
        return self._body

    @body.setter
    def body(self, b):
        if b is None:
            self._body = b''
        elif isinstance(b, str):
            self._body = b.encode('utf-8')
        elif not isinstance(b, bytes):
            raise TypeError('body must be of type bytes')
        else:
            self._body = b

    def to_dict(self):
        """Return a dictionary representation of the response, without the body.

        Returns: A dictionary.
        """
        d = vars(self)
        d.pop('_body')
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def __repr__(self):
        return 'Response(status={status!r}, reason={reason!r}, headers={headers!r}, ' \
               'body={_body!r})'.format(**vars(self))

    def __str__(self):
        return '{} {}'.format(self.status, self.reason)

from collections import OrderedDict
from collections.abc import Mapping, MutableMapping
import time

from selenium.common.exceptions import TimeoutException


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
        return [Request(r, self._client) for r in self._client.get_requests()]

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
            return Request(data, self._client)

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
            request = self._client.find(path)

            if request is not None:
                return Request(request, self._client)
            else:
                time.sleep(0.2)

        raise TimeoutException('Timed out after {}s waiting for request {}'.format(timeout, path))

    @property
    def header_overrides(self):
        """The header overrides for outgoing browser requests.

        The value of the header overrides should be a dictionary. Where a
        header in the dictionary exists in the request, the value will be
        used in preference to the one in the request. Where a header in the
        dictionary does not exist in the request, it will be added to the
        request as a new header. To filter out a header from the request,
        set that header in the dictionary with a value of None. Header
        names are case insensitive.
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

        For example:
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
        self.headers = CaseInsensitiveDict(data['headers'])
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
        self.headers = CaseInsensitiveDict(data['headers'])

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


# This class has been taken from the requests library.
# https://github.com/requests/requests.
class CaseInsensitiveDict(MutableMapping):
    """A case-insensitive ``dict``-like object.
    Implements all methods and operations of
    ``MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.
    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::
        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True
    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    def __init__(self, data=None, **kwargs):
        self._store = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))

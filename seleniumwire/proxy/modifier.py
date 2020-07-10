import re
import threading
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from .utils import is_list_alike

# Map of default attribute names on request/response objects.
DEFAULT_ATTRS_MAP = {
    'url': 'url',
    'method': 'method',
    'headers': 'headers',
    'path': 'path',
    'body': 'body'
}


class RequestModifier:
    """This class is responsible for modifying the URL and headers
    of a request.

    Instances of this class are designed to be stateful and threadsafe.
    """

    def __init__(self):
        """Initialise a new RequestModifier."""
        self._lock = threading.Lock()
        self._headers = []
        self._params = []
        self._querystring = None
        self._rewrite_rules = []

    @property
    def headers(self):
        """The headers that should be used to override the request headers.

        The value of the headers can be a dictionary or list of sublists,
        with each sublist having two elements - a URL pattern and headers.
        Where a header in the dictionary exists in the request, the dictionary
        value will overwrite the one in the request. Where a header in the
        dictionary does not exist in the request, it will be added to the
        request as a new header. To filter out a header from the request,
        set that header in the dictionary with a value of None.
        Header names are case insensitive.

        For example:
            headers = {'User-Agent': 'Firefox'}
            headers = [
                ('.*somewhere.com.*', {'User-Agent': 'Firefox'}),
                ('*.somewhere-else.com.*', {'User-Agent': 'Chrome'}),
            ]
        """
        with self._lock:
            if is_list_alike(self._headers):
                return self._headers
            else:
                return dict(self._headers)

    @headers.setter
    def headers(self, headers):
        """Sets the headers to override request headers.

        Args:
            headers: The dictionary of headers or list of sublists,
            with each sublist having two elements - the pattern and headers
            to set.
        """
        with self._lock:
            self._headers = headers

    @headers.deleter
    def headers(self):
        """Clears the headers being used to override request headers.

        After this is called, request headers will pass through unmodified.
        """
        with self._lock:
            self._headers.clear()

    @property
    def params(self):
        """The params that should be used to override the request params.

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
            params = {'foo': 'bar'}
            params = [
                ('.*somewhere.com.*', {'foo': 'bar'}),
                ('*.somewhere-else.com.*', {'x': 'y'}),
            ]
        """
        with self._lock:
            if is_list_alike(self._params):
                return self._params
            else:
                return dict(self._params)

    @params.setter
    def params(self, params):
        """Sets the params to override request params.

        Args:
            params: The dictionary of params or list of sublists,
            with each sublist having two elements - the pattern and params
            to set.
        """
        with self._lock:
            self._params = params

    @params.deleter
    def params(self):
        """Clears the params being used to override request params.

        After this is called, request params will pass through unmodified.
        """
        with self._lock:
            self.params.clear()

    @property
    def querystring(self):
        """The querystring overrides for outgoing browser requests.

        The value of the querystring override can be a string or a list of sublists,
        with each sublist having two elements, a URL pattern and the querystring.
        The querystring override will overwrite the querystring in the request
        or will be added to the request if the request has no querystring. To
        remove a querystring from the request, set the value to None.

        For example:
            querystring = 'foo=bar&x=y'
            querystring = [
                ('.*somewhere.com.*', 'foo=bar&x=y'),
                ('*.somewhere-else.com.*', 'a=b&c=d'),
            ]
        """
        with self._lock:
            if is_list_alike(self._querystring):
                return self._querystring
            else:
                return dict(self._querystring)

    @querystring.setter
    def querystring(self, querystring):
        """Sets the querystring to override request querystring.

        Args:
            querystring: The querystring.
        """
        with self._lock:
            self._querystring = querystring

    @querystring.deleter
    def querystring(self):
        """Clears the querystring being used to override request querystring."""
        with self._lock:
            self.querystring.clear()

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
        with self._lock:
            return [(pat.pattern, repl) for pat, repl in self._rewrite_rules]

    @rewrite_rules.setter
    def rewrite_rules(self, rewrite_rules):
        """Sets the rewrite rules used to modify request URLs.

        Args:
            rewrite_rules: The list of rewrite rules, which should
                be a list of sublists, with each sublist having two
                elements - the pattern and replacement.
        """
        compiled = []
        for pattern, replacement in rewrite_rules:
            compiled.append((re.compile(pattern), replacement))

        with self._lock:
            self._rewrite_rules = compiled

    @rewrite_rules.deleter
    def rewrite_rules(self):
        """Clears the rewrite rules being used to modify request URLs.

        After this is called, request URLs will no longer be modified.
        """
        with self._lock:
            self._rewrite_rules.clear()

    def modify(self, request, *attr_names):
        """Performs modifications to the request.

        Args:
            request: The request to modify.
            attr_names: The names of request attributes being modified.
        """
        if not attr_names:
            attr_map = DEFAULT_ATTRS_MAP
        else:
            # Overwrite the defaults with what we've been passed
            attr_map = dict(DEFAULT_ATTRS_MAP).update(attr_names)

        self._modify_headers(request, attr_map)
        self._modify_params(request, attr_map)
        self._rewrite_url(request, attr_map)

    def _modify_headers(self, request, attr_map):
        request_headers = getattr(request, attr_map['headers'])
        request_url = getattr(request, attr_map['url'])

        with self._lock:
            # If self._headers is tuple or list, need to use pattern matching
            if is_list_alike(self._headers):
                headers = self._match_values(self._headers, request_url)
            else:
                headers = self._headers

            if not headers:
                return
            headers_lc = {h.lower(): (h, v) for h, v in headers.items()}

        # Remove/replace any header that already exists in the request
        for header in list(request_headers):
            try:
                value = headers_lc.pop(header.lower())[1]
            except KeyError:
                pass
            else:
                del request_headers[header]
                if value is not None:
                    request_headers[header] = value

        # Add new headers to the request that don't already exist
        for header, value in headers_lc.values():
            if value is not None:
                request_headers[header] = value

    def _modify_params(self, request, attr_map):
        request_url = getattr(request, attr_map['url'])

        with self._lock:
            # If self._params is tuple or list, need to use pattern matching
            if is_list_alike(self._params):
                params = self._match_values(self._params, request_url)
            else:
                params = self._params

            if not params:
                return

        method = getattr(request, attr_map['method'])
        headers = getattr(request, attr_map['headers'])
        query = urlsplit(request_url).query
        is_form_data = headers.get('Content-Type') == 'application/x-www-form-urlencoded'

        if method == 'POST' and is_form_data:
            query = getattr(request, attr_map['body']).decode('utf-8', errors='replace')

        if not query:
            return

        request_params = parse_qs(query, keep_blank_values=True)

        with self._lock:
            # Override the params in the request
            request_params.update(self._params)

        # Remove existing params where they have a 'None' value
        for name, value in request_params.items():
            if value is None:
                request_params.pop(name)

        query = urlencode(request_params, doseq=True)

        if method == 'POST' and is_form_data:
            query = query.encode('utf-8')
            headers['Content-Length'] = len(query)
            setattr(request, attr_map['body'], query)
        else:
            scheme, netloc, path, _, fragment = urlsplit(request_url)
            setattr(request, attr_map['url'], urlunsplit((scheme, netloc, path, query, fragment)))

    def _rewrite_url(self, request, attr_map):
        request_headers = getattr(request, attr_map['headers'])
        request_url = getattr(request, attr_map['url'])

        with self._lock:
            rewrite_rules = self._rewrite_rules[:]

        original_netloc = urlsplit(request_url).netloc

        for pattern, replacement in rewrite_rules:
            modified, count = pattern.subn(replacement, request_url)

            if count > 0:
                setattr(request, attr_map['url'], modified)
                break

        request_url = getattr(request, attr_map['url'])
        modified_netloc = urlsplit(request_url).netloc

        if original_netloc != modified_netloc:
            # Modify the Host header if it exists
            if 'Host' in request_headers:
                request_headers['Host'] = modified_netloc

    def _match_values(self, rules, url):
        results = {}
        for pattern, headers in rules:
            match = re.search(pattern, url)
            if match:
                results.update(headers)
        return results

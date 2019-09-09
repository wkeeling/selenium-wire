import re
import threading
from urllib.parse import urlsplit
from .util import is_list_alike


class RequestModifier:
    """This class is responsible for modifying the URL and headers
    of a request.

    Instances of this class are designed to be stateful and threadsafe.
    """

    def __init__(self):
        """Initialise a new RequestModifier."""
        self._lock = threading.Lock()
        self._headers = []
        self._rewrite_rules = []

    @property
    def headers(self):
        """The headers that should be used to override the request headers.

        The value of the headers could be a dictionary or list of sublists,
        with each sublist having two elements - the pattern and headers.
        Where a header in the dictionary exists in the request, the dictionary
        value will overwrite the one in the request. Where a header in the
        dictionary does not exist in the request, it will be added to the
        request as a new header. To filter out a header from the request,
        set that header in the dictionary with a value of None.
        Header names are case insensitive.

        For example:
            headers = {'User-Agent':'Firefox'}
            headers = [
                ('.*google.com.*', {'User-Agent':'Firefox'}),
                ('url2', {'User-Agent':'IE'}),
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

    def modify(self, request):
        """Performs modifications to the request.

        Args:
            request: The request (a BaseHTTPHandler instance) to modify.
        """
        self._modify_headers(request)
        self._rewrite_url(request)

    def _modify_headers(self, request):
        with self._lock:
            # If self._headers is tuple or list, need to use the pattern matching
            if is_list_alike(self._headers):
                headers = self._matched_headers(self._headers, request.path)
            else:
                headers = self._headers

            if not headers:
                return
            headers_lc = {h.lower(): (h, v) for h, v in headers.items()}

        # Remove/replace any header that already exists in the request
        for header in list(request.headers):
            try:
                value = headers_lc.pop(header.lower())[1]
            except KeyError:
                pass
            else:
                del request.headers[header]
                if value is not None:
                    request.headers[header] = value

        # Add new headers to the request that don't already exist
        for header, value in headers_lc.values():
            request.headers[header] = value

    def _rewrite_url(self, request):
        with self._lock:
            rewrite_rules = self._rewrite_rules[:]

        original_netloc = urlsplit(request.path).netloc

        for pattern, replacement in rewrite_rules:
            modified, count = pattern.subn(replacement, request.path)

            if count > 0:
                request.path = modified
                break

        modified_netloc = urlsplit(request.path).netloc

        if original_netloc != modified_netloc:
            # Modify the Host header if it exists
            if 'Host' in request.headers:
                request.headers['Host'] = modified_netloc

    def _matched_headers(self, header_rules, path):
        results = {}
        for rule in header_rules:
            pattern = rule[0]
            headers = rule[1]
            match = re.search(pattern, path)
            if match:
                results.update(headers)
        return results

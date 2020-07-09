import re
import threading
from urllib.parse import urlsplit

from .utils import is_list_alike


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

    def modify(self, request, headers_attr='headers', path_attr='path'):
        """Performs modifications to the request.

        Args:
            request: The request to modify.
            headers_attr: The name of the attribute holding the headers.
            path_attr: The name of the attribute holding the path.
        """
        self._modify_headers(request, headers_attr, path_attr)
        self._rewrite_url(request, headers_attr, path_attr)

    def _modify_headers(self, request, headers_attr, path_attr):
        request_headers = getattr(request, headers_attr)
        request_path = getattr(request, path_attr)

        with self._lock:
            # If self._headers is tuple or list, need to use the pattern matching
            if is_list_alike(self._headers):
                headers = self._matched_headers(self._headers, request_path)
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

    def _rewrite_url(self, request, headers_attr, path_attr):
        request_headers = getattr(request, headers_attr)
        request_path = getattr(request, path_attr)

        with self._lock:
            rewrite_rules = self._rewrite_rules[:]

        original_netloc = urlsplit(request_path).netloc

        for pattern, replacement in rewrite_rules:
            modified, count = pattern.subn(replacement, request_path)

            if count > 0:
                setattr(request, path_attr, modified)
                break

        request_path = getattr(request, path_attr)
        modified_netloc = urlsplit(request_path).netloc

        if original_netloc != modified_netloc:
            # Modify the Host header if it exists
            if 'Host' in request_headers:
                request_headers['Host'] = modified_netloc

    def _matched_headers(self, header_rules, path):
        results = {}
        for pattern, headers in header_rules:
            match = re.search(pattern, path)
            if match:
                results.update(headers)
        return results

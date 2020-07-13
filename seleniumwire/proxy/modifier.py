import re
import threading
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from .utils import is_list_alike


class RequestModifier:
    """This class is responsible for modifying request and response attributes.

    Instances of this class are designed to be stateful and threadsafe.
    """

    def __init__(self):
        """Initialise a new RequestModifier."""
        self._lock = threading.Lock()
        self._headers = {}
        self._params = {}
        self._querystring = None
        self._rewrite_rules = []

    @property
    def headers(self):
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

            headers = {
                'User-Agent': 'Firefox',
                'response:Cache-Control': 'none'
            }
            headers = [
                ('.*somewhere.com.*', {'User-Agent': 'Firefox', 'response:Cache-Control': 'none'}),
                ('*.somewhere-else.com.*', {'User-Agent': 'Chrome'})
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
            self._params.clear()

    @property
    def querystring(self):
        """The querystring overrides for outgoing browser requests.

        The value of the querystring override can be a string or a list of sublists,
        with each sublist having two elements, a URL pattern and the querystring.
        The querystring override will overwrite the querystring in the request
        or will be added to the request if the request has no querystring. To
        remove a querystring from the request, set the value to empty string.

        For example:
            querystring = 'foo=bar&x=y'
            querystring = [
                ('.*somewhere.com.*', 'foo=bar&x=y'),
                ('*.somewhere-else.com.*', 'a=b&c=d'),
            ]
        """
        with self._lock:
            return self._querystring

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
            self._querystring = None

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

    def modify_request(self,
                       request,
                       urlattr='url',
                       methodattr='method',
                       headersattr='headers',
                       bodyattr='body'):
        """Performs modifications to the request.

        Args:
            request: The request to modify.
            urlattr: The name of the url attribute on the request object.
            methodattr: The name of the method attribute on the request object.
            headersattr: The name of the headers attribute on the request object.
            bodyattr: The name of the body attribute on the request object.
        """
        override_headers = self._get_matching_overrides(self._headers, getattr(request, urlattr))
        if override_headers:
            self._modify_headers(getattr(request, headersattr), override_headers)
        self._modify_params(request, urlattr, methodattr, headersattr, bodyattr)
        self._modify_querystring(request, urlattr)
        self._rewrite_url(request, urlattr, headersattr)

    def modify_response(self,
                        response,
                        request,
                        urlattr='url',
                        headersattr='headers'):
        """Performs modifications to the response.

        Args:
            response: The response to modify.
            request: The original request.
            urlattr: The name of the url attribute on the response object.
            headersattr: The name of the headers attribute on the response object.
        """
        override_headers = self._get_matching_overrides(self._headers, getattr(request, urlattr))

        # We're only interested in response headers
        override_headers = {name.split(':', maxsplit=1)[1]: value
                            for name, value in (override_headers or {}).items()
                            if name.lower().startswith('response:')}

        if override_headers:
            self._modify_headers(getattr(response, headersattr), override_headers)

    def _modify_headers(self, headers, override_headers):
        headers_lc = {h.lower(): (h, v) for h, v in override_headers.items()}

        # Remove/replace any header that already exists in the request/response
        for header in list(headers):
            try:
                value = headers_lc.pop(header.lower())[1]
            except KeyError:
                pass
            else:
                del headers[header]
                if value is not None:
                    headers[header] = value

        # Add new headers to the request/response that don't already exist
        for header, value in headers_lc.values():
            if value is not None:
                headers[header] = value

    def _modify_params(self, request, urlattr, methodattr, headersattr, bodyattr):
        request_url = getattr(request, urlattr)
        params = self._get_matching_overrides(self._params, request_url)

        if not params:
            return

        method = getattr(request, methodattr)
        headers = getattr(request, headersattr)
        query = urlsplit(request_url).query
        is_form_data = headers.get('Content-Type') == 'application/x-www-form-urlencoded'

        if method == 'POST' and is_form_data:
            query = getattr(request, bodyattr).decode('utf-8', errors='replace')

        request_params = parse_qs(query, keep_blank_values=True)

        with self._lock:
            # Override the params in the request
            request_params.update(params)

        # Remove existing params where they have a 'None' value
        for name, value in list(request_params.items()):
            if value is None:
                request_params.pop(name)

        query = urlencode(request_params, doseq=True)

        # Update the request with the new params
        if method == 'POST' and is_form_data:
            query = query.encode('utf-8')
            headers['Content-Length'] = str(len(query))
            setattr(request, bodyattr, query)
        else:
            scheme, netloc, path, _, fragment = urlsplit(request_url)
            setattr(request, urlattr, urlunsplit((scheme, netloc, path, query, fragment)))

    def _modify_querystring(self, request, urlattr):
        request_url = getattr(request, urlattr)
        querystring = self._get_matching_overrides(self._querystring, request_url)

        if querystring is None:
            return

        scheme, netloc, path, _, fragment = urlsplit(request_url)
        setattr(request, urlattr, urlunsplit((scheme, netloc, path, querystring or '', fragment)))

    def _rewrite_url(self, request, urlattr, headersattr):
        request_headers = getattr(request, headersattr)
        request_url = getattr(request, urlattr)

        with self._lock:
            rewrite_rules = self._rewrite_rules[:]

        original_netloc = urlsplit(request_url).netloc

        for pattern, replacement in rewrite_rules:
            modified, count = pattern.subn(replacement, request_url)

            if count > 0:
                setattr(request, urlattr, modified)
                break

        request_url = getattr(request, urlattr)
        modified_netloc = urlsplit(request_url).netloc

        if original_netloc != modified_netloc:
            # Modify the Host header if it exists
            if 'Host' in request_headers:
                request_headers['Host'] = modified_netloc

    def _get_matching_overrides(self, overrides, url):
        with self._lock:
            # If the overrides is tuple or list, we need to match against the URL
            if is_list_alike(overrides):
                for pat, ov in overrides:
                    match = re.search(pat, url)
                    if match:
                        return ov
            else:
                return overrides

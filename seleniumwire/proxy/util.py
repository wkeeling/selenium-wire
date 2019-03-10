import base64
import http.client
import logging
import os
import pkgutil
import re
import threading
from urllib.parse import urlsplit

log = logging.getLogger(__name__)


class ProxyAuthorization:

    @property
    def authorization_headers(self):
        headers = {}
        if self.proxy_username and self.proxy_password:
            auth = '%s:%s' % (self.proxy_username, self.proxy_password)
            headers['Proxy-Authorization'] = 'Basic ' + base64.b64encode(auth.encode('latin-1')).decode(
                'latin-1')
        return headers


class ProxyAwareHTTPConnection(ProxyAuthorization, http.client.HTTPConnection):

    def __init__(self, proxy_config, netloc, *args, **kwargs):
        self.proxy_type, self.proxy_username, self.proxy_password, self.proxy_host = proxy_config.get('http')
        self.proxied = proxy_config and netloc not in proxy_config['no_proxy']
        self.netloc = netloc

        if self.proxied:
            super().__init__(self.proxy_host, *args, **kwargs)
        else:
            super().__init__(netloc, *args, **kwargs)

    def request(self, method, url, body=None, headers={}, *, encode_chunked=False):
        if self.proxied:
            if not url.startswith('http'):
                url = 'http://{}{}'.format(self.netloc, url)
            headers.update(self.authorization_headers)

        super().request(method, url, body, headers, encode_chunked=encode_chunked)


class ProxyAwareHTTPSConnection(ProxyAuthorization, http.client.HTTPSConnection):

    def __init__(self, proxy_config, netloc, *args, **kwargs):
        self.proxy_type, self.proxy_username, self.proxy_password, self.proxy_host = proxy_config.get('https')

        if proxy_config and netloc not in proxy_config['no_proxy']:
            super().__init__(self.proxy_host, *args, **kwargs)
            self.set_tunnel(netloc, headers=self.authorization_headers)
        else:
            super().__init__(netloc, *args, **kwargs)


class RequestModifier:
    """Helper class responsible for making modifications to requests
    as they pass through the proxy.

    Instances of this class are designed to be stateful and threadsafe.
    """
    def __init__(self):
        """Initialise a new RequestModifier."""
        self._lock = threading.Lock()
        self._headers = {}
        self._rewrite_rules = []

    @property
    def headers(self):
        """The headers that should be used to override the request headers.

        The value of the headers should be a dictionary. Where a header in
        the dictionary exists in the request, the dictionary value will
        overwrite the one in the request. Where a header in the dictionary
        does not exist in the request, it will be added to the request as a
        new header. To filter out a header from the request, set that header
        in the dictionary with a value of None. Header names are case insensitive.
        """
        with self._lock:
            return dict(self._headers)

    @headers.setter
    def headers(self, headers):
        """Sets the headers to override request headers.

        Args:
            headers: The dictionary of headers to set.
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
            headers_lc = {h.lower(): (h, v) for h, v in self._headers.items()}

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


def extract_cert():
    """Extracts the root certificate to the current working directory."""
    cert_name = 'ca.crt'
    cert = pkgutil.get_data(__package__, cert_name)

    with open(os.path.join(os.getcwd(), cert_name), 'wb') as out:
        out.write(cert)

    log.info('{} extracted. You can now import this into a browser.'.format(cert_name))

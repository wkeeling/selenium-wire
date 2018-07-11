import os
import pkgutil
import threading


class RequestModifier:
    """Helper class responsible for making modifications to requests
    as they pass through the proxy.

    Instances of this class are designed to be stateful and threadsafe.
    """
    def __init__(self):
        """Initialise a new RequestModifier."""
        self._lock = threading.Lock()
        self._headers = {}

    @property
    def headers(self):
        """The headers that should be used to override the request headers.

        The value of the headers should be a dictionary. Where a header in
        the dictionary exists in the request, the dictionary value will be
        used in preference to the one in the request. Where a header in the
        dictionary does not exist in the request, it will be added to the
        request as a new header. To filter out a header from the request,
        set that header in the dictionary with a value of None. Header
        names are case insensitive.
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

    def modify(self, request):
        """Performs modifications to the request.

        Args:
            request: The request (a BaseHTTPHandler instance) to modify.
        """
        with self._lock:
            headers_lc = {h.lower(): v for h, v in self._headers.items()}

        for header in list(request.headers):
            try:
                value = headers_lc[header.lower()]
            except KeyError:
                pass
            else:
                del request.headers[header]
                if value is not None:
                    request.headers[header] = value


def extract_cert():
    """Extracts the root certificate to the current working directory."""
    cert_name = 'ca.crt'
    cert = pkgutil.get_data(__package__, cert_name)

    with open(os.path.join(os.getcwd(), cert_name), 'wb') as out:
        out.write(cert)

    print('{} extracted. You can now import this into a browser.'.format(cert_name))

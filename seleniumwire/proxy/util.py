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

    def set_headers(self, headers):
        """Sets the headers that should be used to override the request headers.

        Where a header in the supplied dictionary exists in the request, the
        value will be used in preference to the one in the request. Where a
        header in the supplied dictionary does not exist in the request, it
        will be added to the request as a new header. To filter out a header
        from the request, set that header in the headers dictionary with a
        value of None. Header names are case insensitive.

        Args:
            headers: A dictionary of headers to override the request headers with.
        """
        with self._lock:
            self._headers = headers

    def clear_headers(self):
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

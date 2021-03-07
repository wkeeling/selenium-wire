import gzip
import logging
import os
import pickle
import re
import shutil
import threading
import uuid
import zlib
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO

log = logging.getLogger(__name__)

# Storage folders older than this are cleaned up.
REMOVE_DATA_OLDER_THAN_DAYS = 1


class RequestStorage:
    """Responsible for saving request and response data that passes through the proxy server.

    Requests and responses are saved separately. However, when a request is loaded, the
    response, if there is one, is automatically loaded and attached to the request. As are
    any websocket messages.

    This implementation writes the request and response data to disk, but keeps an in-memory
    index for sequencing and fast retrieval.

    Instances are designed to be threadsafe.
    """

    def __init__(self, base_dir=None):
        """Initialises a new RequestStorage using an optional base directory.

        Args:
            base_dir: The directory where request and response data is stored.
                If not specified, the current user's home folder is used.
        """
        if base_dir is None:
            base_dir = os.path.expanduser('~')

        self.home_dir = os.path.join(base_dir, '.seleniumwire')
        self.session_dir = os.path.join(self.home_dir, 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self.session_dir, exist_ok=True)
        self._cleanup_old_dirs()

        # Index of requests received.
        # A list of tuples: [(request id, request path, response received), ...]
        self._index = []

        # Sequences of websocket messages held against the
        # id of the originating websocket request.
        self._ws_messages = defaultdict(list)

        self._lock = threading.Lock()

    def save_request(self, request):
        """Save a request to storage.

        Args:
            request: The request to save.
        """
        request_id = self._index_request(request)
        request.id = request_id
        request_dir = self._get_request_dir(request_id)
        os.mkdir(request_dir)

        self._save(request, request_dir, 'request')

    def _index_request(self, request):
        request_id = str(uuid.uuid4())

        with self._lock:
            self._index.append(_IndexedRequest(
                id=request_id,
                url=request.url,
                has_response=False)
            )

        return request_id

    def _save(self, obj, dirname, filename):
        with open(os.path.join(dirname, filename), 'wb') as out:
            pickle.dump(obj, out)

    def save_response(self, request_id, response):
        """Save a response to storage against a request with the specified id.

        Args:
            request_id: The id of the original request.
            response: The response to save.
        """
        indexed_request = self._get_indexed_request(request_id)

        if indexed_request is None:
            log.debug('Cannot save response as request %s is no longer stored' % request_id)
            return

        request_dir = self._get_request_dir(request_id)

        self._save(response, request_dir, 'response')

        indexed_request.has_response = True

    def _get_indexed_request(self, request_id):
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            if indexed_request.id == request_id:
                return indexed_request

        return None

    def save_ws_message(self, request_id, message):
        """Save a websocket message against a request with the specified id.

        Args:
            request_id: The id of the original handshake request.
            message: The websocket message to save.
        """
        with self._lock:
            self._ws_messages[request_id].append(message)

    def save_har_entry(self, request_id, entry):
        """Save a HAR entry to storage against a request with the specified id.

        Args:
            request_id: The id of the original request.
            entry: The HAR entry to save.
        """
        indexed_request = self._get_indexed_request(request_id)

        if indexed_request is None:
            log.debug('Cannot save HAR entry as request %s is no longer stored' % request_id)
            return

        request_dir = self._get_request_dir(request_id)

        self._save(entry, request_dir, 'har_entry')

    def load_requests(self):
        """Load all previously saved requests known to the storage (known to its index).

        The requests are returned as a list of request objects in the order in which they
        were saved. Each request will have any associated response and websocket messages
        attached - assuming they exist.

        Returns: A list of request objects.
        """
        with self._lock:
            index = self._index[:]

        loaded = []

        for indexed_request in index:
            request = self._load_request(indexed_request.id)
            loaded.append(request)

        return loaded

    def _load_request(self, request_id):
        request_dir = self._get_request_dir(request_id)

        with open(os.path.join(request_dir, 'request'), 'rb') as req:
            request = pickle.load(req)

            ws_messages = self._ws_messages.get(request.id)

            if ws_messages:
                # Attach any websocket messages for this request if we have them
                request.ws_messages = ws_messages

            try:
                # Attach the response if there is one.
                with open(os.path.join(request_dir, 'response'), 'rb') as res:
                    response = pickle.load(res)
                    response.body = self._decode(
                        response.body, response.headers.get('Content-Encoding', 'identity')
                    )
                    request.response = response

                    # The certificate data has been stored on the response but we make
                    # it available on the request which is a more logical location.
                    if hasattr(response, 'cert'):
                        request.cert = response.cert
                        del response.cert
            except (FileNotFoundError, EOFError):
                pass

        return request

    def _decode(self, data, encoding):
        if encoding != 'identity':
            try:
                if encoding in ('gzip', 'x-gzip'):
                    io = BytesIO(data)
                    with gzip.GzipFile(fileobj=io) as f:
                        data = f.read()
                elif encoding == 'deflate':
                    try:
                        data = zlib.decompress(data)
                    except zlib.error:
                        data = zlib.decompress(data, -zlib.MAX_WBITS)
                else:
                    log.debug("Unknown Content-Encoding: %s", encoding)
            except (OSError, EOFError, zlib.error) as e:
                # Log a message and return the data untouched
                log.debug('Unable to decode body: %s', str(e))
        return data

    def load_last_request(self):
        """Load the last saved request.

        Returns: The last saved request or None if no requests have
            yet been stored.
        """
        with self._lock:
            if self._index:
                last_request = self._index[-1]
            else:
                return None

        return self._load_request(last_request.id)

    def load_har_entries(self):
        """Load all HAR entries known to this storage.

        Returns: A list of HAR entries.
        """
        with self._lock:
            index = self._index[:]

        entries = []

        for indexed_request in index:
            request_dir = self._get_request_dir(indexed_request.id)

            try:
                with open(os.path.join(request_dir, 'har_entry'), 'rb') as f:
                    entry = pickle.load(f)
                    entries.append(entry)
            except FileNotFoundError:
                # HAR entries aren't necessarily saved with each request.
                pass

        return entries

    def iter_requests(self):
        """Return an iterator of requests known to the storage.

        Returns: An iterator of request objects.
        """
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            yield self._load_request(indexed_request.id)

    def clear_requests(self):
        """Clears all requests currently known to this storage."""
        with self._lock:
            index = self._index[:]
            self._index.clear()
            self._ws_messages.clear()

        for indexed_request in index:
            shutil.rmtree(self._get_request_dir(indexed_request.id), ignore_errors=True)

    def find(self, pat, check_response=True):
        """Find the first request that matches the specified pattern.

        Requests are searched in chronological order.

        Args:
            pat: A pattern that will be searched in the request URL.
            check_response: When a match is found, whether to check that the request has
                a corresponding response. Where check_response=True and no response has
                been received, this method will skip the request and continue searching.

        Returns: The first request in the storage that matches the pattern,
            or None if no requests match.
        """
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            if re.search(pat, indexed_request.url):
                if (check_response and indexed_request.has_response) or not check_response:
                    return self._load_request(indexed_request.id)

        return None

    def _get_request_dir(self, request_id):
        return os.path.join(self.session_dir, 'request-{}'.format(request_id))

    def cleanup(self):
        """Remove all stored requests, the storage directory containing those
        requests, and if that is the only storage directory, also the top level
        parent directory.
        """
        log.debug('Cleaning up %s', self.session_dir)
        self.clear_requests()
        shutil.rmtree(self.session_dir, ignore_errors=True)
        try:
            # Attempt to remove the parent folder if it is empty
            os.rmdir(os.path.dirname(self.session_dir))
        except OSError:
            # Parent folder not empty
            pass

    def _cleanup_old_dirs(self):
        """Clean up and remove any old storage directories that were not previously
        cleaned up properly by cleanup().
        """
        parent_dir = os.path.dirname(self.session_dir)
        for storage_dir in os.listdir(parent_dir):
            storage_dir = os.path.join(parent_dir, storage_dir)
            try:
                if (os.path.getmtime(storage_dir) <
                        (datetime.now() - timedelta(days=REMOVE_DATA_OLDER_THAN_DAYS)).timestamp()):
                    shutil.rmtree(storage_dir, ignore_errors=True)
            except FileNotFoundError:
                # Can happen if multiple instances are run concurrently
                pass


class _IndexedRequest(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

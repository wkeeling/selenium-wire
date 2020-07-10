import gzip
import logging
import os
import pickle
import shutil
import threading
import uuid
import zlib
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Storage folders older than this are cleaned up.
REMOVE_DATA_OLDER_THAN_DAYS = 1


class RequestStorage:
    """Responsible for saving request and response data that passes through the proxy server,
    and provding an API to retrieve that data.

    Requests and responses are saved separately. However, when a request is loaded, the
    response, if there is one, is automatically loaded and attached to the request. Furthermore,
    when saving both requests and responses, the body is split out and saved separately.
    Request/response bodies are not loaded automatically and must be retrieved via a separate
    method call.

    This implementation writes the request and response data to disk, but keeps an in-memory
    index of what is on disk for fast retrieval. Instances are designed to be threadsafe.
    """

    def __init__(self, base_dir=None):
        """Initialises a new RequestStorage using an optional base directory.

        Args:
            base_dir: The directory where request and response data is stored.
                If not specified, the current user's home folder is used.
        """
        if base_dir is None:
            base_dir = os.path.expanduser('~')

        self._storage_dir = os.path.join(base_dir, '.seleniumwire', 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self._storage_dir)
        self._cleanup_old_dirs()

        # Index of requests received.
        # A list of tuples: [(request id, request path, response received), ...]
        self._index = []
        self._lock = threading.Lock()

    def save_request(self, request):
        """Saves the request to storage.

        Args:
            request: The request to save.
        """
        request_id = self._index_request(request)
        request.id = request_id
        request_dir = self._get_request_dir(request_id)
        os.mkdir(request_dir)

        body = request.body
        request.body = b''  # The request body is stored separately to the request itself

        self._save(request, request_dir, 'request')

        if body:
            self._save(body, request_dir, 'requestbody')

    def _index_request(self, request):
        request_id = str(uuid.uuid4())

        with self._lock:
            self._index.append(_IndexedRequest(id=request_id,
                                               url=request.url,
                                               has_response=False))

        return request_id

    def _save(self, obj, dirname, filename):
        request_dir = os.path.join(self._storage_dir, dirname)

        with open(os.path.join(request_dir, filename), 'wb') as out:
            pickle.dump(obj, out)

    def save_response(self, request_id, response):
        """Saves the response to storage.

        Args:
            request_id: The id of the original request.
            response: The response to save.
        """
        indexed_request = self._get_indexed_request(request_id)

        if indexed_request is None:
            # Request has been cleared from storage before
            # the response arrived back
            log.debug('Cannot save response as request {} is no longer stored'.format(request_id))
            return

        request_dir = self._get_request_dir(request_id)

        body = response.body
        response.body = b''  # The response body is stored separately to the response itself

        self._save(response, request_dir, 'response')

        if body:
            self._save(body, request_dir, 'responsebody')

        indexed_request.has_response = True

    def _get_indexed_request(self, request_id):
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            if indexed_request.id == request_id:
                return indexed_request

        return None

    def load_requests(self):
        """Loads all previously saved requests known to the storage (known to its index).

        The requests are returned as a list of request objects.

        Where a request does not have a corresponding response its 'response' attribute
        will be None.

        Returns:
            A list of request objects.
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

            try:
                with open(os.path.join(request_dir, 'response'), 'rb') as res:
                    response = pickle.load(res)
                    request.response = response
            except (FileNotFoundError, EOFError):
                pass

        return request

    def load_request_body(self, request_id):
        """Loads the body of the request with the specified id.

        Args:
            request_id: The id of the request.
        Returns:
            The binary data request body.
        """
        try:
            return self._load_body(request_id, 'requestbody')
        except FileNotFoundError:
            return b''

    def load_response_body(self, request_id):
        """Loads the body of the response corresponding to the request with the specified id.

        Args:
            request_id: The id of the request.
        Returns:
            The binary data response body.
        """
        try:
            raw_body = self._load_body(request_id, 'responsebody')
            request = self._load_request(request_id)
            return self._decode_body(raw_body, request.response.headers.get('Content-Encoding', 'identity'))
        except FileNotFoundError:
            return b''

    def _load_body(self, request_id, name):
        request_dir = self._get_request_dir(request_id)
        with open(os.path.join(request_dir, name), 'rb') as body:
            return pickle.load(body)

    def _decode_body(self, data, encoding):
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
        """Loads the last saved request.

        Returns:
            The last saved request dictionary or None if no requests
            have yet been stored.
        """
        with self._lock:
            if self._index:
                last_request = self._index[-1]
            else:
                return None

        return self._load_request(last_request.id)

    def clear_requests(self):
        """Clears all requests currently known to this storage."""
        with self._lock:
            index = self._index[:]
            self._index.clear()

        for indexed_request in index:
            shutil.rmtree(self._get_request_dir(indexed_request.id), ignore_errors=True)

    def find(self, path, check_response=True):
        """Find the first request that contains the specified path.

        Requests are searched in chronological order.

        Args:
            path: The request path which can be any part of the request URL.
            check_response: Where a path matches a request, whether to check
                that the request has a corresponding response. Where
                check_response=True and no response has been received, this
                method will skip the request and continue searching.

        Returns:
            The first request in the storage that matches the path, or None
            if no requests match.
        """
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            match_url = urlparse(path).geturl()

            if match_url in indexed_request.path:
                if (check_response and indexed_request.has_response) or not check_response:
                    return self._load_request(indexed_request.id)

        return None

    def get_cert_dir(self):
        """Returns a storage-specific path to a directory where the SSL certificates are stored.

        The directory does not have to exist.

        Returns:
            The path to the certificates directory in this storage.
        """
        return os.path.join(self._storage_dir, 'certs')

    def _get_request_dir(self, request_id):
        return os.path.join(self._storage_dir, 'request-{}'.format(request_id))

    def cleanup(self):
        """Removes all stored requests, the storage directory containing those
        requests, and if that is the only storage directory, also removes the
        top level parent directory.
        """
        log.debug('Cleaning up %s', self._storage_dir)
        self.clear_requests()
        shutil.rmtree(self._storage_dir, ignore_errors=True)
        try:
            # Attempt to remove the parent folder if it is empty
            os.rmdir(os.path.dirname(self._storage_dir))
        except OSError:
            # Parent folder not empty
            pass

    def _cleanup_old_dirs(self):
        """Cleans up and removes any old storage directories that were not previously
        cleaned up properly by _cleanup().
        """
        parent_dir = os.path.dirname(self._storage_dir)
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

import gzip
import logging
import os
import pickle
import re
import shutil
import threading
import uuid
import zlib
from datetime import datetime, timedelta
from io import BytesIO

log = logging.getLogger(__name__)

# Storage folders older than this are cleaned up.
REMOVE_DATA_OLDER_THAN_DAYS = 1


class RequestStorage:
    """Responsible for saving request and response data that passes through the proxy server,
    and provding an API to retrieve that data.

    Requests and responses are saved separately. However, when a request is loaded, the
    response, if there is one, is automatically loaded and attached to the request.

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

        self.storage_home = os.path.join(base_dir, '.seleniumwire')
        self.storage_session = os.path.join(self.storage_home, 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self.storage_session, exist_ok=True)
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
        request_dir = os.path.join(self.storage_session, dirname)

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

        self._save(response, request_dir, 'response')

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
                    response.body = self._decode(response.body, response.headers.get('Content-Encoding', 'identity'))
                    request.response = response
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
        """Find the first request that matches the specified path.

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
            if re.search(path, indexed_request.url):
                if (check_response and indexed_request.has_response) or not check_response:
                    return self._load_request(indexed_request.id)

        return None

    def _get_request_dir(self, request_id):
        return os.path.join(self.storage_session, 'request-{}'.format(request_id))

    def cleanup(self):
        """Removes all stored requests, the storage directory containing those
        requests, and if that is the only storage directory, also removes the
        top level parent directory.
        """
        log.debug('Cleaning up %s', self.storage_session)
        self.clear_requests()
        shutil.rmtree(self.storage_session, ignore_errors=True)
        try:
            # Attempt to remove the parent folder if it is empty
            os.rmdir(os.path.dirname(self.storage_session))
        except OSError:
            # Parent folder not empty
            pass

    def _cleanup_old_dirs(self):
        """Cleans up and removes any old storage directories that were not previously
        cleaned up properly by _cleanup().
        """
        parent_dir = os.path.dirname(self.storage_session)
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

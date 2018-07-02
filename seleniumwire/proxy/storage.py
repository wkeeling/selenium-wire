import atexit
from datetime import datetime, timedelta
import logging
import os
import pickle
import shutil
import signal
import tempfile
import threading
import uuid

log = logging.getLogger(__name__)

# Storage folders older than this are cleaned up.
REMOVE_DATA_OLDER_THAN_DAYS = 1


class RequestStorage:
    """Responsible for saving request and response data that passes through the proxy server,
    and provding an API to retrieve that data.

    This implementation writes the request and response data to disk, but keeps an in-memory
    index of what is on disk for fast retrieval.
    """

    def __init__(self, base_dir=None):
        """Initialises a new RequestStorage using an optional base directory.

        The base directory is where request and response data is stored. If
        not specified, the system's temp folder is used.
        """
        if base_dir is None:
            base_dir = tempfile.gettempdir()

        self._storage_dir = os.path.join(base_dir, 'seleniumwire', 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self._storage_dir)
        self._cleanup_old_dirs()

        self._index = []  # Index of requests received
        self._lock = threading.Lock()

        # Register shutdown hooks for cleaning up stored requests
        atexit.register(self._cleanup)
        signal.signal(signal.SIGTERM, self._cleanup)
        signal.signal(signal.SIGINT, self._cleanup)

    def save_request(self, request, request_body=None):
        """Saves the request (a BaseHTTPRequestHandler instance) to storage, and optionally
        saves the request body data if supplied.

        Args:
            request: The BaseHTTPRequestHandler instance to save.
            request_body: The request body data.
        """
        request_id = self._index_request(request)
        request_dir = self._get_request_dir(request_id)
        os.mkdir(request_dir)

        request_data = {
            'id': request_id,
            'method': request.command,
            'path': request.path,
            'headers': dict(request.headers),
            'response': None
        }

        self._save(request_data, request_dir, 'request')
        if request_body is not None:
            self._save(request_body, request_dir, 'requestbody')

        return request_id

    def _index_request(self, request):
        request_id = str(uuid.uuid4())
        request.id = request_id

        with self._lock:
            self._index.append(request_id)

        return request_id

    def _save(self, obj, dirname, filename):
        request_dir = os.path.join(self._storage_dir, dirname)

        with open(os.path.join(request_dir, filename), 'wb') as out:
            pickle.dump(obj, out)

    def save_response(self, request_id, response, response_body=None):
        """Saves the response (a http.client.HTTPResponse instance) to storage, and optionally
        saves the request body data if supplied.

        Args:
            request_id: The id of the original request.
            response: The http.client.HTTPResponse instance to save.
            response_body: The request body data.

        """
        response_data = {
            'status_code': response.status,
            'reason': response.reason,
            'headers': dict(response.headers)
        }

        request_dir = self._get_request_dir(request_id)
        self._save(response_data, request_dir, 'response')
        if response_body is not None:
            self._save(response_body, request_dir, 'responsebody')

    def load_requests(self):
        """Load all previously saved requests known to the storage (known to its index).

        The requests are returned as a list of dictionaries, in the format:

        [{
            'id': 'request id',
            'method': 'GET',
            'path': 'http://www.example.com/some/path',
            'headers': {
                'Accept': '*/*',
                'Host': 'www.example.com'
            }
            'response': {
                'status_code': 200,
                'reason': 'OK',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Content-Length': '15012'
                }
            }
        }, ...]

        Where a request does not have a corresponding response, a 'response' key will
        still exist in the dictionary, but its value will be None.

        Returns:
            A list of dictionaries of previously saved requests.
        """
        with self._lock:
            index = self._index[:]

        loaded = []

        for request_id in index:
            request = self._load_request(request_id)
            loaded.append(request)

        return loaded

    def _load_request(self, request_id):
        request_dir = self._get_request_dir(request_id)

        with open(os.path.join(request_dir, 'request'), 'rb') as req:
            request = pickle.load(req)

            if os.path.exists(os.path.join(request_dir, 'response')):
                with open(os.path.join(request_dir, 'response'), 'rb') as res:
                    response = pickle.load(res)
                    request['response'] = response

        return request

    def load_request_body(self, request_id):
        """Load the body of the request with the specified id.

        Args:
            request_id: The id of the request.
        Returns:
            The binary data request body.
        """
        return self._load_body(request_id, 'requestbody')

    def load_response_body(self, request_id):
        """Load the body of the response corresponding to the request with the specified id.

        Args:
            request_id: The id of the request.
        Returns:
            The binary data response body.
        """
        return self._load_body(request_id, 'responsebody')

    def _load_body(self, request_id, name):
        request_dir = self._get_request_dir(request_id)
        with open(os.path.join(request_dir, name), 'rb') as body:
            return pickle.load(body)

    def load_last_request(self):
        """Load the last saved request.

        Returns:
            The last saved request dictionary (see load_requests() for dict structure).
        """
        with self._lock:
            request_id = self._index[-1]
        return self._load_request(request_id)

    def clear_requests(self):
        """Clear all requests currently known to this storage.

        This clears the index but does not remove the request data from disk. That
        is left to the cleanup actions.
        """
        with self._lock:
            self._index.clear()

    def _get_request_dir(self, request_id):
        return os.path.join(self._storage_dir, 'request-{}'.format(request_id))

    def _cleanup(self):
        """Cleans up and removes all saved requests associated with this storage."""
        log.debug('Cleaning up %s', self._storage_dir)
        shutil.rmtree(self._storage_dir, ignore_errors=True)
        try:
            # Attempt to remove the parent folder if it is empty
            os.rmdir(os.path.dirname(self._storage_dir))
        except OSError:
            # Parent folder not empty
            pass

    def _cleanup_old_dirs(self):
        """Cleans up and removes any old storage folders that were not previously
        cleaned up properly by _cleanup().
        """
        parent_dir = os.path.dirname(self._storage_dir)
        for storage_dir in os.listdir(parent_dir):
            storage_dir = os.path.join(parent_dir, storage_dir)
            if (os.path.getmtime(storage_dir) <
                    (datetime.now() - timedelta(days=REMOVE_DATA_OLDER_THAN_DAYS)).timestamp()):
                shutil.rmtree(storage_dir, ignore_errors=True)

import atexit
import logging
import os
import pickle
import shutil
import signal
import tempfile
import threading
import uuid

log = logging.getLogger(__name__)


class RequestStorage:

    def __init__(self):
        self._storage_dir = os.path.join(tempfile.gettempdir(), 'seleniumwire', 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self._storage_dir)

        self._index = []  # Index of requests received
        self._lock = threading.Lock()

        # Register shutdown hooks for cleaning up stored requests
        atexit.register(self._cleanup)
        signal.signal(signal.SIGTERM, self._cleanup)
        signal.signal(signal.SIGINT, self._cleanup)

    def save_request(self, request, request_body):
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

    def _index_request(self, request):
        request_id = str(uuid.uuid4())
        request.id = request_id

        with self._lock:
            self._index.append((request.path, request_id))

        return request_id

    def _save(self, obj, dirname, filename):
        request_dir = os.path.join(self._storage_dir, dirname)

        with open(os.path.join(request_dir, filename), 'wb') as out:
            pickle.dump(obj, out)

    def save_response(self, response, response_body, request_id):
        response_data = {
            'status_code': response.status,
            'reason': response.reason,
            'headers': response.headers
        }

        request_dir = self._get_request_dir(request_id)
        self._save(response_data, request_dir, 'response')
        self._save(response_body, request_dir, 'responsebody')

    def load_captured_requests(self):
        with self._lock:
            index = self._index[:]

        loaded = []
        for _, guid in index:
            request_dir = self._get_request_dir(guid)
            with open(os.path.join(request_dir, 'request'), 'rb') as req:
                request = pickle.load(req)
                if os.path.exists('response'):
                    with open(os.path.join(request_dir, 'response'), 'rb') as res:
                        response = pickle.load(res)
                        request['response'] = response

            loaded.append(request)

        return loaded

    def _get_request_dir(self, request_id):
        return os.path.join(self._storage_dir, 'request-{}'.format(request_id))

    def _cleanup(self):
        """Clean up and remove all saved requests associated with this storage."""
        log.debug('Cleaning up {}'.format(self._storage_dir))
        shutil.rmtree(self._storage_dir, ignore_errors=True)


storage = RequestStorage()

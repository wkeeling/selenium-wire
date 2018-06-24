import uuid
import logging
import os
import pickle
import shutil
import tempfile
import threading

log = logging.getLogger(__name__)


class RequestStorage:

    _storage_dir = os.path.join(tempfile.gettempdir(), 'seleniumwire')

    _index = []  # Index of requests received
    _lock = threading.Lock()

    def __init__(self):
        # This should remove subfolders older than e.g. 2 hours? Not the whole parent...
        shutil.rmtree(self._storage_dir, ignore_errors=True)
        os.mkdir(self._storage_dir)

    def save_request(self, request, request_body):
        request_id = self._index_request(request)

        request_data = {
            'id': request_id,
            'method': request.command,
            'path': request.path,
            'headers': request.headers,
            'response': None
        }

        self._save(request_data, request.id, 'request')
        if request_body is not None:
            self._save(request_body, request.id, 'requestbody')

    def _index_request(self, request):
        request_id = str(uuid.uuid4())
        request.id = request_id

        with self._lock:
            self._index.append((request.path, request_id))

        return request_id

    def save_response(self, response, response_body, request_id):
        response_data = {
            'status_code': response.status,
            'reason': response.reason,
            'headers': response.headers
        }

        self._save(response_data, request_id, 'response')
        self._save(response_body, request_id, 'responsebody')

    def _save(self, obj, dirname, filename):
        request_dir = os.path.join(self._storage_dir, dirname)
        os.mkdir(os.path.join(self._storage_dir, dirname))

        with open(os.path.join(request_dir, filename), 'wb') as out:
            pickle.dump(obj, out)

    def load_captured_requests(self):
        with self._lock:
            index = self._index[:]

        loaded = []
        for _, guid in index:
            with open(os.path.join(self._storage_dir, guid, 'request')) as req:
                request = pickle.load(req)
                if os.path.exists('response'):
                    with open(os.path.join(self._storage_dir, guid, 'response')) as res:
                        response = pickle.load(res)
                        request['response'] = response

            loaded.append(request)

        return loaded


storage = RequestStorage()

import logging
import os
import pickle
import shutil
import tempfile

log = logging.getLogger(__name__)


class RequestStorage:

    storage_dir = os.path.join(tempfile.gettempdir(), 'seleniumwire')

    def __init__(self):
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        os.mkdir(self.storage_dir)

    def save_request(self, request, request_body):
        request_data = {
            'id': request.id,
            'method': request.command,
            'path': request.path,
            'headers': request.headers,
        }

        self._save(request_data, request.id, 'request')
        if request_body is not None:
            self._save(request_body, request.id, 'requestbody')

    def save_response(self, response, response_body, request_id):
        response_data = {
            'status_code': response.status,
            'reason': response.reason,
            'headers': response.headers
        }

        self._save(response_data, request_id, 'response')
        self._save(response_body, request_id, 'responsebody')

    def _save(self, obj, dirname, filename):
        request_dir = os.path.join(self.storage_dir, dirname)

        if not os.path.exists(request_dir):
            try:
                os.mkdir(request_dir)
            except FileExistsError:
                pass

        with open(os.path.join(request_dir, filename), 'wb') as out:
            pickle.dump(obj, out)



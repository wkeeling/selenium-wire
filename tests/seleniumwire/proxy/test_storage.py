import glob
import gzip
import os
import pickle
import shutil
from datetime import datetime, timedelta
from fnmatch import fnmatch
from io import BytesIO
from unittest import TestCase

from seleniumwire.proxy.request import Request, Response
from seleniumwire.proxy.storage import RequestStorage


class RequestStorageTest(TestCase):

    def test_initialise(self):
        RequestStorage(base_dir=self.base_dir)
        storage_dir = glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*'))

        self.assertEqual(1, len(storage_dir))

    def test_cleanup_removes_storage(self):
        storage = RequestStorage(base_dir=self.base_dir)
        storage.cleanup()

        # The 'seleniumwire' parent folder should have been cleaned up
        # when there is nothing left inside of it.
        self.assertFalse(os.listdir(self.base_dir))

    def test_cleanup_does_not_remove_parent_folder(self):
        # There is an existing storage folder
        os.makedirs(os.path.join(self.base_dir, '.seleniumwire', 'teststorage'))
        storage = RequestStorage(base_dir=self.base_dir)
        storage.cleanup()

        # The existing storage folder is not cleaned up
        self.assertEqual(1, len(os.listdir(self.base_dir)))
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, '.seleniumwire', 'teststorage')))

    def test_initialise_clears_old_folders(self):
        old_dir = os.path.join(self.base_dir, '.seleniumwire', 'storage-test1')
        new_dir = os.path.join(self.base_dir, '.seleniumwire', 'storage-test2')
        os.makedirs(old_dir)
        os.makedirs(new_dir)
        two_days_ago = (datetime.now() - timedelta(days=2)).timestamp()
        os.utime(old_dir, times=(two_days_ago, two_days_ago))

        RequestStorage(base_dir=self.base_dir)

        self.assertFalse(os.path.exists(old_dir))
        self.assertTrue(os.path.exists(new_dir))

    def test_save_request(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)

        storage.save_request(request)

        request_file_path = self._get_stored_path(request.id, 'request')

        with open(request_file_path[0], 'rb') as loaded:
            loaded_request = pickle.load(loaded)

        self.assertEqual(request.id, loaded_request.id)
        self.assertEqual('http://www.example.com/test/path/', loaded_request.path)
        self.assertEqual('GET', loaded_request.method)
        self.assertEqual({
            'Host': 'www.example.com',
            'Accept': '*/*'
        }, loaded_request.headers)
        self.assertIsNone(loaded_request.response)

    def test_save_request_with_body(self):
        body = b'test request body'
        request = self._create_request(body=body)
        storage = RequestStorage(base_dir=self.base_dir)

        storage.save_request(request)

        request_body_path = self._get_stored_path(request.id, 'requestbody')

        with open(request_body_path[0], 'rb') as loaded:
            loaded_body = pickle.load(loaded)

        self.assertEqual(body, loaded_body)

    def test_save_response(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response()

        storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        with open(response_file_path[0], 'rb') as loaded:
            loaded_response = pickle.load(loaded)

        self.assertEqual(200, loaded_response.status_code)
        self.assertEqual('OK', loaded_response.reason)
        self.assertEqual({
            'Content-Type': 'application/json',
            'Content-Length': 500
        }, loaded_response.headers)

    def test_save_response_with_body(self):
        body = b'some response body'
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response(body=body)

        storage.save_response(request.id, response)

        response_body_path = self._get_stored_path(request.id, 'responsebody')

        with open(response_body_path[0], 'rb') as loaded:
            loaded_body = pickle.load(loaded)

        self.assertEqual(b'some response body', loaded_body)

    def test_save_response_no_request(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response()
        storage.clear_requests()

        storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        self.assertFalse(response_file_path)

    def test_load_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_request(request_2)

        requests = storage.load_requests()

        self.assertEqual(2, len(requests))
        self.assertEqual(request_1.id, requests[0].id)
        self.assertEqual(request_2.id, requests[1].id)
        self.assertIsNone(requests[0].response)
        self.assertIsNone(requests[1].response)

    def test_load_response(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response()
        storage.save_response(request.id, response)

        requests = storage.load_requests()

        self.assertIsNotNone(requests[0].response)

    def test_load_request_body(self):
        body = b'test request body'
        request = self._create_request(body=body)
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)

        request_body = storage.load_request_body(request.id)

        self.assertEqual(body, request_body)

    def test_load_response_body(self):
        body = b'test response body'
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        mock_response = self._create_response(body=body)
        storage.save_response(request.id, mock_response)

        response_body = storage.load_response_body(request.id)

        self.assertEqual(body, response_body)

    def test_load_response_body_encoded(self):
        body = b'test response body'
        io = BytesIO()
        with gzip.GzipFile(fileobj=io, mode='wb') as f:
            f.write(body)
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response(body=io.getvalue())
        response.headers['Content-Encoding'] = 'gzip'
        storage.save_response(request.id, response)

        response_body = storage.load_response_body(request.id)

        self.assertEqual(body, response_body)

    def test_load_response_body_encoded_error(self):
        body = b'test response body'
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response(body=body)
        response.headers['Content-Encoding'] = 'gzip'
        storage.save_response(request.id, response)

        response_body = storage.load_response_body(request.id)

        self.assertEqual(body, response_body)

    def test_load_last_request(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_request(request_2)

        last_request = storage.load_last_request()

        self.assertEqual(request_2.id, last_request.id)

    def test_load_last_request_none(self):
        storage = RequestStorage(base_dir=self.base_dir)

        last_request = storage.load_last_request()

        self.assertIsNone(last_request)

    def test_clear_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_request(request_2)

        storage.clear_requests()
        requests = storage.load_requests()

        self.assertFalse(requests)
        self.assertFalse(glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*', '*')))

    def test_get_cert_dir(self):
        storage = RequestStorage(base_dir=self.base_dir)

        self.assertTrue(fnmatch(storage.get_cert_dir(),
                                os.path.join(self.base_dir, '.seleniumwire', 'storage-*', 'certs')))

    def test_find(self):
        request_1 = self._create_request('http://www.example.com/test/path/?foo=bar')
        request_2 = self._create_request('http://www.stackoverflow.com/other/path/?x=y')
        mock_response = self._create_response()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_response(request_1.id, mock_response)
        storage.save_request(request_2)

        self.assertEqual(request_1.id, storage.find('/test/path/').id)
        self.assertEqual(request_1.id, storage.find('/test/path/?foo=bar').id)
        self.assertEqual(request_1.id, storage.find('http://www.example.com/test/path/?foo=bar').id)
        self.assertEqual(request_1.id, storage.find('http://www.example.com/test/path/').id)

        self.assertIsNone(storage.find('/different/path'))
        self.assertIsNone(storage.find('/test/path/?x=y'))
        self.assertIsNone(storage.find('http://www.example.com/different/path/?foo=bar'))
        self.assertIsNone(storage.find('http://www.different.com/test/path/?foo=bar'))
        self.assertIsNone(storage.find('http://www.example.com/test/path/?x=y'))

    def _get_stored_path(self, request_id, filename):
        return glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*',
                                      'request-{}'.format(request_id), filename))

    def _create_request(self, path='http://www.example.com/test/path/', body=None):
        headers = {
            'Host': 'www.example.com',
            'Accept': '*/*'
        }
        return Request(method='GET', path=path, headers=headers, body=body)

    def _create_response(self, body=None):
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': 500
        }
        return Response(status_code=200, reason='OK', headers=headers, body=body)

    def setUp(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'data')

    def tearDown(self):
        shutil.rmtree(os.path.join(self.base_dir), ignore_errors=True)

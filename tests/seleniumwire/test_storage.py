import glob
import gzip
import os
import pickle
import shutil
from datetime import datetime, timedelta
from fnmatch import fnmatch
from io import BytesIO
from unittest import TestCase

from seleniumwire.request import Request, Response, WebSocketMessage
from seleniumwire.storage import RequestStorage


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
        self.assertEqual('http://www.example.com/test/path/', loaded_request.url)
        self.assertEqual('GET', loaded_request.method)
        self.assertEqual({
            'Host': 'www.example.com',
            'Accept': '*/*'
        }, dict(loaded_request.headers))
        self.assertIsNone(loaded_request.response)

    def test_save_request_with_body(self):
        body = b'test request body'
        request = self._create_request(body=body)
        storage = RequestStorage(base_dir=self.base_dir)

        storage.save_request(request)

        request_file_path = self._get_stored_path(request.id, 'request')

        with open(request_file_path[0], 'rb') as loaded:
            loaded_request = pickle.load(loaded)

        self.assertEqual(body, loaded_request.body)

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
            'Content-Length': '500'
        }, dict(loaded_response.headers))

    def test_save_response_with_body(self):
        body = b'some response body'
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response(body=body)

        storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        with open(response_file_path[0], 'rb') as loaded:
            loaded_response = pickle.load(loaded)

        self.assertEqual(b'some response body', loaded_response.body)

    def test_save_response_no_request(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response()
        storage.clear_requests()

        storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        self.assertFalse(response_file_path)

    def test_save_har_entry(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)

        storage.save_har_entry(request.id, {'name': 'test_har_entry'})

        har_file_path = self._get_stored_path(request.id, 'har_entry')

        with open(har_file_path[0], 'rb') as loaded:
            loaded_har = pickle.load(loaded)

        self.assertEqual(loaded_har['name'], 'test_har_entry')

    def test_save_har_entry_no_request(self):
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        storage.clear_requests()

        storage.save_har_entry(request.id, {'name': 'test_har_entry'})

        har_file_path = self._get_stored_path(request.id, 'har_entry')

        self.assertFalse(har_file_path)

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

    def test_load_response_encoded_body(self):
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

        response_body = storage.load_requests()[0].response.body

        self.assertEqual(body, response_body)

    def test_load_response_encoded_body_error(self):
        body = b'test response body'
        request = self._create_request()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request)
        response = self._create_response(body=body)
        response.headers['Content-Encoding'] = 'gzip'
        storage.save_response(request.id, response)

        response_body = storage.load_requests()[0].response.body

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

    def test_load_request_with_ws_messages(self):
        storage = RequestStorage(base_dir=self.base_dir)
        request_1 = self._create_request()  # Websocket handshake request
        request_2 = self._create_request()
        storage.save_request(request_1)
        storage.save_request(request_2)
        storage.save_ws_message(request_1.id, WebSocketMessage(
            from_client=True,
            content='websocket test message',
            date=datetime.now(),
        ))

        requests = storage.load_requests()

        self.assertTrue(len(requests[0].ws_messages) > 0)
        self.assertEqual('websocket test message', requests[0].ws_messages[0].content)
        self.assertTrue(len(requests[1].ws_messages) == 0)

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

    def test_get_home_dir(self):
        storage = RequestStorage(base_dir=self.base_dir)

        self.assertEqual(os.path.join(self.base_dir, '.seleniumwire'), storage.home_dir)

    def test_get_session_dir(self):
        storage = RequestStorage(base_dir=self.base_dir)

        self.assertTrue(fnmatch(storage.session_dir, os.path.join(self.base_dir, '.seleniumwire', 'storage-*')))

    def test_find(self):
        request_1 = self._create_request('http://www.example.com/test/path/?foo=bar')
        request_2 = self._create_request('http://www.stackoverflow.com/other/path/?x=y')
        mock_response = self._create_response()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_response(request_1.id, mock_response)
        storage.save_request(request_2)

        self.assertEqual(request_1.id, storage.find('/test/path/').id)
        self.assertEqual(request_1.id, storage.find(r'/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, storage.find(r'http://www.example.com/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, storage.find(r'http://www.example.com/test/path/').id)

        self.assertIsNone(storage.find('/different/path'))
        self.assertIsNone(storage.find('/test/path/?x=y'))
        self.assertIsNone(storage.find(r'http://www.example.com/different/path/\?foo=bar'))
        self.assertIsNone(storage.find(r'http://www.different.com/test/path/\?foo=bar'))
        self.assertIsNone(storage.find(r'http://www.example.com/test/path/\?x=y'))

    def test_find_similar_urls(self):
        request_1 = self._create_request('https://192.168.1.1/redfish/v1')
        request_2 = self._create_request('https://192.168.1.1/redfish')
        mock_response = self._create_response()
        storage = RequestStorage(base_dir=self.base_dir)
        storage.save_request(request_1)
        storage.save_response(request_1.id, mock_response)
        storage.save_request(request_2)
        storage.save_response(request_2.id, mock_response)

        self.assertEqual(request_1.id, storage.find('.*v1').id)
        self.assertEqual(request_2.id, storage.find('https://192.168.1.1/redfish$').id)

    def _get_stored_path(self, request_id, filename):
        return glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*',
                                      'request-{}'.format(request_id), filename))

    def _create_request(self, url='http://www.example.com/test/path/', body=b''):
        headers = [
            ('Host', 'www.example.com'),
            ('Accept', '*/*')
        ]
        return Request(method='GET', url=url, headers=headers, body=body)

    def _create_response(self, body=b''):
        headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', '500')
        ]
        return Response(status_code=200, reason='OK', headers=headers, body=body)

    def setUp(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'data')

    def tearDown(self):
        shutil.rmtree(os.path.join(self.base_dir), ignore_errors=True)

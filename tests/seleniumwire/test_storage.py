import glob
import os
import pickle
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta
from fnmatch import fnmatch
from unittest import TestCase
from unittest.mock import patch

from seleniumwire.request import Request, Response, WebSocketMessage
from seleniumwire.storage import InMemoryRequestStorage, RequestStorage, create


class CreateTest(TestCase):
    @patch('seleniumwire.storage.os')
    def test_create_default_storage(self, mock_os):
        base_dir = '/some/dir'
        mock_os.path = os.path
        storage = create(base_dir=base_dir)

        self.assertIsInstance(storage, RequestStorage)
        self.assertEqual(storage.home_dir, os.path.join(base_dir, '.seleniumwire'))

    def test_create_in_memory_storage(self):
        storage = create(memory_only=True, maxsize=10)

        self.assertIsInstance(storage, InMemoryRequestStorage)
        self.assertEqual(storage._maxsize, 10)


class RequestStorageTest(TestCase):
    def test_initialise(self):
        storage_dir = glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*'))

        self.assertEqual(1, len(storage_dir))

    def test_cleanup_removes_storage(self):
        self.storage.cleanup()

        # The 'seleniumwire' parent folder should have been cleaned up
        # when there is nothing left inside of it.
        self.assertFalse(os.listdir(self.base_dir))

    def test_cleanup_does_not_remove_parent_folder(self):
        # There is an existing storage folder
        os.makedirs(os.path.join(self.base_dir, '.seleniumwire', 'teststorage'))
        self.storage.cleanup()

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

        self.storage.save_request(request)

        request_file_path = self._get_stored_path(request.id, 'request')

        with open(request_file_path[0], 'rb') as loaded:
            loaded_request = pickle.load(loaded)

        self.assertEqual(request.id, loaded_request.id)
        self.assertEqual('http://www.example.com/test/path/', loaded_request.url)
        self.assertEqual('GET', loaded_request.method)
        self.assertEqual({'Host': 'www.example.com', 'Accept': '*/*'}, dict(loaded_request.headers))
        self.assertIsNone(loaded_request.response)

    def test_save_request_with_body(self):
        body = b'test request body'
        request = self._create_request(body=body)

        self.storage.save_request(request)

        request_file_path = self._get_stored_path(request.id, 'request')

        with open(request_file_path[0], 'rb') as loaded:
            loaded_request = pickle.load(loaded)

        self.assertEqual(body, loaded_request.body)

    def test_save_response(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()

        self.storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        with open(response_file_path[0], 'rb') as loaded:
            loaded_response = pickle.load(loaded)

        self.assertEqual(200, loaded_response.status_code)
        self.assertEqual('OK', loaded_response.reason)
        self.assertEqual({'Content-Type': 'application/json', 'Content-Length': '500'}, dict(loaded_response.headers))

    def test_save_response_with_body(self):
        body = b'some response body'
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response(body=body)

        self.storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        with open(response_file_path[0], 'rb') as loaded:
            loaded_response = pickle.load(loaded)

        self.assertEqual(b'some response body', loaded_response.body)

    def test_save_response_no_request(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        self.storage.clear_requests()

        self.storage.save_response(request.id, response)

        response_file_path = self._get_stored_path(request.id, 'response')

        self.assertFalse(response_file_path)

    def test_save_har_entry(self):
        request = self._create_request()
        self.storage.save_request(request)

        self.storage.save_har_entry(request.id, {'name': 'test_har_entry'})

        har_file_path = self._get_stored_path(request.id, 'har_entry')

        with open(har_file_path[0], 'rb') as loaded:
            loaded_har = pickle.load(loaded)

        self.assertEqual(loaded_har['name'], 'test_har_entry')

    def test_save_har_entry_no_request(self):
        request = self._create_request()
        self.storage.save_request(request)
        self.storage.clear_requests()

        self.storage.save_har_entry(request.id, {'name': 'test_har_entry'})

        har_file_path = self._get_stored_path(request.id, 'har_entry')

        self.assertFalse(har_file_path)

    def test_load_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        requests = self.storage.load_requests()

        self.assertEqual(2, len(requests))
        self.assertEqual(request_1.id, requests[0].id)
        self.assertEqual(request_2.id, requests[1].id)
        self.assertIsNone(requests[0].response)
        self.assertIsNone(requests[1].response)

    @patch('seleniumwire.storage.pickle')
    def test_load_requests_unpickle_error(self, mock_pickle):
        request_1 = self._create_request()
        request_2 = self._create_request()
        mock_pickle.load.side_effect = [Exception, request_2]
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        requests = self.storage.load_requests()

        self.assertEqual(1, len(requests))
        self.assertEqual(request_2.id, requests[0].id)

    def test_iter_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        requests = self.storage.iter_requests()

        self.assertIsInstance(requests, Iterator)
        requests = list(requests)
        self.assertEqual(2, len(requests))
        self.assertEqual(request_1.id, requests[0].id)
        self.assertEqual(request_2.id, requests[1].id)

    def test_load_response(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        self.storage.save_response(request.id, response)

        requests = self.storage.load_requests()

        self.assertIsNotNone(requests[0].response)

    @patch('seleniumwire.storage.pickle')
    def test_load_response_unpickle_error(self, mock_pickle):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        self.storage.save_response(request.id, response)
        mock_pickle.load.side_effect = [request, Exception]

        requests = self.storage.load_requests()

        self.assertIsNone(requests[0].response)

    def test_load_last_request(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        last_request = self.storage.load_last_request()

        self.assertEqual(request_2.id, last_request.id)

    def test_load_last_request_none(self):
        last_request = self.storage.load_last_request()

        self.assertIsNone(last_request)

    def test_load_request_with_ws_messages(self):
        request_1 = self._create_request()  # Websocket handshake request
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)
        self.storage.save_ws_message(
            request_1.id,
            WebSocketMessage(
                from_client=True,
                content='websocket test message',
                date=datetime.now(),
            ),
        )

        requests = self.storage.load_requests()

        self.assertTrue(len(requests[0].ws_messages) > 0)
        self.assertEqual('websocket test message', requests[0].ws_messages[0].content)
        self.assertTrue(len(requests[1].ws_messages) == 0)

    def test_load_request_cert_data(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        response.cert = {'subject': 'test_cert'}
        self.storage.save_response(request.id, response)

        requests = self.storage.load_requests()

        self.assertEqual({'subject': 'test_cert'}, requests[0].cert)
        self.assertFalse(hasattr(requests[0].response, 'cert'))

    def test_clear_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        self.storage.clear_requests()
        requests = self.storage.load_requests()

        self.assertFalse(requests)
        self.assertFalse(glob.glob(os.path.join(self.base_dir, '.seleniumwire', 'storage-*', '*')))

    def test_get_home_dir(self):
        self.assertEqual(os.path.join(self.base_dir, '.seleniumwire'), self.storage.home_dir)

    def test_get_session_dir(self):
        self.assertTrue(fnmatch(self.storage.session_dir, os.path.join(self.base_dir, '.seleniumwire', 'storage-*')))

    def test_find(self):
        request_1 = self._create_request('http://www.example.com/test/path/?foo=bar')
        request_2 = self._create_request('http://www.stackoverflow.com/other/path/?x=y')
        mock_response = self._create_response()
        self.storage.save_request(request_1)
        self.storage.save_response(request_1.id, mock_response)
        self.storage.save_request(request_2)

        self.assertEqual(request_1.id, self.storage.find('/test/path/').id)
        self.assertEqual(request_1.id, self.storage.find(r'/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, self.storage.find(r'http://www.example.com/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, self.storage.find(r'http://www.example.com/test/path/').id)

        self.assertIsNone(self.storage.find('/different/path'))
        self.assertIsNone(self.storage.find('/test/path/?x=y'))
        self.assertIsNone(self.storage.find(r'http://www.example.com/different/path/\?foo=bar'))
        self.assertIsNone(self.storage.find(r'http://www.different.com/test/path/\?foo=bar'))
        self.assertIsNone(self.storage.find(r'http://www.example.com/test/path/\?x=y'))

    def test_find_similar_urls(self):
        request_1 = self._create_request('https://192.168.1.1/redfish/v1')
        request_2 = self._create_request('https://192.168.1.1/redfish')
        mock_response = self._create_response()
        self.storage.save_request(request_1)
        self.storage.save_response(request_1.id, mock_response)
        self.storage.save_request(request_2)
        self.storage.save_response(request_2.id, mock_response)

        self.assertEqual(request_1.id, self.storage.find('.*v1').id)
        self.assertEqual(request_2.id, self.storage.find('https://192.168.1.1/redfish$').id)

    def _get_stored_path(self, request_id, filename):
        return glob.glob(
            os.path.join(self.base_dir, '.seleniumwire', 'storage-*', 'request-{}'.format(request_id), filename)
        )

    def _create_request(self, url='http://www.example.com/test/path/', body=b''):
        headers = [('Host', 'www.example.com'), ('Accept', '*/*')]
        return Request(method='GET', url=url, headers=headers, body=body)

    def _create_response(self, body=b''):
        headers = [('Content-Type', 'application/json'), ('Content-Length', '500')]
        return Response(status_code=200, reason='OK', headers=headers, body=body)

    def setUp(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.storage = RequestStorage(base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(os.path.join(self.base_dir), ignore_errors=True)


class InMemoryRequestStorageTest(TestCase):
    def test_save_request(self):
        request = self._create_request()

        self.storage.save_request(request)

        self.assertEqual(self.storage.load_requests()[0], request)

    def test_save_request_max_size(self):
        self.storage = InMemoryRequestStorage(maxsize=3)
        requests = [self._create_request() for _ in range(10)]

        for request in requests:
            self.storage.save_request(request)

        self.assertEqual(self.storage.load_requests(), requests[7:])

    def test_save_request_max_size_zero(self):
        self.storage = InMemoryRequestStorage(maxsize=0)
        requests = [self._create_request() for _ in range(10)]

        for request in requests:
            self.storage.save_request(request)

        self.assertEqual(len(self.storage.load_requests()), 0)

    def test_save_response(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()

        self.storage.save_response(request.id, response)

        self.assertEqual(self.storage.load_requests()[0].response, response)

    def test_save_response_cert_data(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        response.cert = 'cert_data'

        self.storage.save_response(request.id, response)

        request = self.storage.load_requests()[0]
        self.assertEqual(request.cert, 'cert_data')
        self.assertFalse(hasattr(request.response, 'cert'))

    def test_save_response_no_request(self):
        request = self._create_request()
        self.storage.save_request(request)
        response = self._create_response()
        self.storage.clear_requests()

        self.storage.save_response(request.id, response)

        self.assertEqual(len(self.storage.load_requests()), 0)

    def test_save_har_entry(self):
        request = self._create_request()
        har_entry = {'name': 'test_har_entry'}
        self.storage.save_request(request)

        self.storage.save_har_entry(request.id, har_entry)

        self.assertEqual(self.storage.load_har_entries()[0], har_entry)

    def test_save_har_entry_no_request(self):
        request = self._create_request()
        self.storage.save_request(request)
        self.storage.clear_requests()

        self.storage.save_har_entry(request.id, {'name': 'test_har_entry'})

        self.assertEqual(len(self.storage.load_har_entries()), 0)

    def test_load_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        requests = self.storage.load_requests()

        self.assertEqual(2, len(requests))
        self.assertEqual(request_1.id, requests[0].id)
        self.assertEqual(request_2.id, requests[1].id)
        self.assertIsNone(requests[0].response)
        self.assertIsNone(requests[1].response)

    def test_iter_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        requests = self.storage.iter_requests()

        self.assertIsInstance(requests, Iterator)
        requests = list(requests)
        self.assertEqual(2, len(requests))
        self.assertEqual(request_1.id, requests[0].id)
        self.assertEqual(request_2.id, requests[1].id)

    def test_load_last_request(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        last_request = self.storage.load_last_request()

        self.assertEqual(request_2.id, last_request.id)

    def test_load_last_request_none(self):
        last_request = self.storage.load_last_request()

        self.assertIsNone(last_request)

    def test_load_request_with_ws_messages(self):
        request_1 = self._create_request()  # Websocket handshake request
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)
        self.storage.save_ws_message(
            request_1.id,
            WebSocketMessage(
                from_client=True,
                content='websocket test message',
                date=datetime.now(),
            ),
        )

        requests = self.storage.load_requests()

        self.assertTrue(len(requests[0].ws_messages) > 0)
        self.assertEqual('websocket test message', requests[0].ws_messages[0].content)
        self.assertTrue(len(requests[1].ws_messages) == 0)

    def test_clear_requests(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        self.storage.clear_requests()
        requests = self.storage.load_requests()

        self.assertFalse(requests)

    def test_cleanup(self):
        request_1 = self._create_request()
        request_2 = self._create_request()
        self.storage.save_request(request_1)
        self.storage.save_request(request_2)

        self.storage.cleanup()
        requests = self.storage.load_requests()

        self.assertFalse(requests)

    def test_get_home_dir(self):
        self.assertEqual(os.path.join(tempfile.gettempdir(), '.seleniumwire'), self.storage.home_dir)

    def test_find(self):
        request_1 = self._create_request('http://www.example.com/test/path/?foo=bar')
        request_2 = self._create_request('http://www.stackoverflow.com/other/path/?x=y')
        mock_response = self._create_response()
        self.storage.save_request(request_1)
        self.storage.save_response(request_1.id, mock_response)
        self.storage.save_request(request_2)

        self.assertEqual(request_1.id, self.storage.find('/test/path/').id)
        self.assertEqual(request_1.id, self.storage.find(r'/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, self.storage.find(r'http://www.example.com/test/path/\?foo=bar').id)
        self.assertEqual(request_1.id, self.storage.find(r'http://www.example.com/test/path/').id)

        self.assertIsNone(self.storage.find('/different/path'))
        self.assertIsNone(self.storage.find('/test/path/?x=y'))
        self.assertIsNone(self.storage.find(r'http://www.example.com/different/path/\?foo=bar'))
        self.assertIsNone(self.storage.find(r'http://www.different.com/test/path/\?foo=bar'))
        self.assertIsNone(self.storage.find(r'http://www.example.com/test/path/\?x=y'))

    def test_find_similar_urls(self):
        request_1 = self._create_request('https://192.168.1.1/redfish/v1')
        request_2 = self._create_request('https://192.168.1.1/redfish')
        mock_response = self._create_response()
        self.storage.save_request(request_1)
        self.storage.save_response(request_1.id, mock_response)
        self.storage.save_request(request_2)
        self.storage.save_response(request_2.id, mock_response)

        self.assertEqual(request_1.id, self.storage.find('.*v1').id)
        self.assertEqual(request_2.id, self.storage.find('https://192.168.1.1/redfish$').id)

    def _create_request(self, url='http://www.example.com/test/path/'):
        headers = [('Host', 'www.example.com'), ('Accept', '*/*')]
        return Request(method='GET', url=url, headers=headers, body=b'foobarbaz')

    def _create_response(self, body=b''):
        headers = [('Content-Type', 'application/json'), ('Content-Length', '500')]
        return Response(status_code=200, reason='OK', headers=headers, body=body)

    def setUp(self) -> None:
        self.storage = InMemoryRequestStorage()

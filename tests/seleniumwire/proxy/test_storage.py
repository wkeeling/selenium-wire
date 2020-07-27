import glob
import gzip
import os
import pickle
import shutil
from datetime import datetime, timedelta
from fnmatch import fnmatch
from io import BytesIO
from unittest import TestCase
import pytest

from seleniumwire.proxy.request import Request, Response
from seleniumwire.proxy.storage import RequestStorage, InMemoryRequestStorage


@pytest.fixture
def base_dir():
    base_dir = os.path.join(os.path.dirname(__file__), 'data')
    yield base_dir
    shutil.rmtree(os.path.join(base_dir), ignore_errors=True)


def _get_stored_path(base_dir, request_id, filename):
    return glob.glob(os.path.join(base_dir, '.seleniumwire', 'storage-*',
                                  'request-{}'.format(request_id), filename))


def _create_request(url='http://www.example.com/test/path/', body=None):
    headers = {
        'Host': 'www.example.com',
        'Accept': '*/*'
    }
    return Request(method='GET', url=url, headers=headers, body=body)


def _create_response(body=None):
    headers = {
        'Content-Type': 'application/json',
        'Content-Length': 500
    }
    return Response(status_code=200, reason='OK', headers=headers, body=body)


@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_initialise(base_dir, storage_cls):
    storage_cls(base_dir=base_dir)
    storage_dir = glob.glob(os.path.join(base_dir, '.seleniumwire', 'storage-*'))

    assert 1 == len(storage_dir)

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_cleanup_removes_storage(base_dir, storage_cls):
    storage = storage_cls(base_dir=base_dir)
    storage.cleanup()

    # The 'seleniumwire' parent folder should have been cleaned up
    # when there is nothing left inside of it.
    assert not os.listdir(base_dir)

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_cleanup_does_not_remove_parent_folder(base_dir, storage_cls):
    # There is an existing storage folder
    os.makedirs(os.path.join(base_dir, '.seleniumwire', 'teststorage'))
    storage = storage_cls(base_dir=base_dir)
    storage.cleanup()

    # The existing storage folder is not cleaned up
    assert 1 == len(os.listdir(base_dir))
    assert os.path.exists(os.path.join(base_dir, '.seleniumwire', 'teststorage'))

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_initialise_clears_old_folders(base_dir, storage_cls):
    old_dir = os.path.join(base_dir, '.seleniumwire', 'storage-test1')
    new_dir = os.path.join(base_dir, '.seleniumwire', 'storage-test2')
    os.makedirs(old_dir)
    os.makedirs(new_dir)
    two_days_ago = (datetime.now() - timedelta(days=2)).timestamp()
    os.utime(old_dir, times=(two_days_ago, two_days_ago))

    storage_cls(base_dir=base_dir)

    assert not os.path.exists(old_dir)
    assert os.path.exists(new_dir)


@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_requests(base_dir, storage_cls):
    request_1 = _create_request()
    request_2 = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request_1)
    storage.save_request(request_2)

    requests = storage.load_requests()

    assert 2 == len(requests)
    assert request_1.id == requests[0].id
    assert request_2.id == requests[1].id
    assert requests[0].response is None
    assert requests[1].response is None

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_response(base_dir, storage_cls):
    request = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response()
    storage.save_response(request.id, response)

    requests = storage.load_requests()

    assert requests[0].response is not None

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_request_body(base_dir, storage_cls):
    body = b'test request body'
    request = _create_request(body=body)
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request)

    request_body = storage.load_request_body(request.id)

    assert body == request_body

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_response_body(base_dir, storage_cls):
    body = b'test response body'
    request = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request)
    mock_response = _create_response(body=body)
    storage.save_response(request.id, mock_response)

    response_body = storage.load_response_body(request.id)

    assert body == response_body

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_response_body_encoded(base_dir, storage_cls):
    body = b'test response body'
    io = BytesIO()
    with gzip.GzipFile(fileobj=io, mode='wb') as f:
        f.write(body)
    request = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response(body=io.getvalue())
    response.headers['Content-Encoding'] = 'gzip'
    storage.save_response(request.id, response)

    response_body = storage.load_response_body(request.id)

    assert body == response_body

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_response_body_encoded_error(base_dir, storage_cls):
    body = b'test response body'
    request = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response(body=body)
    response.headers['Content-Encoding'] = 'gzip'
    storage.save_response(request.id, response)

    response_body = storage.load_response_body(request.id)

    assert body == response_body

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_last_request(base_dir, storage_cls):
    request_1 = _create_request()
    request_2 = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request_1)
    storage.save_request(request_2)

    last_request = storage.load_last_request()

    assert request_2.id == last_request.id

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_load_last_request_none(base_dir, storage_cls):
    storage = storage_cls(base_dir=base_dir)

    last_request = storage.load_last_request()

    assert last_request is None

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_clear_requests(base_dir, storage_cls):
    request_1 = _create_request()
    request_2 = _create_request()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request_1)
    storage.save_request(request_2)

    storage.clear_requests()
    requests = storage.load_requests()

    assert not requests
    assert not glob.glob(os.path.join(base_dir, '.seleniumwire', 'storage-*', '*'))

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_get_cert_dir(base_dir, storage_cls):
    storage = storage_cls(base_dir=base_dir)

    assert fnmatch(storage.get_cert_dir(),
                   os.path.join(base_dir, '.seleniumwire', 'storage-*', 'certs'))

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_find(base_dir, storage_cls):
    request_1 = _create_request('http://www.example.com/test/path/?foo=bar')
    request_2 = _create_request('http://www.stackoverflow.com/other/path/?x=y')
    mock_response = _create_response()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request_1)
    storage.save_response(request_1.id, mock_response)
    storage.save_request(request_2)

    assert request_1.id == storage.find('/test/path/').id
    assert request_1.id == storage.find('/test/path/\?foo=bar').id
    assert request_1.id == storage.find('http://www.example.com/test/path/\?foo=bar').id
    assert request_1.id == storage.find('http://www.example.com/test/path/').id

    assert storage.find('/different/path') is None
    assert storage.find('/test/path/?x=y') is None
    assert storage.find('http://www.example.com/different/path/\?foo=bar') is None
    assert storage.find('http://www.different.com/test/path/\?foo=bar') is None
    assert storage.find('http://www.example.com/test/path/\?x=y') is None

@pytest.mark.parametrize("storage_cls", [RequestStorage, InMemoryRequestStorage])
def test_find_similar_urls(base_dir, storage_cls):
    request_1 = _create_request('https://192.168.1.1/redfish/v1')
    request_2 = _create_request('https://192.168.1.1/redfish')
    mock_response = _create_response()
    storage = storage_cls(base_dir=base_dir)
    storage.save_request(request_1)
    storage.save_response(request_1.id, mock_response)
    storage.save_request(request_2)
    storage.save_response(request_2.id, mock_response)

    assert request_1.id == storage.find('.*v1').id
    assert request_2.id == storage.find('https://192.168.1.1/redfish$').id


# these tests check disk, only apply to RequestStorage:
def test_save_request(base_dir):
    request = _create_request()
    storage = RequestStorage(base_dir=base_dir)

    storage.save_request(request)

    request_file_path = _get_stored_path(base_dir, request.id, 'request')

    with open(request_file_path[0], 'rb') as loaded:
        loaded_request = pickle.load(loaded)

    assert request.id == loaded_request.id
    assert 'http://www.example.com/test/path/' == loaded_request.url
    assert 'GET' == loaded_request.method
    assert {
        'Host': 'www.example.com',
        'Accept': '*/*'
    } == loaded_request.headers
    assert loaded_request.response is None

def test_save_request_with_body(base_dir):
    body = b'test request body'
    request = _create_request(body=body)
    storage = RequestStorage(base_dir=base_dir)

    storage.save_request(request)

    request_body_path = _get_stored_path(base_dir, request.id, 'requestbody')

    with open(request_body_path[0], 'rb') as loaded:
        loaded_body = pickle.load(loaded)

    assert body == loaded_body

def test_save_response(base_dir):
    request = _create_request()
    storage = RequestStorage(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response()

    storage.save_response(request.id, response)

    response_file_path = _get_stored_path(base_dir, request.id, 'response')

    with open(response_file_path[0], 'rb') as loaded:
        loaded_response = pickle.load(loaded)

    assert 200 == loaded_response.status_code
    assert 'OK' == loaded_response.reason
    assert {
        'Content-Type': 'application/json',
        'Content-Length': 500
    } == loaded_response.headers

def test_save_response_with_body(base_dir):
    body = b'some response body'
    request = _create_request()
    storage = RequestStorage(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response(body=body)

    storage.save_response(request.id, response)

    response_body_path = _get_stored_path(base_dir, request.id, 'responsebody')

    with open(response_body_path[0], 'rb') as loaded:
        loaded_body = pickle.load(loaded)

    assert b'some response body' == loaded_body

def test_save_response_no_request(base_dir):
    request = _create_request()
    storage = RequestStorage(base_dir=base_dir)
    storage.save_request(request)
    response = _create_response()
    storage.clear_requests()

    storage.save_response(request.id, response)

    response_file_path = _get_stored_path(base_dir, request.id, 'response')

    assert not response_file_path

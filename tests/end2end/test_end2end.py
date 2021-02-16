"""End to end tests for Selenium Wire.

Note that these tests are meant to cover off many of the main use cases
but are not meant to be exhaustive. They require expensive setup and are
slow to run. For edge cases and niche scenarios, consider writing a
unit test where it makes sense.
"""

import json
import shutil
from pathlib import Path

import pytest
from selenium.common.exceptions import TimeoutException

from seleniumwire import webdriver
from tests import utils as testutils


@pytest.fixture(scope='module')
def httpbin():
    httpbin = testutils.get_httpbin()
    yield httpbin
    httpbin.close()


@pytest.fixture
def chrome_options():
    options = webdriver.ChromeOptions()
    options.binary_location = testutils.get_headless_chromium()
    return options


@pytest.fixture
def driver_path():
    return str(Path(__file__).parent / Path('linux', 'chromedriver'))


@pytest.fixture
def driver(chrome_options, driver_path):
    driver = webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
    )

    yield driver

    driver.quit()
    cleanup()


def cleanup():
    try:
        (Path(__file__).parent / Path('linux', 'chrome_debug.log')).unlink()
    except FileNotFoundError:
        pass
    shutil.rmtree(
        Path(__file__).parent / Path('linux', 'locales'),
        ignore_errors=True
    )
    shutil.rmtree(
        Path(__file__).parent / 'chrome_tmp',
        ignore_errors=True
    )


def test_capture_requests(driver, httpbin):
    driver.get(f'{httpbin}/html')

    assert f'{httpbin}/html' in [r.url for r in driver.requests]
    del driver.requests
    assert not driver.requests


def test_last_request(driver, httpbin):
    driver.get(f'{httpbin}/html')
    driver.get(f'{httpbin}/anything')

    assert driver.last_request.url == f'{httpbin}/anything'


def test_wait_for_request(driver, httpbin):
    driver.get(f'{httpbin}/html')
    driver.get(f'{httpbin}/anything/hello/world')
    driver.get(f'{httpbin}/anything/foo/bar/baz?spam=eggs')

    request = driver.wait_for_request(r'\/hello\/')

    assert request.url == f'{httpbin}/anything/hello/world'


def test_wait_for_request_timeout(driver, httpbin):
    driver.get(f'{httpbin}/html')

    with pytest.raises(TimeoutException):
        driver.wait_for_request(r'\/hello\/', timeout=2)


def test_scopes(driver, httpbin):
    driver.scopes = [
        '.*/anything/.*'
    ]

    driver.get(f'{httpbin}/anything/hello/world')
    driver.get(f'{httpbin}/html')

    assert len(driver.requests) == 1
    assert driver.requests[0].url == f'{httpbin}/anything/hello/world'


def test_add_request_header(driver, httpbin):
    def interceptor(req):
        req.headers['X-New-Header'] = 'test'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')
    request = driver.wait_for_request('/headers')

    data = json.loads(request.response.body.decode('utf-8'))

    assert data['headers']['X-New-Header'] == 'test'


def test_replace_request_header(driver, httpbin):
    def interceptor(req):
        del req.headers['User-Agent']
        req.headers['User-Agent'] = 'test_user_agent'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')
    request = driver.wait_for_request('/headers')

    data = json.loads(request.response.body.decode('utf-8'))

    assert data['headers']['User-Agent'] == 'test_user_agent'


def test_add_duplicate_request_header(driver, httpbin):
    def interceptor(req):
        del req.headers['Referer']
        req.headers['Referer'] = 'some_referer'
        # Adding a header that already exists will add a duplicate
        # header rather than overwriting the existing header.
        req.headers['Referer'] = 'another_referer'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')
    request = driver.wait_for_request('/headers')

    data = json.loads(request.response.body.decode('utf-8'))

    assert data['headers']['Referer'] == 'some_referer,another_referer'


def test_add_request_parameter(driver, httpbin):
    def interceptor(req):
        params = req.params
        params['foo'] = 'bar'
        req.params = params

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/get?spam=eggs')
    request = driver.wait_for_request(r'get\?spam=eggs')

    data = json.loads(request.response.body.decode('utf-8'))

    assert data['args'] == {'foo': 'bar', 'spam': 'eggs'}


def test_update_json_post_request(chrome_options, driver_path, httpbin):
    # We need to start Chrome with --disable-web-security so that it
    # can post JSON from a file-based form to our httpbin endpoint.
    # Without that option the AJAX post would be blocked by CORS.
    chrome_options.add_argument('--disable-web-security')
    chrome_data_dir = Path(__file__).parent / 'chrome_tmp'
    chrome_options.add_argument(f'--user-data-dir={str(chrome_data_dir)}')
    chrome_options.add_argument('--ignore-certificate-errors')

    driver = webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
    )

    def interceptor(req):
        if req.method == 'POST' and req.headers['Content-Type'] == 'application/json':
            # We expect the request body to contain the JSON:
            # '{ "hello": "world", "spam": "eggs" }'
            body = req.body.decode('utf-8')
            data = json.loads(body)
            data['foo'] = 'bar'  # Add a new property
            req.body = json.dumps(data).encode('utf-8')
            del req.headers['Content-Length']
            req.headers['Content-Length'] = str(len(req.body))

    driver.request_interceptor = interceptor

    form = Path(__file__).parent / 'jsonform.html'
    driver.get(f'file:///{str(form)}')
    button = driver.find_element_by_id('submit')
    button.click()
    request = driver.wait_for_request('/post')

    resp_body = json.loads(request.response.body.decode('utf-8'))

    assert resp_body['json'] == {'hello': 'world', 'spam': 'eggs', 'foo': 'bar'}


def test_block_a_request(driver, httpbin):
    def interceptor(req):
        req.abort()

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/image/png')
    request = driver.wait_for_request('/image/png')

    assert request.response.status_code == 403


def test_mock_a_response(driver, httpbin):
    def interceptor(req):
        if req.url == f'{httpbin}/html':
            req.create_response(
                status_code=200,
                headers={'Content-Type': 'text/html'},
                body='<html>Hello World!</html>'
            )

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/html')
    driver.wait_for_request('/html')

    assert 'Hello World!' in driver.page_source

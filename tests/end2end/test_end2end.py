"""End to end tests for Selenium Wire.

Note that these tests are meant to cover off many of the main use cases
but are not meant to be exhaustive. They require expensive setup and are
slow to run. For edge cases and niche scenarios, consider writing a
unit test where it makes sense.
"""

import json
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
    options.binary_location = str(Path(__file__).parent / Path('linux', 'headless-chromium'))
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

    return driver


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
    def interceptor(request):
        request.headers['X-New-Header'] = 'test'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')

    data = json.loads(driver.requests[0].response.body.decode('utf-8'))

    assert data['headers']['X-New-Header'] == 'test'


def test_replace_request_header(driver, httpbin):
    def interceptor(request):
        del request.headers['User-Agent']
        request.headers['User-Agent'] = 'test_user_agent'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')

    data = json.loads(driver.requests[0].response.body.decode('utf-8'))

    assert data['headers']['User-Agent'] == 'test_user_agent'


def test_add_duplicate_request_header(driver, httpbin):
    def interceptor(request):
        del request.headers['Referer']
        request.headers['Referer'] = 'some_referer'
        # Adding a header that already exists will add a duplicate
        # header rather than overwriting the existing header.
        request.headers['Referer'] = 'another_referer'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')

    data = json.loads(driver.requests[0].response.body.decode('utf-8'))

    assert data['headers']['Referer'] == 'some_referer,another_referer'

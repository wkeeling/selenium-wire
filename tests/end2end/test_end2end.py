"""End to end tests for Selenium Wire."""

import json
import shutil
import threading
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


@pytest.fixture(scope='module')
def httpproxy():
    httpproxy = testutils.get_proxy()
    yield httpproxy
    httpproxy.close()


@pytest.fixture(scope='module')
def socksproxy():
    httpproxy = testutils.get_proxy(port=8087, mode='socks')
    yield httpproxy
    httpproxy.close()


@pytest.fixture
def driver_path():
    return str(Path(__file__).parent / Path('linux', 'chromedriver'))


@pytest.fixture
def chrome_options():
    options = webdriver.ChromeOptions()
    options.binary_location = testutils.get_headless_chromium()
    return options


@pytest.fixture
def driver(driver_path, chrome_options):
    driver = create_driver(driver_path, chrome_options)
    yield driver
    driver.quit()


def create_driver(
        driver_path,
        chrome_options,
        seleniumwire_options=None,
        desired_capabilities=None,
):
    return webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
        seleniumwire_options=seleniumwire_options,
        desired_capabilities=desired_capabilities,
    )


def teardown_function():
    try:
        (Path(__file__).parent / Path('linux', 'chrome_debug.log')).unlink()
    except FileNotFoundError:
        pass

    shutil.rmtree(
        Path(__file__).parent / Path('linux', 'locales'), ignore_errors=True
    )

    shutil.rmtree(
        Path(__file__).parent / 'chrome_tmp', ignore_errors=True
    )


def test_capture_requests(driver, httpbin):
    driver.get(f'{httpbin}/html')

    assert driver.requests
    assert all(r.response is not None for r in driver.requests)
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

    data = json.loads(driver.last_request.response.body.decode('utf-8'))

    assert data['headers']['X-New-Header'] == 'test'


def test_replace_request_header(driver, httpbin):
    def interceptor(req):
        del req.headers['User-Agent']
        req.headers['User-Agent'] = 'test_user_agent'

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/headers')

    data = json.loads(driver.last_request.response.body.decode('utf-8'))

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

    data = json.loads(driver.last_request.response.body.decode('utf-8'))

    assert data['headers']['Referer'] == 'some_referer,another_referer'


def test_add_request_parameter(driver, httpbin):
    def interceptor(req):
        params = req.params
        params['foo'] = 'bar'
        req.params = params

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/get?spam=eggs')

    data = json.loads(driver.last_request.response.body.decode('utf-8'))

    assert data['args'] == {'foo': 'bar', 'spam': 'eggs'}


def test_update_json_post_request(driver_path, chrome_options, httpbin):
    # We need to start Chrome with --disable-web-security so that it
    # can post JSON from a file-based form to our httpbin endpoint.
    # Without that option the AJAX post would be blocked by CORS.
    chrome_options.add_argument('--disable-web-security')
    chrome_data_dir = Path(__file__).parent / 'chrome_tmp'
    chrome_options.add_argument(f'--user-data-dir={str(chrome_data_dir)}')

    driver = create_driver(driver_path, chrome_options)

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
    button.click()  # Makes Ajax request so need to wait for it
    request = driver.wait_for_request('/post')

    resp_body = json.loads(request.response.body.decode('utf-8'))

    assert resp_body['json'] == {'hello': 'world', 'spam': 'eggs', 'foo': 'bar'}

    driver.quit()


def test_block_a_request(driver, httpbin):
    def interceptor(req):
        req.abort()

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/image/png')

    assert driver.last_request.response.status_code == 403


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

    assert 'Hello World!' in driver.page_source


def test_mitmproxy_backend(driver_path, chrome_options, httpbin):
    sw_options = {
        'backend': 'mitmproxy'
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert driver.last_request.response is not None

    driver.quit()


def test_upstream_http_proxy(driver_path, chrome_options, httpbin, httpproxy):
    sw_options = {
        'proxy': {
            'https': f'{httpproxy}'
        }
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert 'This passed through a http proxy' in driver.page_source

    driver.quit()


def test_upstream_http_proxy_basic_auth(driver_path, chrome_options, httpbin):
    httpproxy = None

    try:
        httpproxy = testutils.get_proxy(mode='http', port=8088, auth='test:test')
        sw_options = {
            'proxy': {
                'https': f'{httpproxy}'
            }
        }

        driver = create_driver(driver_path, chrome_options, sw_options)
        driver.get(f'{httpbin}/html')

        assert 'This passed through a authenticated http proxy' in driver.page_source

        driver.quit()
    finally:
        if httpproxy:
            httpproxy.close()


def test_upstream_http_proxy_custom_auth(driver_path, chrome_options, httpbin):
    httpproxy = None

    try:
        httpproxy = testutils.get_proxy(mode='http', port=8088, auth='test:test')
        sw_options = {
            'proxy': {
                'https': 'https://localhost:8088',
                'custom_authorization': 'Basic dGVzdDp0ZXN0',  # Omit newline from end of the string
            },
        }

        driver = create_driver(driver_path, chrome_options, sw_options)
        driver.get(f'{httpbin}/html')

        assert 'This passed through a authenticated http proxy' in driver.page_source

        driver.quit()
    finally:
        if httpproxy:
            httpproxy.close()


def test_upstream_socks_proxy(driver_path, chrome_options, httpbin, socksproxy):
    """Note that authenticated socks proxy is not supported by mitmproxy currently
    so we're only able to test unauthenticated.
    """
    sw_options = {
        'proxy': {
            'https': f'{socksproxy}'
        }
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert 'This passed through a socks proxy' in driver.page_source

    driver.quit()


@pytest.mark.skip('Skipping until no_proxy option has been fixed')
def test_bypass_upstream_http_proxy(driver_path, chrome_options, httpbin, httpproxy):
    sw_options = {
        'proxy': {
            'https': f'{httpproxy}',
            'no_proxy': 'localhost'
        }
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert 'This passed through a http proxy' not in driver.page_source

    driver.quit()


def test_no_auto_config(driver_path, chrome_options, httpbin):
    sw_options = {
        'auto_config': False
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert not driver.requests

    driver.quit()


def test_no_auto_config_manual_proxy(driver_path, chrome_options, httpbin):
    """This demonstrates how you would separate browser proxy configuration
    from Selenium Wire proxy configuration.

    You might want to do this if you need the browser to address
    Selenium Wire using a different IP/host than what Selenium Wire uses
    by default. E.g. A dynamic hostname for a container setup.
    """
    capabilities = webdriver.DesiredCapabilities.CHROME.copy()
    capabilities['proxy'] = {
        'proxyType': 'manual',
        'sslProxy': '{}:{}'.format('localhost', 8088),
    }
    capabilities['acceptInsecureCerts'] = True

    sw_options = {
        'auto_config': False,
        'addr': '127.0.0.1',
        'port': 8088,
    }

    driver = create_driver(
        driver_path,
        chrome_options,
        sw_options,
        capabilities,
    )

    driver.get(f'{httpbin}/html')
    driver.wait_for_request('/html')

    driver.quit()


def test_exclude_hosts(driver_path, chrome_options, httpbin):
    sw_options = {
        'exclude_hosts': ['localhost']
    }

    driver = create_driver(driver_path, chrome_options, sw_options)
    driver.get(f'{httpbin}/html')

    assert not driver.requests

    driver.quit()


@pytest.mark.skip("Fails on GitHub Actions - chromedriver instances timeout")
def test_multiple_threads(driver_path, chrome_options, httpbin):
    num_threads = 5
    threads, results = [], []

    def run_driver():
        driver = create_driver(driver_path, chrome_options)
        driver.get(f'{httpbin}/html')
        request = driver.wait_for_request('/html')
        results.append(request)
        driver.quit()

    for i in range(num_threads):
        t = threading.Thread(
            name=f'Driver thread {i + 1}',
            target=run_driver
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    assert len(results) == num_threads

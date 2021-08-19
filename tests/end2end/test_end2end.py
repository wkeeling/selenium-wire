"""End to end tests for Selenium Wire."""

import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from glob import glob
from pathlib import Path
from unittest.mock import patch

import pytest
from selenium.common.exceptions import TimeoutException

import seleniumwire
from seleniumwire import webdriver
from seleniumwire.thirdparty.mitmproxy.exceptions import ServerException
from tests import utils as testutils


@pytest.fixture(scope='module')
def httpbin():
    # This module scoped Httpbin fixture uses HTTPS
    with create_httpbin() as httpbin:
        yield httpbin


@contextmanager
def create_httpbin(port=8085, use_https=True):
    httpbin = testutils.get_httpbin(port, use_https)
    try:
        yield httpbin
    finally:
        httpbin.close()


@pytest.fixture(scope='module')
def httpproxy():
    with create_httpproxy() as proxy:
        yield proxy


@contextmanager
def create_httpproxy(port=8086, mode='http', auth=''):
    httpproxy = testutils.get_proxy(port, mode, auth)
    try:
        yield httpproxy
    finally:
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
    with create_driver(driver_path, chrome_options) as driver:
        yield driver


@contextmanager
def create_driver(
    driver_path,
    chrome_options,
    seleniumwire_options=None,
    desired_capabilities=None,
):
    driver = webdriver.Chrome(
        executable_path=driver_path,
        options=chrome_options,
        seleniumwire_options=seleniumwire_options,
        desired_capabilities=desired_capabilities,
    )
    try:
        yield driver
    finally:
        driver.quit()


def teardown_function():
    try:
        (Path(__file__).parent / Path('linux', 'chrome_debug.log')).unlink()
    except FileNotFoundError:
        pass

    try:
        (Path(__file__).parent / Path('html.html')).unlink()
    except FileNotFoundError:
        pass

    shutil.rmtree(Path(__file__).parent / Path('linux', 'locales'), ignore_errors=True)

    shutil.rmtree(Path(__file__).parent / 'chrome_tmp', ignore_errors=True)


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
    driver.scopes = ['.*/anything/.*']

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


def test_add_response_header(driver, httpbin):
    def interceptor(req, res):
        # Causes the browser to trigger a download rather
        # than render the page.
        res.headers['Content-Disposition'] = 'attachment'

    driver.response_interceptor = interceptor
    driver.get(f'{httpbin}/html')

    # We don't expect to find this text in the page because
    # the HTML wasn't rendered.
    assert 'Herman Melville' not in driver.page_source


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

    with create_driver(driver_path, chrome_options) as driver:
        driver.request_interceptor = interceptor

        form = Path(__file__).parent / 'jsonform.html'
        driver.get(f'file:///{str(form)}')
        button = driver.find_element_by_id('submit')
        button.click()  # Makes Ajax request so need to wait for it
        request = driver.wait_for_request('/post')

        resp_body = json.loads(request.response.body.decode('utf-8'))

        assert resp_body['json'] == {'hello': 'world', 'spam': 'eggs', 'foo': 'bar'}


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
                status_code=200, headers={'Content-Type': 'text/html'}, body='<html>Hello World!</html>'
            )

    driver.request_interceptor = interceptor
    driver.get(f'{httpbin}/html')

    assert 'Hello World!' in driver.page_source


def test_upstream_http_proxy(driver_path, chrome_options, httpbin, httpproxy):
    sw_options = {'proxy': {'https': f'{httpproxy}'}}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert 'This passed through a http proxy' in driver.page_source


def test_upstream_http_proxy_basic_auth(driver_path, chrome_options, httpbin):
    with create_httpproxy(port=8888, auth='test:test') as httpproxy:
        sw_options = {'proxy': {'https': f'{httpproxy}'}}

        with create_driver(driver_path, chrome_options, sw_options) as driver:
            driver.get(f'{httpbin}/html')

            assert 'This passed through a authenticated http proxy' in driver.page_source


def test_upstream_http_proxy_basic_auth_empty_pass(driver_path, chrome_options, httpbin):
    with create_httpproxy(port=8888, auth='test:') as httpproxy:
        sw_options = {'proxy': {'https': f'{httpproxy}'}}

        with create_driver(driver_path, chrome_options, sw_options) as driver:
            driver.get(f'{httpbin}/html')

            assert 'This passed through a authenticated http proxy' in driver.page_source


def test_upstream_http_proxy_custom_auth(driver_path, chrome_options, httpbin):
    with create_httpproxy(port=8088, auth='test:test'):
        sw_options = {
            'proxy': {
                'https': 'https://localhost:8088',
                'custom_authorization': 'Basic dGVzdDp0ZXN0',  # Omit newline from end of the string
            },
        }

        with create_driver(driver_path, chrome_options, sw_options) as driver:
            driver.get(f'{httpbin}/html')

            assert 'This passed through a authenticated http proxy' in driver.page_source


def test_upstream_socks_proxy(driver_path, chrome_options, httpbin, socksproxy):
    """Note that authenticated socks proxy is not supported by mitmproxy currently
    so we're only able to test unauthenticated.
    """
    sw_options = {'proxy': {'https': f'{socksproxy}'}}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert 'This passed through a socks proxy' in driver.page_source


def test_bypass_upstream_proxy_when_target_http(driver_path, chrome_options, httpproxy):
    sw_options = {'proxy': {'https': f'{httpproxy}', 'no_proxy': 'localhost:9091'}}

    with create_httpbin(port=9091, use_https=False) as httpbin:
        with create_driver(driver_path, chrome_options, sw_options) as driver:
            driver.get(f'{httpbin}/html')  # Scheme is http://

            assert 'Moby-Dick' in driver.page_source
            assert 'This passed through a http proxy' not in driver.page_source


def test_bypass_upstream_proxy_when_target_https(driver_path, chrome_options, httpbin, httpproxy):
    sw_options = {'proxy': {'https': f'{httpproxy}', 'no_proxy': 'localhost:8085'}}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')  # Scheme is https://

        assert 'Moby-Dick' in driver.page_source
        assert 'This passed through a http proxy' not in driver.page_source


def test_upstream_http_proxy_env_var(driver_path, chrome_options, httpbin, httpproxy):
    with patch.dict(os.environ, {'HTTPS_PROXY': f'{httpproxy}'}):
        with create_driver(driver_path, chrome_options) as driver:
            driver.get(f'{httpbin}/html')

            assert 'This passed through a http proxy' in driver.page_source


def test_no_auto_config(driver_path, chrome_options, httpbin):
    sw_options = {'auto_config': False}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert not driver.requests


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

    with create_driver(
        driver_path,
        chrome_options,
        sw_options,
        capabilities,
    ) as driver:

        driver.get(f'{httpbin}/html')
        driver.wait_for_request('/html')


def test_exclude_hosts(driver_path, chrome_options, httpbin):
    httpbin2 = testutils.get_httpbin(port=8090)
    sw_options = {'exclude_hosts': ['<-loopback>', 'localhost:8085']}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')
        driver.get(f'{httpbin2}/html')

        assert len(driver.requests) == 1
        assert driver.requests[0].url == f'{httpbin2}/html'


@pytest.mark.skip("Fails on GitHub Actions - chromedriver threads timeout")
def test_multiple_threads(driver_path, chrome_options, httpbin):
    num_threads = 5
    threads, results = [], []

    def run_driver():
        with create_driver(driver_path, chrome_options) as driver:
            driver.get(f'{httpbin}/html')
            request = driver.wait_for_request('/html')
            results.append(request)

    for i in range(num_threads):
        t = threading.Thread(name=f'Driver thread {i + 1}', target=run_driver)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    assert len(results) == num_threads


def test_ignore_http_methods(driver_path, chrome_options, httpbin):
    sw_options = {'ignore_http_methods': ['GET']}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert not driver.requests


def test_address_in_use(driver_path, chrome_options, httpbin):
    sw_options = {
        'addr': '127.0.0.1',
        'port': 8089,
    }

    with create_driver(driver_path, chrome_options, sw_options):
        with pytest.raises(ServerException, match='.*Address already in use.*'):
            with create_driver(driver_path, chrome_options, sw_options):
                pass


def test_har(driver_path, chrome_options, httpbin):
    with create_driver(driver_path, chrome_options, {'enable_har': True}) as driver:
        driver.get(f'{httpbin}/html')

        har = json.loads(driver.har)

        assert har['log']['creator']['comment'] == f'Selenium Wire version {seleniumwire.__version__}'
        assert len(har['log']['entries']) == 1
        assert har['log']['entries'][0]['request']['url'] == f'{httpbin}/html'
        assert har['log']['entries'][0]['response']['status'] == 200


def test_disable_capture(driver_path, chrome_options, httpbin):
    sw_options = {'disable_capture': True}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert not driver.requests


def test_in_memory_storage(driver_path, chrome_options, httpbin):
    sw_options = {
        'request_storage': 'memory',
        'request_storage_base_dir': f'{tempfile.gettempdir()}/sw_memory',
        'enable_har': True,
    }

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')
        driver.get(f'{httpbin}/anything')

        assert not glob(os.path.join(driver.backend.storage.home_dir, 'storage*'))
        assert len(driver.requests) == 2
        assert driver.last_request.url == f'{httpbin}/anything'
        assert driver.wait_for_request('/anything')
        assert [r.url for r in driver.iter_requests()] == [f'{httpbin}/html', f'{httpbin}/anything']
        assert [e['request']['url'] for e in json.loads(driver.har)['log']['entries']] == [
            f'{httpbin}/html',
            f'{httpbin}/anything',
        ]
        assert driver.last_request.cert


def test_switch_proxy_on_the_fly(driver_path, chrome_options, httpbin, httpproxy):
    sw_options = {'proxy': {'https': f'{httpproxy}'}}

    with create_driver(driver_path, chrome_options, sw_options) as driver:
        driver.get(f'{httpbin}/html')

        assert 'This passed through a http proxy' in driver.page_source

        with create_httpproxy(port=8088, auth='test:test') as authproxy:
            driver.proxy = {'https': str(authproxy)}  # Switch the proxy on the same driver instance

            driver.get(f'{httpbin}/html')

            assert 'This passed through a authenticated http proxy' in driver.page_source

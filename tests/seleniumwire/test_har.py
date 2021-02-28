import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import seleniumwire
from seleniumwire.har import create_har_entry, generate_har


def test_create_har_entry():
    mock_flow = Mock()
    # Timings (using seconds here as using millis causes rounding issues with floats)
    # connect time = 2s
    # ssl time = 3s
    # send = 4s
    # receive = 3s
    # wait = 2s
    # full = 14s
    start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    mock_flow.server_conn.timestamp_start = start.timestamp()
    mock_flow.server_conn.timestamp_tcp_setup = (start + timedelta(seconds=2)).timestamp()
    mock_flow.server_conn.timestamp_tls_setup = (start + timedelta(seconds=5)).timestamp()
    req_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    mock_flow.request.timestamp_start = req_start.timestamp()
    mock_flow.request.timestamp_end = (req_start + timedelta(seconds=4)).timestamp()
    res_start = req_start + timedelta(seconds=6)
    mock_flow.response.timestamp_start = res_start.timestamp()
    mock_flow.response.timestamp_end = (res_start + timedelta(seconds=3)).timestamp()

    # Request attributes
    mock_flow.request.method = 'POST'
    mock_flow.request.url = 'https://www.somewhere.com/some/path?foo=bar'
    mock_flow.request.http_version = '1.1'
    mock_flow.request.cookies.fields = [
        ('test_req_cookie', 'c_val1'),
        ('path', '/'),
        ('expires', f'{start.timestamp()}')
    ]
    mock_flow.request.headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'test-header-2': 'bar'
    }
    mock_flow.request.query = {'foo': 'bar'}
    mock_flow.request.urlencoded_form.items.return_value = [('a', 'b'), ('c', 'd')]
    mock_flow.request.get_text.return_value = 'a=b&c=d'
    mock_flow.request.content = b'a=b&c=d'

    # Response attributes
    mock_flow.response.status_code = 200
    mock_flow.response.reason = 'OK'
    mock_flow.response.http_version = '1.1'
    mock_flow.response.cookies.fields = [
        ('test_res_cookie', ('test', {'path': '/'}))
    ]
    mock_flow.response.headers = {'Content-Type': 'text/plain', 'Location': 'test_location'}
    mock_flow.response.raw_content = b'compressed'
    mock_flow.response.content = b'helloworld12345'
    mock_flow.response.get_text.return_value = 'helloworld12345'

    mock_flow.server_conn.ip_address = ('10.10.10.1', )

    entry = create_har_entry(mock_flow)

    assert entry['startedDateTime'] == req_start.isoformat()
    assert entry['time'] == 14000
    assert entry['request']['method'] == 'POST'
    assert entry['request']['url'] == 'https://www.somewhere.com/some/path?foo=bar'
    assert entry['request']['httpVersion'] == '1.1'
    assert entry['request']['cookies'] == [{
        'name': 'test_req_cookie',
        'value': 'c_val1',
        'path': '/',
        'httpOnly': False,
        'secure': False
    }]
    assert entry['request']['headers'] == [
        {'name': 'Content-Type', 'value': 'application/x-www-form-urlencoded'},
        {'name': 'test-header-2', 'value': 'bar'},
    ]
    assert entry['request']['queryString'] == [
        {'name': 'foo', 'value': 'bar'},
    ]
    assert entry['request']['headersSize'] == 77
    assert entry['request']['bodySize'] == 7
    assert entry['request']['postData']['mimeType'] == 'application/x-www-form-urlencoded'
    assert entry['request']['postData']['text'] == 'a=b&c=d'
    assert entry['request']['postData']['params'] == [
        {'name': 'a', 'value': 'b'},
        {'name': 'c', 'value': 'd'}
    ]
    assert entry['response']['status'] == 200
    assert entry['response']['statusText'] == 'OK'
    assert entry['response']['httpVersion'] == '1.1'
    assert entry['response']['cookies'] == [{
        'name': 'test_res_cookie',
        'value': 'test',
        'path': '/',
        'httpOnly': False,
        'secure': False
    }]
    assert entry['response']['headers'] == [
        {'name': 'Content-Type', 'value': 'text/plain'},
        {'name': 'Location', 'value': 'test_location'},
    ]
    assert entry['response']['content']['size'] == 10
    assert entry['response']['content']['compression'] == 5
    assert entry['response']['content']['mimeType'] == 'text/plain'
    assert entry['response']['content']['text'] == 'helloworld12345'
    assert entry['response']['redirectURL'] == 'test_location'
    assert entry['response']['headersSize'] == 59
    assert entry['response']['bodySize'] == 10
    assert entry['timings']['send'] == 4000
    assert entry['timings']['receive'] == 3000
    assert entry['timings']['wait'] == 2000
    assert entry['timings']['connect'] == 2000
    assert entry['timings']['ssl'] == 3000
    assert entry['serverIPAddress'] == '10.10.10.1'


def test_generate_har():
    entries = [
        {'name': 'entry1'},
        {'name': 'entry2'}
    ]

    har = generate_har(entries)
    har = json.loads(har)

    assert har['log']['creator']['name'] == 'Selenium Wire HAR dump'
    assert har['log']['creator']['comment'] == f'Selenium Wire version {seleniumwire.__version__}'
    assert len(har['log']['entries']) == 2
    assert [e['name'] for e in har['log']['entries']] == ['entry1', 'entry2']

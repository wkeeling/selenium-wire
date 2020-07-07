"""This module manages the integraton with mitmproxy."""

import logging
import socket
import subprocess
import time
from contextlib import closing

try:
    import mitmproxy
except ImportError:
    raise ImportError('mitmproxy not found. Install it with "pip install mitmproxy".')

from seleniumwire.proxy.handler import ADMIN_PATH, AdminMixin, CaptureMixin
from seleniumwire.proxy.modifier import RequestModifier
from seleniumwire.proxy.request import Request, Response
from seleniumwire.proxy.storage import RequestStorage
from seleniumwire.proxy.utils import get_upstream_proxy

DEFAULT_LISTEN_PORT = 9950


def start(host, port, options, timeout=10):
    """Start an instance of mitmproxy server in a subprocess.

    Args:
        host: The host running mitmproxy.
        port: The port mitmproxy will listen on.
        options: The selenium wire options.
        timeout: The number of seconds to wait for the server to start.
            Default 10 seconds.

    Returns: A MitmProxy object representing the server.
    Raises:
        TimeoutException: if the mitmproxy server did not start in the
            timout period.
    """
    port = port or DEFAULT_LISTEN_PORT

    proxy = subprocess.Popen([
        'mitmdump',
        '--set',
        f'listen_port={port}',
        '--set',
        'ssl_insecure={}'.format(str(options.get('verify_ssl', 'true')).lower()),
        '--set',
        'upstream_cert=false',
        '--set',
        'stream_websockets=true',
        '--set',
        'termlog_verbosity=error',
        '--set',
        'flow_detail=0',
        *_get_upstream_proxy_args(options),
        '-s',
        __file__
    ])

    start_time = time.time()

    while time.time() - start_time < timeout:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex((host, port)) == 0:
                return MitmProxy(host, port, proxy)
            time.sleep(0.5)

    raise TimeoutError('mitmproxy did not start within {} seconds'.format(timeout))


def _get_upstream_proxy_args(options):
    args = []
    proxy_config = get_upstream_proxy(options)

    http_proxy = proxy_config.get('http')
    https_proxy = proxy_config.get('https')
    conf = None

    if http_proxy and https_proxy:
        if http_proxy != https_proxy:
            raise ValueError('http and https proxy must be the same for the mitmproxy backend')

        conf = https_proxy
    elif http_proxy:
        conf = http_proxy
    elif https_proxy:
        conf = https_proxy

    if conf:
        scheme, username, password, hostport = conf

        args += [
            '--set',
            f'mode=upstream:{scheme}://{hostport}'
        ]

        if username and password:
            args += [
                '--set',
                f'upstream_auth={username}:{password}'
            ]

    return args


class RequestCapture(AdminMixin, CaptureMixin):
    """Mitmproxy add-on which provides request modification and capture.

    Clients do not import this class. Mitmproxy will automatically load it
    when this module is passed as a script to the mitmproxy subprocesss.
    """
    def __init__(self):
        self.options = None
        self.storage = None
        self.modifier = RequestModifier()
        self.scopes = []

    def initialise(self, options):
        self.options = options
        self.storage = RequestStorage(
            base_dir=options.get('request_storage_base_dir')
        )

        # The logging in this add-on is not controlled by the logging
        # in the selenium test because we're running in a subprocess.
        # For the time being, configure basic logging using a config option.
        logging.basicConfig(
            level=getattr(logging, options.get('mitmproxy_log_level', 'ERROR'))
        )

    def request(self, flow):
        if flow.request.url.startswith(ADMIN_PATH):
            self.handle_admin(flow)
        else:
            # Make any modifications to the original request
            self.modifier.modify(flow.request, path_attr='url')

            # Convert to one of our requests for handling
            request = self._create_request(flow)

            self.capture_request(request)
            flow.request.id = request.id

    def response(self, flow):
        if not hasattr(flow.request, 'id'):
            # Request was not stored
            return

        # Convert the implementation specific response to one of our responses
        # for handling.
        response = Response(
            status_code=flow.response.status_code,
            reason=flow.response.reason,
            headers=dict(flow.response.headers),
            body=flow.response.content
        )

        self.capture_response(flow.request.id, flow.request.url, response)

    def handle_admin(self, flow):
        request = self._create_request(flow)
        response = self.dispatch_admin(request)

        flow.response = mitmproxy.http.HTTPResponse.make(
            status_code=200,
            content=response.body,
            headers=dict((k, str(v).encode('utf-8')) for k, v in response.headers.items())
        )

    def _create_request(self, flow):
        request = Request(
            method=flow.request.method,
            path=flow.request.url,
            headers=dict(flow.request.headers),
            body=flow.request.content
        )

        return request


class MitmProxy:
    """Wrapper class that provides access to a running mitmproxy subprocess."""

    def __init__(self, host, port, proc):
        self.host = host
        self.port = port
        self.proc = proc

    def shutdown(self):
        self.proc.terminate()

    def __del__(self):
        self.shutdown()


addons = [
    RequestCapture()
]

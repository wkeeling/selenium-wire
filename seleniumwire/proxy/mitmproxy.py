"""This module manages the integraton with mitmproxy."""

import socket
import subprocess
import time
from contextlib import closing

try:
    import mitmproxy
except ImportError:
    raise ImportError('mitmproxy not found. Install it with "pip install mitmproxy".')

from seleniumwire.proxy.handler import AdminMixin, CaptureMixin
from seleniumwire.proxy.modifier import RequestModifier
from seleniumwire.proxy.request import Request, Response
from seleniumwire.proxy.storage import RequestStorage

DEFAULT_LISTEN_PORT = 9950


def run(host, port, options):
    """Create and run an instance of mitmproxy server in a subprocess.

    Args:
        host: The host running mitmproxy.
        port: The port mitmproxy will listen on.
        options: The selenium wire options.

    Returns: A MitmProxy object representing the running server.
    """
    proxy = subprocess.Popen([
        'mitmdump',
        '--set',
        'listen_port={}'.format(port or DEFAULT_LISTEN_PORT),
        '--set',
        'ssl_insecure={}'.format(str(options.get('verify_ssl', 'false')).lower()),
        '--set',
        'stream_websockets=true',
        '--set',
        'termlog_verbosity=error',
        '-s',
        __file__
    ])

    return MitmProxy(host, port, proxy)


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

    def request(self, flow):
        if flow.request.url.startswith('http://seleniumwire'):
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

    def wait(self, timeout=10):
        """Wait for mitmproxy server to start.

        Args:
            timeout: The number of seconds to wait for the server to start.
                Default 10 seconds.

        Raises:
            TimeoutException if the mitmproxy server did not start in the
                timout period.
        """
        start = time.time()

        while time.time() - start < timeout:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                if sock.connect_ex((self.host, self.port)) == 0:
                    return
                time.sleep(0.5)

        raise TimeoutError('mitmproxy did not start within {} seconds'.format(timeout))

    def shutdown(self):
        self.proc.terminate()

    def __del__(self):
        self.shutdown()


addons = [
    RequestCapture()
]

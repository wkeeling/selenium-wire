"""This module manages the integraton with mitmproxy.

DEPRECATED. The default backend now uses mitmproxy so this separate
add-on will be removed in a future release.
"""
import asyncio
import logging
import re

from seleniumwire.modifier import RequestModifier
from seleniumwire.request import Request, Response
from seleniumwire.storage import RequestStorage
from seleniumwire.utils import get_upstream_proxy, is_list_alike

try:
    import mitmproxy  # noqa:F401  # isort:skip
except ImportError as e:
    raise ImportError("To use the mitmproxy backend you must first "
                      "install mitmproxy with 'pip install mitmproxy'.") from e

from mitmproxy import addons, http  # isort:skip
from mitmproxy.exceptions import Timeout  # isort:skip
from mitmproxy.master import Master  # isort:skip
from mitmproxy.net.http.headers import Headers  # isort:skip
from mitmproxy.options import Options  # isort:skip
from mitmproxy.proxy.config import ProxyConfig  # isort:skip
from mitmproxy.proxy.server import ProxyServer  # isort:skip


logger = logging.getLogger(__name__)

DEFAULT_CONFDIR = '~/.mitmproxy'
DEFAULT_UPSTREAM_CERT = False
DEFAULT_STREAM_WEBSOCKETS = True


class CaptureMixin:
    """Mixin that handles the capturing of requests and responses.

    DEPRECATED.
    """

    def capture_request(self, request):
        """Capture a request and save the unique id associated with the
        captured request in the id field.

        If any modification rules are set, the request will be modified
        before capture.

        Args:
            request: The request to capture.
        Returns: The captured request id.
        """
        ignore_method = request.method in self.server.options.get(
            'ignore_http_methods', ['OPTIONS'])
        not_in_scope = not self.in_scope(self.server.scopes, request.url)
        if ignore_method or not_in_scope:
            logger.debug('Not capturing %s request: %s', request.method, request.url)
            return

        logger.info('Capturing request: %s', request.url)

        # Save the request to our storage
        self.server.storage.save_request(request)

    def capture_response(self, request_id, url, response):
        """Capture a response and its body that relate to a previous request.

        Args:
            request_id: The id of the original request.
            url: The request url.
            response: The response to capture.
        """
        logger.info('Capturing response: %s %s %s', url, response.status_code, response.reason)

        self.server.storage.save_response(request_id, response)

    def in_scope(self, scopes, url):
        if not scopes:
            return True
        elif not is_list_alike(scopes):
            scopes = [scopes]
        for scope in scopes:
            match = re.search(scope, url)
            if match:
                return True
        return False


class MitmProxyRequestHandler(CaptureMixin):
    """Mitmproxy add-on which provides request modification and capture.

    DEPRECATED.
    """

    def __init__(self, server):
        self.server = server

    def requestheaders(self, flow):
        # Requests that are being captured are not streamed.
        if self.in_scope(self.server.scopes, flow.request.url):
            flow.request.stream = False

    def request(self, flow):
        # Make any modifications to the original request
        # DEPRECATED. This will be replaced by request_interceptor
        self.server.modifier.modify_request(flow.request, bodyattr='raw_content')

        # Convert to one of our requests for handling
        request = self._create_request(flow)

        # Call the request interceptor if set
        if self.server.request_interceptor is not None:
            self.server.request_interceptor(request)

            if request.response:
                # The interceptor has created a response for us to send back immediately
                flow.response = http.HTTPResponse.make(
                    status_code=int(request.response.status_code),
                    content=request.response.body,
                    headers=[(k.encode('utf-8'), v.encode('utf-8')) for k, v in request.response.headers.items()]
                )
                return

            flow.request.method = request.method
            flow.request.url = request.url
            flow.request.headers = self._to_headers_obj(request.headers)
            flow.request.raw_content = request.body

        self.capture_request(request)
        if request.id is not None:  # Will not be None when captured
            flow.request.id = request.id

        # Could possibly use mitmproxy's 'anticomp' option instead of this
        if self.server.options.get('disable_encoding') is True:
            flow.request.headers['Accept-Encoding'] = 'identity'

    def response(self, flow):
        # Make any modifications to the response
        # DEPRECATED. This will be replaced by response_interceptor
        self.server.modifier.modify_response(flow.response, flow.request)

        if not hasattr(flow.request, 'id'):
            # Request was not stored
            return

        # Convert the mitmproxy specific response to one of our responses
        # for handling.
        response = Response(
            status_code=flow.response.status_code,
            reason=flow.response.reason,
            headers=[(k, v) for k, v in flow.response.headers.items(multi=True)],
            body=flow.response.raw_content
        )

        # Call the response interceptor if set
        if self.server.response_interceptor is not None:
            self.server.response_interceptor(self._create_request(flow, response), response)
            flow.response.status_code = response.status_code
            flow.response.reason = response.reason
            flow.response.headers = self._to_headers_obj(response.headers)
            flow.response.raw_content = response.body

        self.capture_response(flow.request.id, flow.request.url, response)

    def responseheaders(self, flow):
        # Responses that are being captured are not streamed.
        if self.in_scope(self.server.scopes, flow.request.url):
            flow.response.stream = False

    def _create_request(self, flow, response=None):
        request = Request(
            method=flow.request.method,
            url=flow.request.url,
            headers=[(k, v) for k, v in flow.request.headers.items()],
            body=flow.request.raw_content
        )
        request.response = response

        return request

    def _to_headers_obj(self, headers):
        return Headers([(k.encode('utf-8'), v.encode('utf-8')) for k, v in headers.items()])


class MitmProxy:
    """Run and manage a mitmproxy server instance.

    DEPRECATED.
    """

    def __init__(self, host, port, options):
        self.options = options

        # Used to stored captured requests
        self.storage = RequestStorage(
            base_dir=options.pop('request_storage_base_dir', None)
        )

        # Used to modify requests/responses passing through the server
        # DEPRECATED. Will be superceded by request/response interceptors.
        self.modifier = RequestModifier()

        # The scope of requests we're interested in capturing.
        self.scopes = []

        self.request_interceptor = None
        self.response_interceptor = None

        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

        # mitmproxy specific options
        mitmproxy_opts = Options(
            confdir=options.pop('mitm_confdir', DEFAULT_CONFDIR),
            listen_host=host,
            listen_port=port,
        )

        # Create an instance of the mitmproxy server
        self._master = Master(mitmproxy_opts)
        self._master.server = ProxyServer(ProxyConfig(mitmproxy_opts))
        self._master.addons.add(*addons.default_addons())
        self._master.addons.add(SendToLogger())
        self._master.addons.add(MitmProxyRequestHandler(self))

        # Update the options now all addons have been added
        mitmproxy_opts.update(
            ssl_insecure=options.get('verify_ssl', True),
            upstream_cert=DEFAULT_UPSTREAM_CERT,
            stream_websockets=DEFAULT_STREAM_WEBSOCKETS,
            **self._get_upstream_proxy_args(),
        )

        # Options that are prefixed mitm_ are passed through to mitmproxy
        mitmproxy_opts.update(**{k[5:]: v for k, v in options.items() if k.startswith('mitm_')})

    def serve_forever(self):
        """Run the server."""
        asyncio.set_event_loop(self._event_loop)
        self._master.run()

    def address(self):
        """Get a tuple of the address and port the mitmproxy server
        is listening on.
        """
        return self._master.server.address

    def shutdown(self):
        """Shutdown the server and perform any cleanup."""
        try:
            # Wait for any active requests to finish. This reduces the
            # probability of seeing shutdown errors in the console.
            self._master.server.wait_for_silence()
        except Timeout:
            pass
        self._master.shutdown()
        self.storage.cleanup()

    def _get_upstream_proxy_args(self):
        proxy_config = get_upstream_proxy(self.options)
        http_proxy = proxy_config.get('http')
        https_proxy = proxy_config.get('https')
        conf = None

        if http_proxy and https_proxy:
            if http_proxy.hostport != https_proxy.hostport:
                # We only support a single upstream mitmproxy server
                raise ValueError('Cannot specify both http AND https '
                                 'mitmproxy settings with mitmproxy backend')

            conf = https_proxy
        elif http_proxy:
            conf = http_proxy
        elif https_proxy:
            conf = https_proxy

        args = {}

        if conf:
            scheme, username, password, hostport = conf

            args['mode'] = 'upstream:{}://{}'.format(scheme, hostport)

            if username:
                args['upstream_auth'] = '{}:{}'.format(username, password)

        return args


class SendToLogger:

    def log(self, entry):
        """Send a mitmproxy log message through our own logger."""
        getattr(logger, entry.level.replace('warn', 'warning'), logger.info)(entry.msg)

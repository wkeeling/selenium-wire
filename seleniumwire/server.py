import asyncio
import logging

from seleniumwire.handler import InterceptRequestHandler
from seleniumwire.modifier import RequestModifier
from seleniumwire.storage import RequestStorage
from seleniumwire.thirdparty.mitmproxy import addons
from seleniumwire.thirdparty.mitmproxy.master import Master
from seleniumwire.thirdparty.mitmproxy.options import Options
from seleniumwire.thirdparty.mitmproxy.server import ProxyConfig, ProxyServer
from seleniumwire.utils import extract_cert_and_key, get_upstream_proxy

logger = logging.getLogger(__name__)

DEFAULT_STREAM_WEBSOCKETS = True


class MitmProxy:
    """Run and manage a mitmproxy server instance."""

    def __init__(self, host, port, options):
        self.options = options

        # Used to stored captured requests
        self.storage = RequestStorage(base_dir=options.pop('request_storage_base_dir', None))
        extract_cert_and_key(self.storage.home_dir)

        # Used to modify requests/responses passing through the server
        # DEPRECATED. Will be superceded by request/response interceptors.
        self.modifier = RequestModifier()

        # The scope of requests we're interested in capturing.
        self.scopes = []

        self.request_interceptor = None
        self.response_interceptor = None

        self._event_loop = asyncio.new_event_loop()

        # mitmproxy specific options
        mitmproxy_opts = Options(
            confdir=self.storage.home_dir,
            listen_host=host,
            listen_port=port,
        )

        # Create an instance of the mitmproxy server
        self._master = Master(self._event_loop, mitmproxy_opts)
        self._master.server = ProxyServer(ProxyConfig(mitmproxy_opts))
        self._master.addons.add(*addons.default_addons())
        self._master.addons.add(SendToLogger())
        self._master.addons.add(InterceptRequestHandler(self))

        # Update the options now all addons have been added
        mitmproxy_opts.update(
            ssl_insecure=options.get('verify_ssl', True),
            stream_websockets=DEFAULT_STREAM_WEBSOCKETS,
            suppress_connection_errors=options.get('suppress_connection_errors', True),
            **self._get_upstream_proxy_args(),
        )

        if options.get('disable_capture', False):
            self.scopes = ['$^']

        # Options that are prefixed mitm_ are passed through to mitmproxy
        mitmproxy_opts.update(**{k[5:]: v for k, v in options.items() if k.startswith('mitm_')})

    def serve_forever(self):
        """Run the server."""
        asyncio.set_event_loop(self._event_loop)
        self._master.run_loop(self._event_loop)

    def address(self):
        """Get a tuple of the address and port the proxy server
        is listening on.
        """
        return self._master.server.address

    def shutdown(self):
        """Shutdown the server and perform any cleanup."""
        self._master.shutdown()
        self.storage.cleanup()

    def _get_upstream_proxy_args(self):
        proxy_config = get_upstream_proxy(self.options)
        http_proxy = proxy_config.get('http')
        https_proxy = proxy_config.get('https')
        conf = None

        if http_proxy and https_proxy:
            if http_proxy.hostport != https_proxy.hostport:
                # We only support a single upstream proxy server
                raise ValueError('Different settings for http and https proxy servers not supported')

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

            custom_auth = proxy_config.get('custom_authorization')

            if custom_auth:
                args['upstream_custom_auth'] = custom_auth

            no_proxy = proxy_config.get('no_proxy')

            if no_proxy:
                args['no_proxy'] = no_proxy

        return args


class SendToLogger:
    def log(self, entry):
        """Send a mitmproxy log message through our own logger."""
        getattr(logger, entry.level.replace('warn', 'warning'), logger.info)(entry.msg)

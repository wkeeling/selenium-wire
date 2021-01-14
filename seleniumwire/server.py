import asyncio
import logging

from seleniumwire.handler import MitmProxyRequestHandler
from seleniumwire.thirdparty.mitmproxy import addons
from seleniumwire.thirdparty.mitmproxy.exceptions import Timeout
from seleniumwire.thirdparty.mitmproxy.master import Master
from seleniumwire.thirdparty.mitmproxy.options import Options
from seleniumwire.thirdparty.mitmproxy.server import ProxyConfig, ProxyServer
from seleniumwire.storage import RequestStorage
from seleniumwire.utils import get_upstream_proxy

logger = logging.getLogger(__name__)

DEFAULT_CONFDIR = '~/.mitmproxy'
DEFAULT_UPSTREAM_CERT = False
DEFAULT_STREAM_WEBSOCKETS = True


class MitmProxy:
    """Run and manage a mitmproxy server instance."""

    def __init__(self, host, port, options):
        self.options = options

        # Used to stored captured requests
        self.storage = RequestStorage(
            base_dir=options.pop('request_storage_base_dir', None)
        )

        # The scope of requests we're interested in capturing.
        self.scopes = []

        self.request_interceptor = None
        self.response_interceptor = None

        self._event_loop = asyncio.get_event_loop()

        if self._event_loop.is_closed():
            # The event loop may be closed if the server had previously
            # been shutdown and then spun up again
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

        # mitmproxy specific options
        mitmproxy_opts = Options(
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
            confdir=DEFAULT_CONFDIR,
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
        self._master.run_loop(self._event_loop.run_forever)

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

            if username and password:
                args['upstream_auth'] = '{}:{}'.format(username, password)

        return args


class SendToLogger:

    def log(self, entry):
        """Send a mitmproxy log message through our own logger."""
        getattr(logger, entry.level, logger.info)(entry.msg)

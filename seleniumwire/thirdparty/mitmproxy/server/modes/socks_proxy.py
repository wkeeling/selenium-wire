from collections import namedtuple

from seleniumwire.thirdparty.mitmproxy import connections
from seleniumwire.thirdparty.mitmproxy.server import protocol


class SocksUpstreamProxy(protocol.Layer, protocol.ServerConnectionMixin):

    def __init__(self, ctx, upstream_server, upstream_auth):
        super().__init__(ctx)
        self.server_conn = self._make_connection(upstream_server, upstream_auth)

    def _make_connection(self, upstream_server, upstream_auth):
        socks_config = self._create_socks_config(upstream_server, upstream_auth)

        if self.config.options.spoof_source_address and self.config.options.upstream_bind_address == '':
            return connections.SocksServerConnection(
                socks_config, None, (self.ctx.client_conn.address[0], 0), True)
        else:
            return connections.SocksServerConnection(
                socks_config, None, (self.config.options.upstream_bind_address, 0),
                self.config.options.spoof_source_address
            )

    def _create_socks_config(self, upstream_server, upstream_auth):
        scheme, (host, port) = upstream_server
        username, password = None, None

        if upstream_auth is not None:
            username, password = upstream_auth.split(':')

        socksconfig = namedtuple(
            'SocksConfig', 'scheme address port username password'
        )
        config = socksconfig(
            scheme,
            host,
            port,
            username,
            password,
        )

        return config

    def __call__(self):
        layer = self.ctx.next_layer(self)
        try:
            layer()
        finally:
            if self.server_conn.connected():
                self.disconnect()

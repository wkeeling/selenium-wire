import re
import typing
import base64

from seleniumwire.thirdparty.mitmproxy import exceptions
from seleniumwire.thirdparty.mitmproxy import ctx
from seleniumwire.thirdparty.mitmproxy.utils import strutils


def parse_upstream_auth(auth):
    pattern = re.compile(".+:")
    if pattern.search(auth) is None:
        raise exceptions.OptionsError(
            "Invalid upstream auth specification: %s" % auth
        )
    return b"Basic" + b" " + base64.b64encode(strutils.always_bytes(auth))


class UpstreamAuth:
    """
        This addon handles authentication to systems upstream from us for the
        upstream proxy and reverse proxy mode. There are 4 cases:

        - Upstream proxy CONNECT requests should have authentication added, and
          subsequent already connected requests should not.
        - Upstream proxy regular requests
        - Reverse proxy regular requests (CONNECT is invalid in this mode)
        - Upstream SOCKS proxy requests (CONNECT is invalid in this mode)
    """
    def __init__(self):
        self.auth = None

    def load(self, loader):
        loader.add_option(
            "upstream_auth", typing.Optional[str], None,
            """
            Add HTTP Basic authentication to upstream proxy and reverse proxy
            requests. Format: username:password.
            """
        )

        loader.add_option(
            "upstream_custom_auth", typing.Optional[str], None,
            """
            Add custom authentication to upstream proxy requests by supplying
            the full value of the Proxy-Authorization header. 
            Format: <type> <credentials> - e.g. "Bearer mytoken123"
            """
        )

    def configure(self, updated):
        # FIXME: We're doing this because our proxy core is terminally confused
        # at the moment. Ideally, we should be able to check if we're in
        # reverse proxy mode at the HTTP layer, so that scripts can put the
        # proxy in reverse proxy mode for specific requests.
        if "upstream_custom_auth" in updated:
            if ctx.options.upstream_custom_auth is None:
                self.auth = None
            elif "socks" not in ctx.options.mode:
                self.auth = ctx.options.upstream_custom_auth
        elif "upstream_auth" in updated:
            if ctx.options.upstream_auth is None:
                self.auth = None
            elif "socks" not in ctx.options.mode:
                self.auth = parse_upstream_auth(ctx.options.upstream_auth)

    def http_connect(self, f):
        if self.auth and f.mode == "upstream":
            f.request.headers["Proxy-Authorization"] = self.auth

    def requestheaders(self, f):
        if self.auth:
            if f.mode == "upstream" and not f.server_conn.via:
                f.request.headers["Proxy-Authorization"] = self.auth
            elif ctx.options.mode.startswith("reverse"):
                f.request.headers["Proxy-Authorization"] = self.auth

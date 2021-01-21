from seleniumwire.thirdparty.mitmproxy.addons import core
from seleniumwire.thirdparty.mitmproxy.addons import streambodies
from seleniumwire.thirdparty.mitmproxy.addons import upstream_auth


def default_addons():
    return [
        core.Core(),
        streambodies.StreamBodies(),
        upstream_auth.UpstreamAuth(),
    ]

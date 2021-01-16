from seleniumwire.thirdparty.mitmproxy.addons import core
from seleniumwire.thirdparty.mitmproxy.addons import streambodies


def default_addons():
    return [
        core.Core(),
        streambodies.StreamBodies(),
    ]

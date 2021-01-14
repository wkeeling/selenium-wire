from seleniumwire.thirdparty.mitmproxy.addons import streambodies


def default_addons():
    return [
        streambodies.StreamBodies(),
    ]

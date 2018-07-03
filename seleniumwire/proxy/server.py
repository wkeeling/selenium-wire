import threading

from seleniumwire.proxy.handler import CaptureRequestHandler
from seleniumwire.proxy.proxy2 import ThreadingHTTPServer
from seleniumwire.proxy.storage import RequestStorage


class ProxyHTTPServer(ThreadingHTTPServer):

    def server_activate(self):
        # Each server instance gets its own storage
        self.storage = RequestStorage()
        super().server_activate()

    @staticmethod
    def start(host='localhost', port=0):
        CaptureRequestHandler.protocol_version = 'HTTP/1.1'
        proxy = ProxyHTTPServer((host, port), CaptureRequestHandler)

        t = threading.Thread(name='Selenium Wire Proxy Server', target=proxy.serve_forever)
        t.daemon = True
        t.start()

        # proxy_host = self._proxy.socket.gethostname()
        proxy_port = proxy.socket.getsockname()[1]

        return host, proxy_port


if __name__ == '__main__':
    ProxyHTTPServer.start(port=8080)

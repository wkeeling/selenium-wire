"""This module manages the integraton with mitmproxy."""

import logging
import subprocess


try:
    import mitmproxy
except ImportError:
    raise ImportError('mitmproxy not found. Install it with "pip install mitmproxy".')

from .handler import AdminMixin, CaptureMixin

log = logging.getLogger(__name__)


def run(port, options):
    """Create and run an instance of mitmproxy server in a subprocess.

    Returns: A MitmProxy object representing the running server.
    """
    assert port, 'You must pass a port number when running a mitmproxy backend.'

    proxy = subprocess.Popen([
        'mitmdump',
        '--set',
        'listen_port={}'.format(port),
        '--set',
        'ssl_insecure={}'.format(str(options.get('verify_ssl', 'false')).lower())
    ])

    return MitmProxy(proxy, port)


# def _create_master(request_capture, created_callback):
#     """Closure function that allows the SeleniumWireDumpMaster access to the
#     selenium wire options and callback.
#     """
#
#     class SeleniumWireDumpMaster(DumpMaster):
#         def __init__(self, options):
#             options.set('listen_port=0')
#             super().__init__(options, with_termlog=False, with_dumper=False)
#             self.addons.add(
#                 RequestCapture()
#             )
#
#         def run(self, func=None):
#             super().run(func)
#             created_callback(MitmProxy(self))
#
#     return SeleniumWireDumpMaster


class RequestCapture(AdminMixin, CaptureMixin):

    def __init__(self):
        self.num = 0

    def request(self, flow):
        self.num = self.num + 1
        print("We've seen %d flows" % self.num)


class MitmProxy:
    """Wrapper class that provides access to a running mitmproxy subprocess."""

    def __init__(self, proc, port):
        self.proc = proc
        self.port = port

    def shutdown(self):
        self.proc.terminate()

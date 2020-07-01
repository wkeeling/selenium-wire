"""This module manages the integraton with mitmproxy."""

import threading


try:
    import mitmproxy
except ImportError:
    raise ImportError('mitmproxy not found. Install it with "pip install mitmproxy".')

from mitmproxy.tools import cmdline
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.tools.main import run as run_mitm

from .handler import AdminMixin, CaptureMixin


def run(sw_options, created_callback):
    """Create and run an instance of mitmproxy server.

    Args:
        sw_options: The selenium wire options.
        created_callback: A function that will be called when the mitmproxy
            server has started. It will receive an instance of the MitmProxy
            class which represents the running server.
    """
    def extra(args):
        if args.filter_args:
            v = " ".join(args.filter_args)
            return dict(
                save_stream_filter=v,
                readfile_filter=v,
                dumper_filter=v,
            )
        return {}

    run_mitm(
        master_cls=_create_master(sw_options, created_callback),
        make_parser=cmdline.mitmdump,
        arguments=[],
        extra=extra
    )


def _create_master(request_capture, created_callback):
    """Closure function that allows the SeleniumWireDumpMaster access to the
    selenium wire options and callback.
    """

    class SeleniumWireDumpMaster(DumpMaster):
        def __init__(self, options):
            options.set('listen_port=0')
            super().__init__(options, with_termlog=False, with_dumper=False)
            self.addons.add(
                RequestCapture()
            )

        def run(self, func=None):
            super().run(func)
            created_callback(MitmProxy(self))

    return SeleniumWireDumpMaster


class RequestCapture(AdminMixin, CaptureMixin):

    def __init__(self):
        self.num = 0

    def request(self, flow):
        self.num = self.num + 1
        print("We've seen %d flows" % self.num)


class MitmProxy:
    """Wrapper class that provides access to a running mitmproxy instance."""

    def __init__(self, dump_master):
        self._dump_master = dump_master

    def port(self):
        return self._dump_master.server.socket.getsockname()[1]

    def shutdown(self):
        self._dump_master.shutdown()

    server_close = shutdown


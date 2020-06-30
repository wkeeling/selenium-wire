import threading


try:
    import mitmproxy
except ImportError:
    raise ImportError('mitmproxy not found. Install it with "pip install mitmproxy".')

from mitmproxy.tools import cmdline
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.tools.main import run

from .handler import AdminMixin, CaptureMixin


def create_master(sw_options, upstream_proxy):

    class SeleniumWireDumpMaster(DumpMaster):
        def __init__(self, options):
            options.set('listen_port=0')
            super().__init__(options, with_termlog=False, with_dumper=False)
            self.addons.add(
                RequestCaptureAddon()
            )

        def run(self, func=None):
            print('Port is', self.server.socket.getsockname()[1])
            super().run(func)

    return SeleniumWireDumpMaster


class RequestCaptureAddon(AdminMixin, CaptureMixin):

    def __init__(self):
        self.num = 0

    def request(self, flow):
        self.num = self.num + 1
        print("We've seen %d flows" % self.num)


def create(sw_options, upstream_proxy):
    args = []

    def extra(args):
        if args.filter_args:
            v = " ".join(args.filter_args)
            return dict(
                save_stream_filter=v,
                readfile_filter=v,
                dumper_filter=v,
            )
        return {}

    run(create_master(sw_options, upstream_proxy), cmdline.mitmdump, args, extra)

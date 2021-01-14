import logging
import threading

from seleniumwire.server import MitmProxy

log = logging.getLogger(__name__)

DEFAULT_BACKEND = 'default'


def create(addr='127.0.0.1', port=0, options=None):
    """Create a new mitmproxy backend.

    The type of backend created depends on the 'backend' option. Supported types
    are 'default' and 'mitmproxy'. When not specified, the default backend will
    be used. The mitmproxy backend is dependent on the mitmproxy package being
    installed.

    Args:
        addr: The address the mitmproxy server will listen on. Default 127.0.0.1.
        port: The port the mitmproxy server will listen on. Default 0 - which means
            use the first available port.
        options: Additional options to configure the mitmproxy.

    Returns:
        An instance of the mitmproxy backend.
    """
    if options is None:
        options = {}

    backend = options.get('backend', DEFAULT_BACKEND)

    if backend == DEFAULT_BACKEND:
        # Use the default backend
        proxy = MitmProxy(addr, port, options)
    elif backend == 'mitmproxy':
        # Use mitmproxy if installed
        from . import mitmproxy

        proxy = mitmproxy.MitmProxy(addr, port, options)
    else:
        raise TypeError(
            "Invalid backend '{}'. "
            "Valid values are 'default' or 'mitmproxy'."
            .format(options['backend'])
        )

    t = threading.Thread(name='Selenium Wire Proxy Server', target=proxy.serve_forever)
    t.daemon = not options.get('standalone')
    t.start()

    log.info('Created mitmproxy listening on %s:%s', *proxy.address())

    return proxy

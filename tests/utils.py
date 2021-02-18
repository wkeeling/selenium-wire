import os
import shutil
import socket
import subprocess
from contextlib import closing
from pathlib import Path


def get_httpbin(port=8085):
    """Get a running httpbin server instance.

    This function will attempt to discover a httpbin server by trying each
    of the following steps in turn:

    - Check to see if anything is listening on the given port on localhost.
    If so, assume it's a httpbin server and return a Httpbin object containing
    the URL.

    - Attempt to start a local httpbin server on the given port and, if successful,
    return a Httpbin object containing the URL. This will only work for non-Windows
    hosts.

    - Return a Httpbin object containing the URL of the public httpbin website,
    https://httpbin.org

    Clients should call .close() on the returned Httpbin object when they are
    finished with it.

    Args:
        port: Optional port number that the httpbin instance is/should listen on.
    Returns:
        A Httpbin object containing the URL of the httpbin server.
    """
    url = f'https://localhost:{port}'

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(('localhost', port)) == 0:
            print(f'Using existing httpbin server at {url}')
            return Httpbin(url)

    if os.name != 'nt':  # Gunicorn doesn't work on Windows
        cert = Path(__file__).parent / 'server.crt'
        key = Path(__file__).parent / 'server.key'
        proc = subprocess.Popen([
            'gunicorn',
            f'--certfile={cert}',
            f'--keyfile={key}',
            '--bind',
            f'0.0.0.0:{port}',
            'httpbin:app',
        ],
            bufsize=0,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            proc.wait(timeout=2)
            # If we're here, wait() has returned meaning no process
            print(f'httpbin failed to start: {proc.stderr.read().decode()}')
        except subprocess.TimeoutExpired:
            # Server running
            print(f'Created new httpbin server at {url}')
            return Httpbin(url, proc)

    print('Using httpbin.org public website')
    return Httpbin('https://httpbin.org')


class Httpbin:
    """Represents a running httpbin server."""

    def __init__(self, url, proc=None):
        """Initialise a new Httpbin with a URL and optional Popen object.

        Args:
            url: The URL of the httpbin server.
            proc: The Popen object if a httpbin server was created.
        """
        self.url = url
        self.proc = proc

    def close(self):
        """Close any resources associated with the httpbin server."""
        if self.proc:
            self.proc.terminate()

    def __str__(self):
        return self.url


def get_headless_chromium():
    """Get the path to a headless chromium executable uncompressing the
    executable if required.

    Returns: The path.
    """
    bin_path = Path(__file__).parent / Path('end2end', 'linux', 'headless-chromium')

    if not bin_path.exists():
        zip_path = bin_path.with_suffix('.zip')
        print(f'Unzipping {zip_path}')
        shutil.unpack_archive(str(zip_path), bin_path.parent)
        os.chmod(bin_path, 0o755)

    return str(bin_path)


def get_proxy(port=8086, mode='http'):
    """Get a running proxy server instance.

    This function will return a Proxy object containing the URL of a running
    proxy server. The URL scheme is based on the supplied mode: 'http'
    (the default) and 'socks' are supported.

    Clients should call .close() on the returned Proxy object when they are
    finished with it.

    Args:
        port: Optional port number the proxy server should listen on.
        mode: Optional mode the proxy server will be started in.
        Either 'http' (the default) or 'socks'.
    Returns: A Proxy object containing the URL of the proxy server.
    """
    assert mode in ('http', 'socks'), "mode must be one of 'http' or 'socks'"

    mode_map = {
        'http': 'regular',
        'socks': 'socks5',
    }

    proc = subprocess.Popen([
        'mitmdump',
        '--listen-port',
        f'{port}',
        '--set',
        f'mode={mode_map[mode]}',
        '--set',
        'flow_detail=0',
        '--set',
        'ssl_insecure',
        '-s',
        Path(__file__).parent / f'inject_message.py',
        '--set',
        f'injectmode={mode}',
    ],
        bufsize=0,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        proc.wait(timeout=2)
        # If we're here, wait() has returned meaning no process
        raise RuntimeError(f'Proxy server failed to start: {proc.stderr.read().decode()}')
    except subprocess.TimeoutExpired:
        # Server running
        if mode == 'http':
            url = f'https://localhost:{port}'
        else:
            url = f'socks5://localhost:{port}'
        print(f'Created new proxy server at {url}')
        return Proxy(url, proc)


class Proxy:
    """Represents a running proxy server."""

    def __init__(self, url, proc):
        """Initialise a new Proxy with a URL and Popen object.

        Args:
            url: The URL of the proxy server.
            proc: The Popen object of the proxy server.
        """
        self.url = url
        self.proc = proc

    def close(self):
        """Close any resources associated with the proxy server."""
        self.proc.terminate()

    def __str__(self):
        return self.url


if __name__ == '__main__':
    get_httpbin()

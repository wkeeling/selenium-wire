import os
import socket
import subprocess
from contextlib import closing
from pathlib import Path


def get_httpbin(port=8085):
    """Get a Httpbin object containing the URL of a running
    httpbin server.

    This function will attempt to discover a httpbin server by
    trying each of the following steps in turn:

    - Check to see if anything is listening on the given port
    on localhost. If so, assume it's a httpbin server and
    return a Httpbin object containing the URL.

    - Attempt to start a local httpbin server on the given
    port and, if successful, return a Httpbin object
    containing the URL. This will only work for non-Windows
    hosts.

    - Return a Httpbin object containing the URL of the
    public httpbin website, i.e. https://httpbin.org

    Clients should call the close() method on the returned
    Httpbin object when they are finished with it.

    Args:
        port: Optional port number that the httpbin instance
        is/should listen on.
    Returns:
        A Httpbin object containing the URL of the httpbin
        server.
    """
    url = f'https://localhost:{port}'

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(('localhost', port)) == 0:
            print(f'Using existing httpbin server at {url}')
            return Httpbin(url)

    if os.name != 'nt':
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
        self.url = url
        self.proc = proc

    def close(self):
        """Close any resources associated with the httpbin server."""
        if self.proc:
            self.proc.terminate()

    def __str__(self):
        return self.url


if __name__ == '__main__':
    get_httpbin()

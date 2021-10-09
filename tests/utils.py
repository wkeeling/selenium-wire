import os
import shutil
import subprocess
from pathlib import Path


class Httpbin:
    """Create and manage a httpbin server.

    Creating a new instance of this class will spawn a httpbin server
    in a subprocess. Clients should call the shutdown() method when they
    are finished with the server.

    Only compatible on non-Windows systems.
    """

    def __init__(self, port: int = 8085, use_https: bool = True):
        """Create a new httpbin server.

        Args:
            port:
                Optional port number that the httpbin instance should listen on.
            use_https:
                Whether the httpbin instance should use https. When True (the default)
                the httpbin instance will be addressable as 'https://' otherwise 'http://'.
        """
        scheme = 'https' if use_https else 'http'
        self.url = f'{scheme}://localhost:{port}'

        # Gunicorn doesn't work on Windows
        assert os.name != 'nt', 'The httpbin utility does not run on Windows'

        args = [
            'gunicorn',
            '--bind',
            f'0.0.0.0:{port}',
        ]

        if use_https:
            cert = Path(__file__).parent / 'server.crt'
            key = Path(__file__).parent / 'server.key'
            args.append(f'--certfile={cert}')
            args.append(f'--keyfile={key}')

        args.append('httpbin:app')

        self.proc = subprocess.Popen(args, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            self.proc.wait(timeout=2)
            # If we're here, wait() has returned meaning no process
            raise RuntimeError(f'httpbin failed to start: {self.proc.stderr.read().decode()}')
        except subprocess.TimeoutExpired:
            # Server running
            print(f'Created new httpbin server at {self.url}')

    def shutdown(self):
        """Shutdownthe httpbin server."""
        if self.proc:
            self.proc.terminate()

    def __str__(self):
        return self.url


def get_headless_chromium() -> str:
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


class Proxy:
    """Create and manage a mitmdump proxy server.

    The proxy supports two URL schemes which based on the supplied mode: 'http'
    (the default) and 'socks'.

    The proxy will modify HTML responses by adding a comment just before the
    closing </body> tag. The text of the comment will depend on what mode the
    proxy is running in and whether authentication has been specified, but will
    be one of:

        This passed through a http proxy
        This passed through a authenticated http proxy
        This passed through a socks proxy

    Note: authenticated socks proxy not currently supported by mitmdump.

    Clients should call the shutdown() method when they are finished with the
    server.
    """

    def __init__(self, port: int = 8086, mode: str = 'http', auth: str = ''):
        """Create a new mitmdump proxy server.

        Args:
            port: Optional port number the proxy server should listen on.
            mode: Optional mode the proxy server will be started in.
                Either 'http' (the default) or 'socks'.
            auth: When supplied, proxy authentication will be enabled.
                The value should be a string in the format: 'username:password'
        """
        assert mode in ('http', 'socks'), "mode must be one of 'http' or 'socks'"

        mode_map = {
            'http': 'regular',
            'socks': 'socks5',
        }

        auth_args = ['--set', f'proxyauth={auth}'] if auth else []

        message = f"This passed through a {'authenticated ' if auth else ''}{mode} proxy"

        self.proc = subprocess.Popen(
            [
                'mitmdump',
                '--listen-port',
                f'{port}',
                '--set',
                f'mode={mode_map[mode]}',
                '--set',
                'flow_detail=0',
                '--set',
                'ssl_insecure',
                *auth_args,
                '-s',
                Path(__file__).parent / 'inject_message.py',
                '--set',
                f'message={message}',
            ],
            bufsize=0,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            self.proc.wait(timeout=2)
            # If we're here, wait() has returned meaning no process
            raise RuntimeError(f'Proxy server failed to start: {self.proc.stderr.read().decode()}')
        except subprocess.TimeoutExpired:
            # Server running
            if auth:
                auth = f'{auth}@'
            if mode == 'http':
                self.url = f'https://{auth}localhost:{port}'
            else:
                self.url = f'socks5://{auth}localhost:{port}'
            print(f'Created new proxy server at {self.url}')

    def shutdown(self):
        """Shutdown the proxy server."""
        self.proc.terminate()

    def __str__(self):
        return self.url

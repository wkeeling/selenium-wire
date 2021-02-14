import subprocess
from pathlib import Path


def start_httpbin(port=8085):
    """Start a httpbin server and return a Popen object that
    can be used to manage the server instance.

    Args:
        port: Optional port number the server should run on.
    Returns: A Popen object.
    """
    cert = Path(__file__).parent / 'server.crt'
    key = Path(__file__).parent / 'server.key'
    proc = subprocess.Popen([
        'gunicorn',
        f'--certfile={cert}',
        f'--keyfile={key}',
        '--bind',
        f'0.0.0.0:{port}',
        'httpbin:app',
    ], bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        proc.wait(timeout=2)
        # wait() has returned indicating there's no process
        raise RuntimeError(f'httpbin failed to start: {proc.stderr.read().decode()}')
    except subprocess.TimeoutExpired:
        # Server running
        return proc


if __name__ == '__main__':
    start_httpbin()

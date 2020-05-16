# -*- coding: utf-8 -*-

#
#
# This code is from the project https://github.com/inaz2/proxy2, with some
# minor modifications.
#
#

import base64
import re
import socket
import ssl
import sys
import threading
import urllib.parse
from http.client import HTTPConnection, HTTPSConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from . import cert, socks


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def handle_error(self, request, client_address):
        # surpress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if issubclass(cls, socket.error) or issubclass(cls, ssl.SSLError):
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    admin_path = 'http://proxy2'
    # Path to the directory used to store the generated certificates.
    # Subclasses can override certdir
    certdir = cert.CERTDIR

    def __init__(self, *args, **kwargs):
        self.tls = threading.local()
        self.tls.conns = {}

        super().__init__(*args, **kwargs)

    def log_error(self, format_, *args):
        # suppress "Request timed out: timeout('timed out',)"
        if isinstance(args[0], socket.timeout):
            return

        self.log_message(format_, *args)

    def do_CONNECT(self):
        self.send_response(200, 'Connection Established')
        self.end_headers()

        certpath = cert.generate(self.path.split(':')[0], self.certdir)

        with ssl.wrap_socket(self.connection, keyfile=cert.CERTKEY, certfile=certpath, server_side=True) as conn:
            self.connection = conn
            self.rfile = conn.makefile('rb', self.rbufsize)
            self.wfile = conn.makefile('wb', self.wbufsize)

        conntype = self.headers.get('Proxy-Connection', '')
        if self.protocol_version == 'HTTP/1.1' and conntype.lower() != 'close':
            self.close_connection = False
        else:
            self.close_connection = True

    def do_GET(self):
        if self.path.startswith(self.admin_path):
            self.admin_handler()
            return
        req = self
        content_length = int(req.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length) if content_length else None

        if req.path[0] == '/':
            path = '{}{}'.format(req.headers['Host'], req.path)
            if isinstance(self.connection, ssl.SSLSocket):
                req.path = 'https://{}'.format(path)
            else:
                req.path = 'http://{}'.format(path)

        req_body_modified = self.request_handler(req, req_body)
        if req_body_modified is False:
            self.send_error(403)
            return
        elif req_body_modified is not None:
            req_body = req_body_modified
            del req.headers['Content-length']
            req.headers['Content-length'] = str(len(req_body))

        u = urllib.parse.urlsplit(req.path)
        scheme, netloc, path = u.scheme, u.netloc, (u.path + '?' + u.query if u.query else u.path)
        assert scheme in ('http', 'https')
        if netloc:
            req.headers['Host'] = netloc
        setattr(req, 'headers', self.filter_headers(req.headers))

        origin = (scheme, netloc)
        conn = None
        try:
            conn = self.create_connection(origin)
            conn.request(self.command, path, req_body, dict(req.headers))
            res = conn.getresponse()

            version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1'}
            setattr(res, 'headers', res.msg)
            setattr(res, 'response_version', version_table[res.version])

            res_body = res.read()
        except Exception:
            if origin in self.tls.conns:
                del self.tls.conns[origin]
            self.send_error(502)
            return
        finally:
            if conn:
                conn.close()

        res_body_modified = self.response_handler(req, req_body, res, res_body)
        if res_body_modified is False:
            self.send_error(403)
            return
        elif res_body_modified is not None:
            res_body = res_body_modified
            del res.headers['Content-length']
            res.headers['Content-Length'] = str(len(res_body))

        setattr(res, 'headers', self.filter_headers(res.headers))

        self.send_response(res.status, res.reason)

        for header, val in res.headers.items():
            self.send_header(header, val)
        self.end_headers()
        if res_body:
            self.wfile.write(res_body)
        self.wfile.flush()
        self.close_connection = True

    def create_connection(self, origin):
        scheme, netloc = origin

        if origin not in self.tls.conns:
            proxy_config = self.server.proxy_config

            kwargs = {
                'timeout': self.timeout
            }

            if scheme == 'https':
                connection = ProxyAwareHTTPSConnection
                if not self.server.options.get('verify_ssl', True):
                    kwargs['context'] = ssl._create_unverified_context()
            else:
                connection = ProxyAwareHTTPConnection

            self.tls.conns[origin] = connection(proxy_config, netloc, **kwargs)

        return self.tls.conns[origin]

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET
    do_PATCH = do_GET

    def filter_headers(self, headers):
        # http://tools.ietf.org/html/rfc2616#section-13.5.1
        hop_by_hop = ('connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
                      'transfer-encoding', 'upgrade')
        for k in hop_by_hop:
            del headers[k]

        # accept only supported encodings
        if 'Accept-Encoding' in headers:
            ae = headers['Accept-Encoding']

            if self.server.options.get('disable_encoding') is True:
                permitted_encodings = ('identity', )
            else:
                permitted_encodings = ('identity', 'gzip', 'x-gzip', 'deflate')

            filtered_encodings = [x for x in re.split(r',\s*', ae) if x in permitted_encodings]

            if not filtered_encodings:
                filtered_encodings.append('identity')

            del headers['Accept-Encoding']

            headers['Accept-Encoding'] = ', '.join(filtered_encodings)

        return headers

    def send_cacert(self):
        with open(cert.CACERT, 'rb') as f:
            data = f.read()

        self.send_response(200, 'OK')
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.send_header('Content-Length', len(data))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def request_handler(self, req, req_body):
        pass

    def response_handler(self, req, req_body, res, res_body):
        pass

    def admin_handler(self):
        if self.path == 'http://proxy2.test/':
            self.send_cacert()


class ProxyAwareHTTPConnection(HTTPConnection):
    """A specialised HTTPConnection that will transparently connect to a
    HTTP or SOCKS proxy server based on supplied proxy configuration.
    """

    def __init__(self, proxy_config, netloc, *args, **kwargs):
        self.proxy_config = proxy_config
        self.netloc = netloc
        self.use_proxy = 'http' in proxy_config and netloc not in proxy_config.get('no_proxy', '')

        if self.use_proxy and proxy_config['http'].scheme.startswith('http'):
            self.custom_authorization = proxy_config.get('custom_authorization')
            super().__init__(proxy_config['http'].hostport, *args, **kwargs)
        else:
            super().__init__(netloc, *args, **kwargs)

    def connect(self):
        if self.use_proxy and self.proxy_config['http'].scheme.startswith('socks'):
            self.sock = _socks_connection(
                self.host,
                self.port,
                self.timeout,
                self.proxy_config['http']
            )
        else:
            super().connect()

    def request(self, method, url, body=None, headers=None, *, encode_chunked=False):
        if headers is None:
            headers = {}

        if self.use_proxy and self.proxy_config['http'].scheme.startswith('http'):
            if not url.startswith('http'):
                url = 'http://{}{}'.format(self.netloc, url)

            headers.update(_create_auth_header(
                self.proxy_config['http'].username,
                self.proxy_config['http'].password,
                self.custom_authorization)
            )

        super().request(method, url, body, headers=headers)


class ProxyAwareHTTPSConnection(HTTPSConnection):
    """A specialised HTTPSConnection that will transparently connect to a
    HTTP or SOCKS proxy server based on supplied proxy configuration.
    """

    def __init__(self, proxy_config, netloc, *args, **kwargs):
        self.proxy_config = proxy_config
        self.use_proxy = 'https' in proxy_config and netloc not in proxy_config.get('no_proxy', '')

        if self.use_proxy and proxy_config['https'].scheme.startswith('http'):
            # For HTTP proxies, CONNECT tunnelling is used
            super().__init__(proxy_config['https'].hostport, *args, **kwargs)
            self.set_tunnel(
                netloc,
                headers=_create_auth_header(
                    proxy_config['https'].username,
                    proxy_config['https'].password,
                    proxy_config.get('custom_authorization')
                )
            )
        else:
            super().__init__(netloc, *args, **kwargs)

    def connect(self):
        if self.use_proxy and self.proxy_config['https'].scheme.startswith('socks'):
            self.sock = _socks_connection(
                self.host,
                self.port,
                self.timeout,
                self.proxy_config['https']
            )
            self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
        else:
            super().connect()


def _create_auth_header(proxy_username, proxy_password, custom_proxy_authorization):
    """Create the Proxy-Authorization header based on the supplied username
    and password or custom Proxy-Authorization header value.

    Args:
        proxy_username: The proxy username.
        proxy_password: The proxy password.
        custom_proxy_authorization: The custom proxy authorization.
    Returns:
        A dictionary containing the Proxy-Authorization header or an empty
        dictionary if the username or password were not set.
    """
    headers = {}

    if proxy_username and proxy_password and not custom_proxy_authorization:
        auth = '{}:{}'.format(proxy_username, proxy_password)
        headers['Proxy-Authorization'] = 'Basic {}'.format(base64.b64encode(auth.encode('utf-8')).decode('utf-8'))
    elif custom_proxy_authorization:
        headers['Proxy-Authorization'] = custom_proxy_authorization

    return headers


def _socks_connection(host, port, timeout, socks_config):
    """Create a SOCKS connection based on the supplied configuration."""
    try:
        socks_type = dict(
            socks4=socks.PROXY_TYPE_SOCKS4,
            socks5=socks.PROXY_TYPE_SOCKS5,
            socks5h=socks.PROXY_TYPE_SOCKS5
        )[socks_config.scheme]
    except KeyError:
        raise TypeError('Invalid SOCKS scheme: {}'.format(socks_config.scheme))

    socks_host, socks_port = socks_config.hostport.split(':')

    return socks.create_connection(
        (host, port),
        timeout,
        None,
        socks_type,
        socks_host,
        int(socks_port),
        socks_config.scheme == 'socks5h',
        socks_config.username,
        socks_config.password,
        ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),)
    )

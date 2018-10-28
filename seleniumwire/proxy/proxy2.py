# -*- coding: utf-8 -*-

#
#
# This code is from the project https://github.com/inaz2/proxy2, with some
# minor modifications.
#
#

import base64
import gzip
import html
import http.client
import json
import os
import re
import select
import socket
import ssl
import sys
import threading
import time
import urllib.parse
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from socketserver import ThreadingMixIn
from subprocess import PIPE, Popen


def with_color(c, s):
    return "\x1b[%dm%s\x1b[0m" % (c, s)


def join_with_script_dir(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def handle_error(self, request, client_address):
        # surpress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if cls is socket.error or cls is ssl.SSLError:
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    cakey = join_with_script_dir('ca.key')
    cacert = join_with_script_dir('ca.crt')
    certkey = join_with_script_dir('cert.key')
    certdir = join_with_script_dir('certs/')
    timeout = 5
    lock = threading.Lock()
    admin_path = 'http://proxy2'

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
        if os.path.isfile(self.cakey) and os.path.isfile(self.cacert) and os.path.isfile(self.certkey):
            self.connect_intercept()
        else:
            self.connect_relay()

    def connect_intercept(self):
        hostname = self.path.split(':')[0]
        certpath = "%s/%s.crt" % (self.certdir.rstrip('/'), hostname)

        with self.lock:
            os.makedirs(self.certdir, exist_ok=True)
            if not os.path.isfile(certpath):
                epoch = "%d" % (time.time() * 1000)

                new_cert_req = ["req", "-new", "-key", self.certkey, "-subj", "/CN=%s" % hostname]
                if os.name == 'nt':
                    openssl = os.path.join(os.path.dirname(__file__), 'win', 'openssl.exe')
                    new_cert_req += ['-config', os.path.join(os.path.dirname(__file__), 'win', 'openssl.cnf')]
                else:
                    openssl = 'openssl'
                new_cert_req.insert(0, openssl)

                p1 = Popen(new_cert_req, stdout=PIPE)
                p2 = Popen([openssl, "x509", "-req", "-days", "3650", "-CA", self.cacert, "-CAkey", self.cakey,
                            "-set_serial", epoch, "-out", certpath], stdin=p1.stdout, stderr=PIPE)
                p2.communicate()
                p1.communicate()

        self.send_response(200, 'Connection Established')
        self.end_headers()

        with ssl.wrap_socket(self.connection, keyfile=self.certkey, certfile=certpath, server_side=True) as conn:
            self.connection = conn
            self.rfile = conn.makefile("rb", self.rbufsize)
            self.wfile = conn.makefile("wb", self.wbufsize)

        conntype = self.headers.get('Proxy-Connection', '')
        if self.protocol_version == "HTTP/1.1" and conntype.lower() != 'close':
            self.close_connection = False
        else:
            self.close_connection = True

    def connect_relay(self):
        address = self.path.split(':', 1)
        address[1] = int(address[1]) or 443
        try:
            s = socket.create_connection(address, timeout=self.timeout)
        except Exception:
            self.send_error(502)
            return
        self.send_response(200, 'Connection Established')
        self.end_headers()

        conns = [self.connection, s]
        self.close_connection = False
        while not self.close_connection:
            rlist, wlist, xlist = select.select(conns, [], conns, self.timeout)
            if xlist or not rlist:
                break
            for r in rlist:
                other = conns[1] if r is conns[0] else conns[0]
                try:
                    data = r.recv(8192)
                except ConnectionError:
                    return
                if not data:
                    self.close_connection = True
                    break
                other.sendall(data)

    def do_GET(self):
        if self.path.startswith(self.admin_path):
            self.admin_handler()
            return
        req = self
        content_length = int(req.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length) if content_length else None

        if req.path[0] == '/':
            if isinstance(self.connection, ssl.SSLSocket):
                req.path = "https://%s%s" % (req.headers['Host'], req.path)
            else:
                req.path = "http://%s%s" % (req.headers['Host'], req.path)

        req_body_modified = self.request_handler(req, req_body)
        if req_body_modified is False:
            self.send_error(403)
            return
        elif req_body_modified is not None:
            req_body = req_body_modified
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

            # support streaming
            if 'Content-Length' not in res.headers and 'no-store' in res.headers.get('Cache-Control', ''):
                self.response_handler(req, req_body, res, '')
                setattr(res, 'headers', self.filter_headers(res.headers))
                self.relay_streaming(res)
                with self.lock:
                    self.save_handler(req, req_body, res, '')
                return

            res_body = res.read()
        except Exception:
            if origin in self.tls.conns:
                del self.tls.conns[origin]
            self.send_error(502)
            return
        finally:
            if conn:
                conn.close()

        content_encoding = res.headers.get('Content-Encoding', 'identity')
        res_body_plain = self.decode_content_body(res_body, content_encoding)

        res_body_modified = self.response_handler(req, req_body, res, res_body_plain)
        if res_body_modified is False:
            self.send_error(403)
            return
        elif res_body_modified is not None:
            res_body_plain = res_body_modified
            res_body = self.encode_content_body(res_body_plain, content_encoding)
            res.headers['Content-Length'] = str(len(res_body))

        setattr(res, 'headers', self.filter_headers(res.headers))

        self.send_response(res.status, res.reason)

        for header, val in res.headers.items():
            self.send_header(header, val)
        self.end_headers()
        if res_body:
            self.wfile.write(res_body)
        self.wfile.flush()

        with self.lock:
            self.save_handler(req, req_body, res, res_body_plain)

    def create_connection(self, origin):
        scheme, netloc = origin

        if origin not in self.tls.conns:
            # Attempt to connect to upstream proxy server
            proxy_config = self.server.proxy_config.get(scheme)
            if proxy_config and netloc not in self.server.proxy_config['no_proxy']:
                proxy_type, username, password, hostport = proxy_config
                headers = {}
                if username and password:
                    auth = '%s:%s' % (username, password)
                    headers['Proxy-Authorization'] = 'Basic ' + base64.b64encode(auth.encode('latin-1')).decode(
                        'latin-1')
                if proxy_type == 'https':
                    conn = http.client.HTTPSConnection(hostport, timeout=self.timeout)
                    conn.set_tunnel(netloc, headers=headers)
                else:
                    conn = http.client.HTTPConnection(hostport, timeout=self.timeout)

                self.tls.conns[origin] = conn

        if origin not in self.tls.conns:
            if scheme == 'https':
                self.tls.conns[origin] = http.client.HTTPSConnection(netloc, timeout=self.timeout)
            else:
                self.tls.conns[origin] = http.client.HTTPConnection(netloc, timeout=self.timeout)

        return self.tls.conns[origin]

    def relay_streaming(self, res):
        self.send_response(res.status, res.reason)
        for header, val in res.headers.items():
            self.send_header(header, val)
        self.end_headers()
        try:
            while True:
                chunk = res.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
            self.wfile.flush()
        except socket.error:
            # connection closed by client
            pass

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET

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

    def encode_content_body(self, text, encoding):
        if encoding != 'identity':
            if encoding in ('gzip', 'x-gzip'):
                io = BytesIO()
                with gzip.GzipFile(fileobj=io, mode='wb') as f:
                    f.write(text)
                text = io.getvalue()
            elif encoding == 'deflate':
                text = zlib.compress(text)
            else:
                self.log_message("Unknown Content-Encoding: %s", encoding)
        return text

    def decode_content_body(self, data, encoding):
        if encoding != 'identity':
            if encoding in ('gzip', 'x-gzip'):
                io = BytesIO(data)
                with gzip.GzipFile(fileobj=io) as f:
                    data = f.read()
            elif encoding == 'deflate':
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    data = zlib.decompress(data, -zlib.MAX_WBITS)
            else:
                self.log_message("Unknown Content-Encoding: %s", encoding)
        return data

    def send_cacert(self):
        with open(self.cacert, 'rb') as f:
            data = f.read()

        self.send_response(200, 'OK')
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.send_header('Content-Length', len(data))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def print_info(self, req, req_body, res, res_body):
        def parse_qsl(s):
            return '\n'.join("%-20s %s" % (k, v) for k, v in urllib.parse.parse_qsl(s, keep_blank_values=True))

        req_header_text = "%s %s %s\n%s" % (req.command, req.path, req.request_version, req.headers)
        res_header_text = "%s %d %s\n%s" % (res.response_version, res.status, res.reason, res.headers)

        print(with_color(33, req_header_text))

        u = urllib.parse.urlsplit(req.path)
        if u.query:
            query_text = parse_qsl(u.query)
            print(with_color(32, "==== QUERY PARAMETERS ====\n%s\n" % query_text))

        cookie = req.headers.get('Cookie', '')
        if cookie:
            cookie = parse_qsl(re.sub(r';\s*', '&', cookie))
            print(with_color(32, "==== COOKIE ====\n%s\n" % cookie))

        auth = req.headers.get('Authorization', '')
        if auth.lower().startswith('basic'):
            token = auth.split()[1].decode('base64')
            print(with_color(31, "==== BASIC AUTH ====\n%s\n" % token))

        if req_body is not None:
            req_body_text = None
            content_type = req.headers.get('Content-Type', '')

            if content_type.startswith('application/x-www-form-urlencoded'):
                req_body_text = parse_qsl(req_body)
            elif content_type.startswith('application/json'):
                try:
                    json_obj = json.loads(req_body)
                    json_str = json.dumps(json_obj, indent=2)
                    if json_str.count('\n') < 50:
                        req_body_text = json_str
                    else:
                        lines = json_str.splitlines()
                        req_body_text = "%s\n(%d lines)" % ('\n'.join(lines[:50]), len(lines))
                except ValueError:
                    req_body_text = req_body
            elif len(req_body) < 1024:
                req_body_text = req_body

            if req_body_text:
                print(with_color(32, "==== REQUEST BODY ====\n%s\n" % req_body_text))

        print(with_color(36, res_header_text))

        cookies = res.headers.get_all('Set-Cookie')

        if cookies:
            cookies = '\n'.join(cookies)
            print(with_color(31, "==== SET-COOKIE ====\n%s\n" % cookies))

        if res_body is not None:
            res_body_text = None
            content_type = res.headers.get('Content-Type', '')

            if content_type.startswith('application/json'):
                try:
                    json_obj = json.loads(res_body)
                    json_str = json.dumps(json_obj, indent=2)
                    if json_str.count('\n') < 50:
                        res_body_text = json_str
                    else:
                        lines = json_str.splitlines()
                        res_body_text = "%s\n(%d lines)" % ('\n'.join(lines[:50]), len(lines))
                except ValueError:
                    res_body_text = res_body
            elif content_type.startswith('text/html'):
                if isinstance(res_body, bytes):
                    res_body = res_body.decode()
                m = re.search(r'<title[^>]*>\s*([^<]+?)\s*</title>', res_body, re.I)
                if m:
                    print(with_color(32, "==== HTML TITLE ====\n%s\n" % html.unescape(m.group(1))))
            elif content_type.startswith('text/') and len(res_body) < 1024:
                res_body_text = res_body

            if res_body_text:
                print(with_color(32, "==== RESPONSE BODY ====\n%s\n" % res_body_text))

    def request_handler(self, req, req_body):
        pass

    def response_handler(self, req, req_body, res, res_body):
        pass

    def save_handler(self, req, req_body, res, res_body):
        self.print_info(req, req_body, res, res_body)

    def admin_handler(self):
        if self.path == 'http://proxy2.test/':
            self.send_cacert()


def test(handler_class=ProxyRequestHandler, server_class=ThreadingHTTPServer, protocol="HTTP/1.1"):
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 8080
    server_address = ('::1', port)

    handler_class.protocol_version = protocol
    httpd = server_class(server_address, handler_class)

    sa = httpd.socket.getsockname()
    print("Serving HTTP Proxy on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()


if __name__ == '__main__':
    test()

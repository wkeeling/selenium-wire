import logging
import re
from datetime import datetime

from seleniumwire import har
from seleniumwire.request import Request, Response, WebSocketMessage
from seleniumwire.thirdparty.mitmproxy.http import HTTPResponse
from seleniumwire.thirdparty.mitmproxy.net import websockets
from seleniumwire.thirdparty.mitmproxy.net.http.headers import Headers
from seleniumwire.utils import is_list_alike

log = logging.getLogger(__name__)


class InterceptRequestHandler:
    """Mitmproxy add-on which is responsible for request modification
    and capture.
    """

    def __init__(self, proxy):
        self.proxy = proxy

    def requestheaders(self, flow):
        # Requests that are being captured are not streamed.
        if self.in_scope(flow.request):
            flow.request.stream = False

    def request(self, flow):
        # Make any modifications to the original request
        # DEPRECATED. This will be replaced by request_interceptor
        self.proxy.modifier.modify_request(flow.request, bodyattr='raw_content')

        # Convert to one of our requests for handling
        request = self._create_request(flow)

        if not self.in_scope(request):
            log.debug('Not capturing %s request: %s', request.method, request.url)
            return

        # Call the request interceptor if set
        if self.proxy.request_interceptor is not None:
            self.proxy.request_interceptor(request)

            if request.response:
                # The interceptor has created a response for us to send back immediately
                flow.response = HTTPResponse.make(
                    status_code=int(request.response.status_code),
                    content=request.response.body,
                    headers=[(k.encode('utf-8'), v.encode('utf-8')) for k, v in request.response.headers.items()],
                )
            else:
                flow.request.method = request.method
                flow.request.url = request.url
                flow.request.headers = self._to_headers_obj(request.headers)
                flow.request.raw_content = request.body

        log.info('Capturing request: %s', request.url)

        self.proxy.storage.save_request(request)

        if request.id is not None:  # Will not be None when captured
            flow.request.id = request.id

        if request.response:
            # This response will be a mocked response. Capture it for completeness.
            self.proxy.storage.save_response(request.id, request.response)

        # Could possibly use mitmproxy's 'anticomp' option instead of this
        if self.proxy.options.get('disable_encoding') is True:
            flow.request.headers['Accept-Encoding'] = 'identity'

    def in_scope(self, request):
        if request.method in self.proxy.options.get('ignore_http_methods', ['OPTIONS']):
            return False

        scopes = self.proxy.scopes

        if not scopes:
            return True
        elif not is_list_alike(scopes):
            scopes = [scopes]

        for scope in scopes:
            match = re.search(scope, request.url)
            if match:
                return True

        return False

    def responseheaders(self, flow):
        # Responses that are being captured are not streamed.
        if self.in_scope(flow.request):
            flow.response.stream = False

    def response(self, flow):
        # Make any modifications to the response
        # DEPRECATED. This will be replaced by response_interceptor
        self.proxy.modifier.modify_response(flow.response, flow.request)

        if not hasattr(flow.request, 'id'):
            # Request was not stored
            return

        # Convert the mitmproxy specific response to one of our responses
        # for handling.
        response = self._create_response(flow)

        # Call the response interceptor if set
        if self.proxy.response_interceptor is not None:
            self.proxy.response_interceptor(self._create_request(flow, response), response)
            flow.response.status_code = response.status_code
            flow.response.reason = response.reason
            flow.response.headers = self._to_headers_obj(response.headers)
            flow.response.raw_content = response.body

        log.info('Capturing response: %s %s %s', flow.request.url, response.status_code, response.reason)

        self.proxy.storage.save_response(flow.request.id, response)

        if self.proxy.options.get('enable_har', False):
            self.proxy.storage.save_har_entry(flow.request.id, har.create_har_entry(flow))

    def _create_request(self, flow, response=None):
        request = Request(
            method=flow.request.method,
            url=flow.request.url,
            headers=[(k, v) for k, v in flow.request.headers.items()],
            body=flow.request.raw_content,
        )

        # For websocket requests, the scheme of the request is overwritten with https
        # in the initial CONNECT request so this hack explicitly sets the scheme back to wss.
        if websockets.check_handshake(request.headers) and websockets.check_client_version(request.headers):
            request.url = request.url.replace('https', 'wss', 1)

        request.response = response

        return request

    def _create_response(self, flow):
        response = Response(
            status_code=flow.response.status_code,
            reason=flow.response.reason,
            headers=[(k, v) for k, v in flow.response.headers.items(multi=True)],
            body=flow.response.raw_content,
        )

        cert = flow.server_conn.cert
        if cert is not None:
            response.cert = dict(
                subject=cert.subject,
                serial=cert.serial,
                key=cert.keyinfo,
                signature_algorithm=cert.x509.get_signature_algorithm(),
                expired=cert.has_expired,
                issuer=cert.issuer,
                notbefore=cert.notbefore,
                notafter=cert.notafter,
                organization=cert.organization,
                cn=cert.cn,
                altnames=cert.altnames,
            )

        return response

    def _to_headers_obj(self, headers):
        return Headers([(k.encode('utf-8'), v.encode('utf-8')) for k, v in headers.items()])

    def websocket_message(self, flow):
        if hasattr(flow.handshake_flow.request, 'id'):
            message = flow.messages[-1]
            ws_message = WebSocketMessage(
                from_client=message.from_client,
                content=message.content,
                date=datetime.fromtimestamp(message.timestamp),
            )

            self.proxy.storage.save_ws_message(flow.handshake_flow.request.id, ws_message)

            if message.from_client:
                direction = '(client -> server)'
            else:
                direction = '(server -> client)'

            log.debug('Capturing websocket message %s: %s', direction, ws_message)

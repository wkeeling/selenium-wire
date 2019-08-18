import logging
import os
import pkgutil

from .handler import CaptureRequestHandler

log = logging.getLogger(__name__)


def create_custom_capture_request_handler(custom_response_handler):
    """Creates a custom class derived from CaptureRequestHandler with the response_handler overwritten to run the
    custom_response_handler function before running super().response_handler"""
    class CustomCaptureRequestHandler(CaptureRequestHandler):
        def response_handler(self, *args, **kwargs):
            super().response_handler(*args, **kwargs)
            return custom_response_handler(*args, **kwargs)
    return CustomCaptureRequestHandler


def extract_cert():
    """Extracts the root certificate to the current working directory."""
    cert_name = 'ca.crt'
    cert = pkgutil.get_data(__package__, cert_name)

    with open(os.path.join(os.getcwd(), cert_name), 'wb') as out:
        out.write(cert)

    log.info('{} extracted. You can now import this into a browser.'.format(cert_name))

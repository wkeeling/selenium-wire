import collections.abc
import logging
import os
import pkgutil


log = logging.getLogger(__name__)


def extract_cert():
    """Extracts the root certificate to the current working directory."""
    cert_name = 'ca.crt'
    cert = pkgutil.get_data(__package__, cert_name)

    with open(os.path.join(os.getcwd(), cert_name), 'wb') as out:
        out.write(cert)

    log.info('{} extracted. You can now import this into a browser.'.format(
        cert_name))


def is_list_alike(container):
    return (isinstance(container, collections.abc.Sequence) and not
            isinstance(container, str))

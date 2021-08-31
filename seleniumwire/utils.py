import collections.abc
import logging
import os
import pkgutil
from collections import namedtuple
from pathlib import Path
from typing import Dict, NamedTuple
from urllib.request import _parse_proxy

from seleniumwire.thirdparty.mitmproxy.net.http import encoding as decoder

log = logging.getLogger(__name__)

ROOT_CERT = 'ca.crt'
ROOT_KEY = 'ca.key'
COMBINED_CERT = 'seleniumwire-ca.pem'


def get_upstream_proxy(options):
    """Get the upstream proxy configuration from the options dictionary.
    This will be overridden with any configuration found in the environment
    variables HTTP_PROXY, HTTPS_PROXY, NO_PROXY

    The configuration will be returned as a dictionary with keys 'http',
    'https' and 'no_proxy'. The value of the 'http' and 'https' keys will
    be a named tuple with the attributes:
        scheme, username, password, hostport
    The value of 'no_proxy' will be a list.

    Note that the keys will only be present in the dictionary when relevant
    proxy configuration exists.

    Args:
        options: The selenium wire options.
    Returns: A dictionary.
    """
    proxy_options = (options or {}).pop('proxy', {})

    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    no_proxy = os.environ.get('NO_PROXY')

    merged = {}

    if http_proxy:
        merged['http'] = http_proxy
    if https_proxy:
        merged['https'] = https_proxy
    if no_proxy:
        merged['no_proxy'] = no_proxy

    merged.update(proxy_options)

    no_proxy = merged.get('no_proxy')
    if isinstance(no_proxy, str):
        merged['no_proxy'] = [h.strip() for h in no_proxy.split(',')]

    conf = namedtuple('ProxyConf', 'scheme username password hostport')

    for proxy_type in ('http', 'https'):
        # Parse the upstream proxy URL into (scheme, username, password, hostport)
        # for ease of access.
        if merged.get(proxy_type) is not None:
            merged[proxy_type] = conf(*_parse_proxy(merged[proxy_type]))

    return merged


def build_proxy_args(proxy_config: Dict[str, NamedTuple]) -> Dict[str, str]:
    """Build the arguments needed to pass an upstream proxy to mitmproxy.

    Args:
        proxy_config: The proxy config parsed out of the Selenium Wire options.
    Returns: A dictionary of arguments suitable for passing to mitmproxy.
    """
    http_proxy = proxy_config.get('http')
    https_proxy = proxy_config.get('https')
    conf = None

    if http_proxy and https_proxy:
        if http_proxy.hostport != https_proxy.hostport:  # noqa
            # We only support a single upstream proxy server
            raise ValueError('Different settings for http and https proxy servers not supported')

        conf = https_proxy
    elif http_proxy:
        conf = http_proxy
    elif https_proxy:
        conf = https_proxy

    args = {}

    if conf:
        scheme, username, password, hostport = conf

        args['mode'] = 'upstream:{}://{}'.format(scheme, hostport)

        if username:
            args['upstream_auth'] = '{}:{}'.format(username, password)

        custom_auth = proxy_config.get('custom_authorization')

        if custom_auth:
            args['upstream_custom_auth'] = custom_auth

        no_proxy = proxy_config.get('no_proxy')

        if no_proxy:
            args['no_proxy'] = no_proxy

    return args


def extract_cert(cert_name='ca.crt'):
    """Extracts the root certificate to the current working directory."""

    try:
        cert = pkgutil.get_data(__package__, cert_name)
    except FileNotFoundError:
        log.error("Invalid certificate '{}'".format(cert_name))
    else:
        with open(Path(os.getcwd(), cert_name), 'wb') as out:
            out.write(cert)
        log.info('{} extracted. You can now import this into a browser.'.format(cert_name))


def extract_cert_and_key(dest_folder, check_exists=True):
    """Extracts the root certificate and key and combines them into a
    single file called seleniumwire-ca.pem in the specified destination
    folder.

    Args:
        dest_folder: The destination folder that the combined certificate
            and key will be written to.
        check_exists: If True the destination file will not be overwritten
            if it already exists.
    """
    os.makedirs(dest_folder, exist_ok=True)
    combined_path = Path(dest_folder, COMBINED_CERT)
    if check_exists and combined_path.exists():
        return

    root_cert = pkgutil.get_data(__package__, ROOT_CERT)
    root_key = pkgutil.get_data(__package__, ROOT_KEY)

    with open(combined_path, 'wb') as f_out:
        f_out.write(root_cert + root_key)


def is_list_alike(container):
    return isinstance(container, collections.abc.Sequence) and not isinstance(container, str)


def urlsafe_address(address):
    """Make an address safe to use in a URL.

    Args:
        address: A tuple of address information.
    Returns:
        A 2-tuple of url-safe (address, port)
    """
    addr, port, *rest = address

    if rest:
        # An IPv6 address needs to be surrounded by square brackets
        addr = f'[{addr}]'

    return addr, port


def decode(data: bytes, encoding: str) -> bytes:
    """Attempt to decode data based on the supplied encoding.

    If decoding fails a ValueError is raised.

    Args:
        data: The encoded data.
        encoding: The encoding type.
    Returns: The decoded data.
    Raises: ValueError if the data could not be decoded.
    """
    return decoder.decode(data, encoding)

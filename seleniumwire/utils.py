import collections.abc
import logging
import os
import pkgutil
from pathlib import Path
from typing import Dict, List, Sequence, Union
from urllib.request import _parse_proxy  # type: ignore

from seleniumwire.thirdparty.mitmproxy.net.http import encoding as decoder

log = logging.getLogger(__name__)

ROOT_CERT = 'ca.crt'
ROOT_KEY = 'ca.key'
COMBINED_CERT = 'seleniumwire-ca.pem'


def get_upstream_proxy(options: Dict[str, Union[str, Dict]]) -> Dict[str, str]:
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
    try:
        proxy_options: Dict[str, str] = options['proxy']  # type: ignore
    except KeyError:
        proxy_options = {}

    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    no_proxy = os.environ.get('NO_PROXY')

    merged: Dict[str, str] = {}

    if http_proxy:
        merged['http'] = http_proxy
    if https_proxy:
        merged['https'] = https_proxy
    if no_proxy:
        merged['no_proxy'] = no_proxy

    merged.update(proxy_options)

    return merged


def build_proxy_args(proxy_config: Dict[str, str]) -> Dict[str, Union[str, List[str]]]:
    """Build the arguments needed to pass an upstream proxy to mitmproxy.

    Args:
        proxy_config: The proxy config parsed out of the Selenium Wire options.
    Returns: A dictionary of arguments suitable for passing to mitmproxy.
    """
    http_proxy = proxy_config.get('http')
    https_proxy = proxy_config.get('https')
    conf = None

    if https_proxy:
        conf = https_proxy
    elif http_proxy:
        conf = http_proxy

    args: Dict[str, Union[str, List[str]]] = {}

    if conf:
        scheme, username, password, hostport = _parse_proxy(conf)

        args['mode'] = 'upstream:{}://{}'.format(scheme, hostport)

        if username:
            args['upstream_auth'] = '{}:{}'.format(username, password)

        custom_auth = proxy_config.get('custom_authorization')

        if custom_auth:
            args['upstream_custom_auth'] = custom_auth

        no_proxy = proxy_config.get('no_proxy')

        if no_proxy:
            args['no_proxy'] = [h.strip() for h in no_proxy.split(',')]

    return args


def extract_cert(cert_name: str = 'ca.crt') -> None:
    """Extracts the root certificate to the current working directory."""

    cert = pkgutil.get_data(__package__, cert_name)

    if cert is None:
        log.error("Invalid certificate '{}'".format(cert_name))
    else:
        with open(Path(os.getcwd(), cert_name), 'wb') as out:
            out.write(cert)
        log.info('{} extracted. You can now import this into a browser.'.format(cert_name))


def extract_cert_and_key(dest_folder: Union[str, Path], check_exists: bool = True) -> None:
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

    if root_cert is None or root_key is None:
        log.error('Root certificate and/or key missing')
    else:
        with open(combined_path, 'wb') as f_out:
            f_out.write(root_cert + root_key)


def is_list_alike(container: Union[str, Sequence]) -> bool:
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


def decode(data: bytes, encoding: str) -> Union[None, str, bytes]:
    """Attempt to decode data based on the supplied encoding.

    If decoding fails a ValueError is raised.

    Args:
        data: The encoded data.
        encoding: The encoding type.
    Returns: The decoded data.
    Raises: ValueError if the data could not be decoded.
    """
    return decoder.decode(data, encoding)

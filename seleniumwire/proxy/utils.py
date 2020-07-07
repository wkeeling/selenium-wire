import collections.abc
import logging
import os
import pkgutil
from collections import namedtuple, OrderedDict
from collections.abc import Mapping, MutableMapping
from urllib.request import _parse_proxy

log = logging.getLogger(__name__)

ca_certs = {
    'default': 'ca.crt',
    'mitmproxy': 'mitmproxy.crt'
}


def get_upstream_proxy(options):
    """Get the upstream proxy configuration from the options dictionary.
    This will be overridden with any configuration found in the environment
    variables HTTP_PROXY, HTTPS_PROXY, NO_PROXY

    The configuration will be returned as a dictionary with keys 'http',
    'https' and 'no_proxy'. The value of the 'http' and 'https' keys will
    be a named tuple with the attributes:
        scheme, username, password, hostport
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

    conf = namedtuple('ProxyConf', 'scheme username password hostport')

    for proxy_type in ('http', 'https'):
        # Parse the upstream proxy URL into (scheme, username, password, hostport)
        # for ease of access.
        if merged.get(proxy_type) is not None:
            merged[proxy_type] = conf(*_parse_proxy(merged[proxy_type]))

    return merged


def extract_cert(backend='default'):
    """Extracts the root certificate to the current working directory."""
    try:
        cert_name = ca_certs[backend]
    except KeyError as e:
        raise TypeError(
            "Invalid backend '{}'. "
            "Valid values are 'default' or 'mitmproxy'."
            .format(backend)
        ) from e
    cert = pkgutil.get_data(__package__, cert_name)

    with open(os.path.join(os.getcwd(), cert_name), 'wb') as out:
        out.write(cert)

    log.info('{} extracted. You can now import this into a browser.'.format(
        cert_name))


def is_list_alike(container):
    return (isinstance(container, collections.abc.Sequence) and not
            isinstance(container, str))


# This class has been taken from the requests library.
# https://github.com/requests/requests.
class CaseInsensitiveDict(MutableMapping):
    """A case-insensitive ``dict``-like object.
    Implements all methods and operations of
    ``MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.
    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::
        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True
    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    def __init__(self, data=None, **kwargs):
        self._store = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))

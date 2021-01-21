from .http_proxy import HttpProxy, HttpUpstreamProxy
from .socks_proxy import SocksUpstreamProxy

__all__ = [
    "HttpProxy", "HttpUpstreamProxy",
    "SocksUpstreamProxy",
]

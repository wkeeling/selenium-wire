import typing


class UpstreamAuth:
    """
    This addon handles authentication to systems upstream from us for the
    upstream proxy and reverse proxy mode.

    NOTE: due to timing issues, upstream authentication has been moved
    to the HTTPLayer. It seems that when running in a multi-threaded
    environment, the hooks that apply authentication are not always
    invoked at the correct moment leading to sporadic proxy authorization
    failures. The root cause possibly lies in channel messaging but
    that would need further investigation.
    """

    def __init__(self):
        self.auth = None

    def load(self, loader):
        loader.add_option(
            "upstream_auth",
            typing.Optional[str],
            None,
            """
            Add HTTP Basic authentication to upstream proxy and reverse proxy
            requests. Format: username:password.
            """,
        )

        loader.add_option(
            "upstream_custom_auth",
            typing.Optional[str],
            None,
            """
            Add custom authentication to upstream proxy requests by supplying
            the full value of the Proxy-Authorization header. 
            Format: <type> <credentials> - e.g. "Bearer mytoken123"
            """,
        )

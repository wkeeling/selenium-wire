import contextlib
import os
from unittest import TestCase

from seleniumwire.proxy2.utils import get_upstream_proxy


class GetUpstreamProxyTest(TestCase):

    def test_get_config(self):
        options = {
            'proxy': {
                'http': 'http://username1:password1@server1:8888',
                'https': 'https://username2:password2@server2:8888',
                'no_proxy': 'localhost'
            }
        }

        proxy = get_upstream_proxy(options)

        http = proxy['http']
        self.assertEqual('http', http.scheme)
        self.assertEqual('username1', http.username)
        self.assertEqual('password1', http.password)
        self.assertEqual('server1:8888', http.hostport)

        https = proxy['https']
        self.assertEqual('https', https.scheme)
        self.assertEqual('username2', https.username)
        self.assertEqual('password2', https.password)
        self.assertEqual('server2:8888', https.hostport)

        self.assertEqual('localhost', proxy['no_proxy'])

    def test_get_from_env(self):
        with self.set_env(HTTP_PROXY='http://username1:password1@server1:8888',
                          HTTPS_PROXY='https://username2:password2@server2:8888',
                          NO_PROXY='localhost'):

            proxy = get_upstream_proxy({})

            http = proxy['http']
            self.assertEqual('http', http.scheme)
            self.assertEqual('username1', http.username)
            self.assertEqual('password1', http.password)
            self.assertEqual('server1:8888', http.hostport)

            https = proxy['https']
            self.assertEqual('https', https.scheme)
            self.assertEqual('username2', https.username)
            self.assertEqual('password2', https.password)
            self.assertEqual('server2:8888', https.hostport)

            self.assertEqual('localhost', proxy['no_proxy'])

    def test_merge(self):
        options = {
            'proxy': {
                'https': 'https://username3:password3@server3:8888',
                'no_proxy': 'localhost'
            }
        }

        with self.set_env(HTTP_PROXY='http://username1:password1@server1:8888',
                          HTTPS_PROXY='https://username2:password2@server2:8888',
                          NO_PROXY='127.0.0.1'):

            proxy = get_upstream_proxy(options)

            http = proxy['http']
            self.assertEqual('http', http.scheme)
            self.assertEqual('username1', http.username)
            self.assertEqual('password1', http.password)
            self.assertEqual('server1:8888', http.hostport)

            # The dict config overrides that defined in env variables
            https = proxy['https']
            self.assertEqual('https', https.scheme)
            self.assertEqual('username3', https.username)
            self.assertEqual('password3', https.password)
            self.assertEqual('server3:8888', https.hostport)

            self.assertEqual('localhost', proxy['no_proxy'])

    def test_none(self):
        options = None

        proxy = get_upstream_proxy(options)

        self.assertEqual({}, proxy)

    @contextlib.contextmanager
    def set_env(self, **environ):
        """Context manager used to temporarily set environment vars."""
        old_environ = dict(os.environ)
        os.environ.update(environ)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old_environ)

import struct
from typing import Tuple


class ClientHello:
    """Provide access to the component parts of a TLS Client Hello message."""

    def __init__(self, raw_message: bytes):
        self.raw_message: bytes = raw_message
        self.record_header: bytes
        self.handshake_header: bytes
        self.client_version: bytes
        self.client_random: bytes
        self.session_id: bytes
        self.cipher_suites: bytes
        self.compression_methods: bytes
        self.extensions: bytes

        self._parse(raw_message)

    def _parse(self, raw_message: bytes):
        self.record_header, raw_message = self._take(raw_message, 5)
        self.handshake_header, raw_message = self._take(raw_message, 4)
        self.client_version, raw_message = self._take(raw_message, 2)
        self.client_random, raw_message = self._take(raw_message, 32)
        session_id_len, raw_message = self._take(raw_message, 1)
        self.session_id, raw_message = self._take(raw_message, session_id_len[0])
        cipher_suite_len, raw_message = self._take(raw_message, 2)
        self.cipher_suites, raw_message = self._take(raw_message, struct.unpack('>H', cipher_suite_len)[0])
        compression_methods_len, raw_message = self._take(raw_message, 1)
        self.compression_methods, raw_message = self._take(raw_message, compression_methods_len[0])
        extensions_len, raw_message = self._take(raw_message, 2)
        self.extensions, raw_message = self._take(raw_message, struct.unpack('>H', extensions_len)[0])

    def _take(self, remaining: bytes, count: int) -> Tuple[bytes, bytes]:
        prefix = remaining[:count]
        remaining = remaining[count:]
        return prefix, remaining

    def to_bytes(self) -> bytes:
        """Convert the ClientHello object into a sequence of bytes."""

import struct
from typing import Generator, Tuple


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
        self.server_name: bytes

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
        self.server_name = bytes()

        # Find the server name extension
        for ext_type, length, body in self.iter_extensions():
            if ext_type == bytes.fromhex('0000'):  # Server name
                self.server_name = ext_type + length + body
                break

    def _take(self, remaining: bytes, count: int) -> Tuple[bytes, bytes]:
        prefix = remaining[:count]
        remaining = remaining[count:]
        return prefix, remaining

    def iter_extensions(self) -> Generator[(bytes, bytes, bytes)]:
        """Iterate the extensions in the Client Hello.

        Return:
            a generator that yields 3-element tuples of:
            (extension type, extension len, extension body)
        """
        extensions = self.extensions

        while extensions:
            ext_type, extensions = self._take(extensions, 2)
            length, extensions = self._take(extensions, 2)
            body, extensions = self._take(extensions, struct.unpack('>H', length)[0])

            yield ext_type, length, body

    def to_bytes(self) -> bytes:
        """Convert the ClientHello object into a sequence of bytes.

        The message is guaranteed to be exactly 512 bytes excluding the record header.
        """
        message = bytearray()
        message.extend(self.record_header)
        message.extend(self.handshake_header)
        message.extend(self.client_version)
        message.extend(self.client_random)
        message.append(len(self.session_id))
        message.extend(self.session_id)
        message.extend(struct.pack('>H', len(self.cipher_suites)))
        message.extend(self.cipher_suites)
        message.append(len(self.compression_methods))
        message.extend(self.compression_methods)
        message.extend(struct.pack('>H', len(self.extensions)))
        message.extend(self.extensions)

        if len(message) - len(self.record_header) > 512:
            # Message is larger than the max size of 512 bytes
            # Drop all the extensions
            message = message[: -len(self.extensions)]

            # Re-add the extensions apart from the final padding extension
            for ext_type, length, body in self.iter_extensions():
                if ext_type != bytes.fromhex('0015'):
                    message.extend(ext_type + length + body)

            # Add the padding extension to make up to the remaining 512
            message.extend(bytes.fromhex('0015'))
            pad_size = len(message) - len(self.record_header) - 2
            message.extend(struct.pack('>H', pad_size))
            message.extend(bytes.fromhex('00') * pad_size)

        return bytes(message)

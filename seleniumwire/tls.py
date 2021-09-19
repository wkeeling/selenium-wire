import logging
import struct
from typing import Generator, Tuple

# TODO: remove
logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


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
        log.debug(f'Record header: {self.record_header.hex()}')

        self.handshake_header, raw_message = self._take(raw_message, 4)
        log.debug(f'Handshake header: {self.handshake_header.hex()}')

        self.client_version, raw_message = self._take(raw_message, 2)
        log.debug(f'Client version: {self.client_version.hex()}')

        self.client_random, raw_message = self._take(raw_message, 32)
        log.debug(f'Client random: {self.client_random.hex()}')

        session_id_len, raw_message = self._take(raw_message, 1)
        log.debug(f'Session ID length: {session_id_len.hex()}')

        self.session_id, raw_message = self._take(raw_message, session_id_len[0])
        log.debug(f'Session ID: {self.session_id.hex()}')

        cipher_suite_len, raw_message = self._take(raw_message, 2)
        log.debug(f'Cipher suite length: {cipher_suite_len.hex()}')

        self.cipher_suites, raw_message = self._take(raw_message, struct.unpack('>H', cipher_suite_len)[0])
        log.debug(f'Cipher suites: {self.cipher_suites.hex()}')

        compression_methods_len, raw_message = self._take(raw_message, 1)
        log.debug(f'Compression methods length: {compression_methods_len.hex()}')

        self.compression_methods, raw_message = self._take(raw_message, compression_methods_len[0])
        log.debug(f'Compression methods: {self.compression_methods.hex()}')

        extensions_len, raw_message = self._take(raw_message, 2)
        log.debug(f'Extensions length: {extensions_len.hex()}')

        self.extensions, raw_message = self._take(raw_message, struct.unpack('>H', extensions_len)[0])
        log.debug(f'Extensions: {self.extensions.hex()}')

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

    def iter_extensions(self) -> Generator[Tuple[bytes, bytes, bytes], None, None]:
        """Iterate the extensions in the Client Hello.

        Return:
            a generator that yields 2-element tuples of:
            (extension type, extension length, extension body)
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

        extensions = bytearray()

        for ext_type, length, body in self.iter_extensions():
            if ext_type != bytes.fromhex('0015'):
                extensions.extend(ext_type + length + body)

        # Add the padding type
        extensions.extend(bytes.fromhex('0015'))

        pad_len_bytes = 2
        ext_len_bytes = 2
        pad_size = 512 - len(message[len(self.record_header) :]) - len(extensions) - ext_len_bytes - pad_len_bytes

        extensions.extend(struct.pack('>H', pad_size))
        extensions.extend(bytes.fromhex('00') * pad_size)

        message.extend(struct.pack('>H', len(extensions)))
        message.extend(extensions)

        # Update the record length
        message[3:5] = struct.pack('>H', len(message[len(self.record_header) :]))

        # Update the handshake length
        message[6:9] = (len(message[9:])).to_bytes(3, byteorder='big')

        message_len = len(message[len(self.record_header) :])
        assert message_len == 512, f'Client hello is {message_len} bytes (should be 512)'

        return bytes(message)

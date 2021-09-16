import pytest

from seleniumwire.tls import ClientHello


class TestClientHello:
    @pytest.fixture
    def message(self):
        """
        Handshake Protocol: Client Hello
        Handshake Type: Client Hello (1)
        Length: 508
        Version: TLS 1.2 (0x0303)
        Random: b15270347a92b97bbf91fce1f03d9232d6322bf1175d2f30...
        Session ID Length: 32
        Session ID: 0b5dcd017b0dc64100918d6e5e9b2d5f356792839af72656...
        Cipher Suites Length: 36
        Cipher Suites (18 suites)
        Compression Methods Length: 1
        Compression Methods (1 method)
        Extensions Length: 399
        Extension: server_name (len=22)
        Extension: extended_master_secret (len=0)
        Extension: renegotiation_info (len=1)
        Extension: supported_groups (len=14)
        Extension: ec_point_formats (len=2)
        Extension: SessionTicket TLS (len=0)
        Extension: application_layer_protocol_negotiation (len=14)
        Extension: status_request (len=5)
        Extension: key_share (len=107)
        Extension: supported_versions (len=5)
        Extension: signature_algorithms (len=24)
        Extension: psk_key_exchange_modes (len=2)
        Extension: Unknown type 28 (len=2)
        Extension: padding (len=145)
        """
        return bytes.fromhex(
            '1603010200010001fc0303b15270347a92b97bbf91fce1f03d9232d6322bf1175d2f303b4ec4be3cdbe95a200b5dcd017b0dc641'
            '00918d6e5e9b2d5f356792839af7265691dfa3619d7861bb0024130113031302c02bc02fcca9cca8c02cc030c00ac009c013c014'
            '009c009d002f0035000a0100018f000000160014000011737461636b6f766572666c6f772e636f6d00170000ff01000100000a00'
            '0e000c001d00170018001901000101000b00020100002300000010000e000c02683208687474702f312e31000500050100000000'
            '0033006b0069001d00206d3798e9e78a240c97a4f78f9d97ceb6f9634a96d230e6b10e7eb8c9f9faef3a00170041041b5a526b58'
            'f2338d963577bbf8524d65ff1763bb9ebdb507663c05ea75438da7976e75732f1e123f01d7f2d12397f183420addcb8271112bc5'
            '9631016580ac65002b00050403040303000d0018001604030503060308040805080604010501060102030201002d00020101001c'
            '00024001001500910000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
        )

    @pytest.fixture
    def client_hello(self, message):
        return ClientHello(message)

    def test_raw_message(self, client_hello, message):
        assert client_hello.raw_message == message

    def test_record_header(self, client_hello):
        assert client_hello.record_header == bytes.fromhex('1603010200')

    def test_handshake_header(self, client_hello):
        assert client_hello.handshake_header == bytes.fromhex('010001fc')

    def test_client_version(self, client_hello):
        assert client_hello.client_version == bytes.fromhex('0303')

    def test_client_random(self, client_hello):
        assert client_hello.client_random == bytes.fromhex(
            'b15270347a92b97bbf91fce1f03d9232d6322bf1175d2f303b4ec4be3cdbe95a'
        )

    def test_session_id(self, client_hello):
        assert client_hello.session_id == bytes.fromhex(
            '0b5dcd017b0dc64100918d6e5e9b2d5f356792839af7265691dfa3619d7861bb'
        )

    def test_cipher_suites(self, client_hello):
        assert client_hello.cipher_suites == bytes.fromhex(
            '130113031302c02bc02fcca9cca8c02cc030c00ac009c013c014009c009d002f0035000a'
        )

    def test_compression_methods(self, client_hello):
        assert client_hello.compression_methods == bytes.fromhex('00')

    def test_extensions(self, client_hello):
        assert client_hello.extensions == bytes.fromhex(
            '000000160014000011737461636b6f766572666c6f772e636f6d00170000ff01000100000a000e000c001d001700180019010001'
            '01000b00020100002300000010000e000c02683208687474702f312e310005000501000000000033006b0069001d00206d3798e9'
            'e78a240c97a4f78f9d97ceb6f9634a96d230e6b10e7eb8c9f9faef3a00170041041b5a526b58f2338d963577bbf8524d65ff1763'
            'bb9ebdb507663c05ea75438da7976e75732f1e123f01d7f2d12397f183420addcb8271112bc59631016580ac65002b0005040304'
            '0303000d0018001604030503060308040805080604010501060102030201002d00020101001c0002400100150091000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '0000000000000000000000000000000000000000000000000000000000000000000000'
        )

    def test_server_name_extension(self, client_hello):
        assert client_hello.server_name == bytes.fromhex('000000160014000011737461636b6f766572666c6f772e636f6d')

    def test_to_bytes(self, client_hello):
        assert client_hello.raw_message == client_hello.to_bytes()

from seleniumwire.webdriver import urlsafe_address


def test_urlsafe_address_ipv4():
    assert urlsafe_address(('192.168.0.1', 9999)) == ('192.168.0.1', 9999)


def test_urlsafe_address_ipv6():
    assert urlsafe_address(('::ffff:127.0.0.1', 9999, 0, 0)) == ('[::ffff:127.0.0.1]', 9999)

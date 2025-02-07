import pytest

from solrizer.handles import Handle, HandleValueError


@pytest.mark.parametrize(
    ('value', 'expected_prefix', 'expected_suffix'),
    [
        # tuple
        (('1903.1', '123'), '1903.1', '123'),
        # hdl: URI
        ('hdl:1903.1/123', '1903.1', '123'),
        # info: URI
        ('info:hdl/1903.1/123', '1903.1', '123'),
        # plain
        ('1903.1/123', '1903.1', '123'),
    ]
)
def test_handle_parse(value, expected_prefix, expected_suffix):
    handle = Handle.parse(value)
    assert handle.prefix == expected_prefix
    assert handle.suffix == expected_suffix


def test_handle_parse_with_default_proxy_base():
    handle = Handle.parse('http://hdl.handle.net/1903.1/456')
    assert handle.prefix == '1903.1'
    assert handle.suffix == '456'


def test_handle_parse_with_explicit_proxy_base():
    handle = Handle.parse('http://handle.example.org/1903.1/456', 'http://handle.example.org/')
    assert handle.prefix == '1903.1'
    assert handle.suffix == '456'


@pytest.mark.parametrize(
    ('value', 'expected_message'),
    [
        (None, 'Cannot parse None'),
        ('', 'does not look like a handle'),
        ('string without slash', 'does not look like a handle'),
        ('prefix-only/', 'suffix cannot be empty'),
        ('prefix-with-blank-suffix/   ', 'suffix cannot be empty'),
        ('/suffix-only', 'prefix cannot be empty'),
        ('   /suffix-with-blank-prefix', 'prefix cannot be empty'),
    ]
)
def test_handle_parse_error(value, expected_message):
    with pytest.raises(HandleValueError) as e:
        Handle.parse(value)

    assert expected_message in str(e.value)


def test_handles_equal():
    assert Handle.parse('1903.1/789') == Handle('1903.1', '789')


def test_handles_not_equal():
    assert Handle.parse('1903.1/789') != Handle('1903.1', '001')


@pytest.fixture
def handle():
    return Handle('1903.1', '123')


def test_handle_str(handle):
    assert str(handle) == '1903.1/123'


def test_handle_hdl_uri(handle):
    assert handle.hdl_uri == 'hdl:1903.1/123'


def test_handle_info_uri(handle):
    assert handle.info_uri == 'info:hdl/1903.1/123'


def test_handle_proxy_url(handle):
    assert handle.proxy_url() == 'http://hdl.handle.net/1903.1/123'
    assert handle.proxy_url('http://handle.example.org/') == 'http://handle.example.org/1903.1/123'
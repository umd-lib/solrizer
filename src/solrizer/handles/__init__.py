from typing import NamedTuple, Self

DEFAULT_PROXY_BASE = 'http://hdl.handle.net/'


def split_as_handle(value: str) -> tuple[str, str]:
    """Split the given string `value` into two parts on a "/" separator, and return
    those strings. If either string is empty (i.e., no non-whitespace characters in
    it), raises a `HandleValueError`."""
    prefix, suffix = value.split('/', 1)
    if prefix.strip() == '':
        raise HandleValueError('Handle prefix cannot be empty')
    if suffix.strip() == '':
        raise HandleValueError('Handle suffix cannot be empty')
    return prefix, suffix


class Handle(NamedTuple):
    """Syntactic representation of a [handle](https://en.wikipedia.org/wiki/Handle_System).

    Instances of `Handle` stringify to their basic `{prefix}/{suffix}` format:

    ```pycon
    >>> h = Handle('1903.1', '1673')

    >>> str(h)
    '1903.1/1673'

    ```

    Other formats are also available:

    ```pycon
    >>> h.hdl_uri
    'hdl:1903.1/1673'

    >>> h.info_uri
    'info:hdl/1903.1/1673'

    >>> h.proxy_url()
    'http://hdl.handle.net/1903.1/1673'

    >>> h.proxy_url('http://handle.example.org/')
    'http://handle.example.org/1903.1/1673'

    ```
    """

    prefix: str
    """Handle prefix"""
    suffix: str
    """Handle suffix"""

    @classmethod
    def parse(cls, value: str | tuple, proxy_base: str = DEFAULT_PROXY_BASE) -> Self:
        """Attempt to parse the given `value` as a handle. Accepts the following
        types of input:

        * a tuple with 2 elements (prefix and suffix)
        * a string of the form `hdl:{prefix}/{suffix}`
        * a string of the form `info:hdl/{prefix}/{suffix}`
        * a string of the form `hdl:{prefix}/{suffix}`
        * a string of the form `{proxy_base}{prefix}/{suffix}`, where `proxy_base` is
          the base URL for a handle proxy service

        The default `proxy_base` is "http://hdl.handle.net/"

        If the `value` is `None`, or cannot be parsed as any of the above forms,
        raises a `HandleValueError`.
        """
        if value is None:
            raise HandleValueError('Cannot parse None as a handle value')
        if isinstance(value, tuple):
            return cls(*value[0:2])
        if value.startswith('hdl:'):
            return cls(*split_as_handle(value[4:]))
        if value.startswith('info:hdl/'):
            return cls(*split_as_handle(value[9:]))
        if proxy_base is not None and value.startswith(proxy_base):
            return cls(*split_as_handle(value[len(proxy_base):]))
        if '/' in value:
            return cls(*split_as_handle(value))

        raise HandleValueError(f'{value} does not look like a handle')

    def __str__(self):
        """Format the handle as `{prefix}/{suffix}`"""
        return f'{self.prefix}/{self.suffix}'

    @property
    def hdl_uri(self) -> str:
        """Format the handle as `hdl:{prefix}/{suffix}`"""
        return f'hdl:{self}'

    @property
    def info_uri(self) -> str:
        """Format the handle as `info:hdl/{prefix}/{suffix}`"""
        return f'info:hdl/{self}'

    def proxy_url(self, proxy_base: str = DEFAULT_PROXY_BASE) -> str:
        """Format the handle as `{proxy_base}{prefix}/{suffix}`"""
        return proxy_base + str(self)


class HandleValueError(ValueError):
    pass

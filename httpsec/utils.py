import typing
from collections.abc import MutableMapping
from multiprocessing import RLock

import socks
from urllib3.util import parse_url

_Null = object()


def iterkeys(d, **kw):
    return iter(d.keys(**kw))


def itervalues(d, **kw):
    return iter(d.values(**kw))


class RecentlyUsedContainer(MutableMapping):
    """
    Provides a thread-safe dict-like container which maintains up to
    ``maxsize`` keys while throwing away the least-recently-used keys beyond
    ``maxsize``.

    :param maxsize:
        Maximum number of recent elements to retain.

    :param dispose_func:
        Every time an item is evicted from the container,
        ``dispose_func(value)`` is called.  Callback which will get called
    """

    ContainerCls = typing.OrderedDict

    def __init__(self, maxsize=10, dispose_func=None):
        self._maxsize = maxsize
        self.dispose_func = dispose_func

        self._container = self.ContainerCls()
        self.lock = RLock()

    def __getitem__(self, key):
        # Re-insert the item, moving it to the end of the eviction line.
        with self.lock:
            item = self._container.pop(key)
            self._container[key] = item
            return item

    def __setitem__(self, key, value):
        evicted_value = _Null
        with self.lock:
            # Possibly evict the existing value of 'key'
            evicted_value = self._container.get(key, _Null)
            self._container[key] = value

            # If we didn't evict an existing value, we might have to evict the
            # least recently used item from the beginning of the container.
            if len(self._container) > self._maxsize:
                _key, evicted_value = self._container.popitem(last=False)

        if self.dispose_func and evicted_value is not _Null:
            self.dispose_func(evicted_value)

    def __delitem__(self, key):
        with self.lock:
            value = self._container.pop(key)

        if self.dispose_func:
            self.dispose_func(value)

    def __len__(self):
        with self.lock:
            return len(self._container)

    def __iter__(self):
        raise NotImplementedError(
            "Iteration over this class is unlikely to be threadsafe."
        )

    def clear(self):
        with self.lock:
            # Copy pointers to all values, then wipe the mapping
            values = list(itervalues(self._container))
            self._container.clear()

        if self.dispose_func:
            for value in values:
                self.dispose_func(value)

    def keys(self):
        with self.lock:
            return list(iterkeys(self._container))


def get_environ_proxies(url, no_proxy=None):
    return {

    }


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if isinstance(value, typing.Mapping):
        value = value.items()

    return list(value)


def merge_setting(request_setting: typing.Mapping, session_setting):
    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting
    if not (
            isinstance(session_setting, typing.Mapping) and isinstance(request_setting, typing.Mapping)
    ):
        return request_setting
    merged_setting = dict(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]

    return merged_setting


def parser_socket_proxy_opts(proxy_url):
    parsed = parse_url(proxy_url)
    username = password = None
    if parsed.auth is not None:
        split = parsed.auth.split(":")
        if len(split) == 2:
            username, password = split
    if parsed.scheme == "socks5":
        socks_version = socks.PROXY_TYPE_SOCKS5
        rDNS = False
    elif parsed.scheme == "socks5h":
        socks_version = socks.PROXY_TYPE_SOCKS5
        rDNS = True
    elif parsed.scheme == "socks4":
        socks_version = socks.PROXY_TYPE_SOCKS4
        rDNS = False
    elif parsed.scheme == "socks4a":
        socks_version = socks.PROXY_TYPE_SOCKS4
        rDNS = True
    else:
        raise ValueError("Unable to determine SOCKS version from %s" % proxy_url)

    opts = {
        "socks_version": socks_version,
        "proxy_host": parsed.host,
        "proxy_port": parsed.port,
        "username": username,
        "password": password,
        "rDNS": rDNS,
    }
    return opts

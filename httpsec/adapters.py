import collections
from urllib.parse import urlparse
from httpsec.connection import HTTPConnection, HTTPSConnection, SOCKSConnection
from httpsec.utils import RecentlyUsedContainer, parser_socket_proxy_opts
import logging

log = logging.getLogger(__file__)

connection_classes_by_scheme = {"http": HTTPConnection, "https": HTTPSConnection, "socks": SOCKSConnection}

_key_fields = (
    "scheme",  # str
    "host",  # str
    "port",  # int
    "timeout",  # int or float or tuple
    "source_address",  # str
    "key_file",  # str
    "key_password",  # str
    "cert_file",  # str
    "cert_reqs",  # str
    "ca_certs",  # str
    "ssl_version",  # str
    "ca_cert_dir",  # str
    "ssl_context",  # instance of ssl.SSLContext or urllib3.util.ssl_.SSLContext
    "proxy",  # parsed proxy url
    "socket_options",  # list of (level (int), optname (int), value (int or str)) tuples
    "socks_options",  # dict
)
PoolKey = collections.namedtuple("PoolKey", _key_fields)


def get_pool_key_normalizer(key_class: PoolKey.__class__, request_context):
    """
    Create a pool key out of a request context dictionary.

    According to RFC 3986, both the scheme and host are case-insensitive.
    Therefore, this function normalizes both before constructing the pool
    key for an HTTPS request. If you wish to change this behaviour, provide
    alternate callables to ``key_fn_by_scheme``.

    :param key_class:
        The class to use when constructing the key. This should be a namedtuple
        with the ``scheme`` and ``host`` keys at a minimum.
    :type  key_class: namedtuple
    :param request_context:
        A dictionary-like object that contain the context for a request.
    :type  request_context: dict

    :return: A namedtuple that can be used as a connection pool key.
    :rtype:  PoolKey
    """
    # Since we mutate the dictionary, make a copy first
    context = request_context.copy()
    context["scheme"] = context["scheme"].lower()
    context["host"] = context["host"].lower()

    # These are both dictionaries and need to be transformed into frozensets
    for key in ("headers", "_proxy_headers", "_socks_options"):
        if key in context and context[key] is not None:
            context[key] = frozenset(context[key].items())

    # The socket_options key may be a list and needs to be transformed into a
    # tuple.
    socket_opts = context.get("socket_options")
    if socket_opts is not None:
        context["socket_options"] = tuple(socket_opts)

    # Map the kwargs to the names in the namedtuple - this is necessary since
    # namedtuples can't have fields starting with '_'.
    for key in list(context.keys()):
        context[key] = context.pop(key)

    # Default to ``None`` for keys missing from the context
    for field in key_class._fields:
        if field not in context:
            context[field] = None

    return key_class(**context)


class HTTPAdapter(object):
    def __init__(self):
        num_pools = 4
        self.pools = RecentlyUsedContainer(num_pools, dispose_func=lambda p: p.close())
        self.num_connections = 0
        self.connection_classes_by_scheme = connection_classes_by_scheme

    def _new_conn(self, pool_key: PoolKey, connect_opts=None) -> HTTPConnection:
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        log.info(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            pool_key.host,
            pool_key.port or "80",
        )
        proxy = pool_key.proxy
        proxy_parsed = urlparse(proxy)
        scheme = pool_key.scheme
        host = pool_key.host
        port = pool_key.port
        if proxy_parsed and proxy_parsed.scheme:
            scheme = proxy_parsed.scheme
            if proxy_parsed.scheme.startswith("http"):
                host = proxy_parsed.hostname
                port = proxy_parsed.port
        connection_class = self.connection_classes_by_scheme.get(scheme)
        conn = connection_class(host=host, port=port, **connect_opts)
        return conn

    def get_conn(self, pool_key, connect_opts=None):
        conn = self.pools.get(pool_key)
        if conn is None:
            conn = self._new_conn(pool_key, connect_opts=connect_opts)
        return conn

    def send(self, method, url=None, proxy=None, timeout=None):
        parsed = urlparse(url)
        if not proxy or not urlparse(proxy).scheme.startswith('http'):
            url = f"{parsed.path}?{parsed.query}#{parsed.fragment}"
        # conn keys
        # 这里对连接池key 进行聚合
        context = {'scheme': parsed.scheme, 'host': parsed.hostname, 'port': parsed.port}
        read_timeout = timeout[1]
        connect_opts = {
            "timeout": timeout[0]
        }
        if proxy:
            if proxy.startswith("http"):
                proxy_parsed = urlparse(proxy)
                context['scheme'] = proxy_parsed.scheme
                context['host'] = proxy_parsed.hostname
                context['port'] = proxy_parsed.port
            else:
                # sock5
                context['proxy'] = proxy
                connect_opts.update(**parser_socket_proxy_opts(proxy))
        pool_key_constructor = get_pool_key_normalizer(PoolKey, context)
        conn = self.get_conn(pool_key_constructor, connect_opts=connect_opts)
        assert conn is not None
        conn.request(method, url)
        conn.sock.settimeout(read_timeout)
        response = conn.getresponse()
        self.pools[pool_key_constructor] = conn
        return response

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        for con in self.pools.values():
            con.close()
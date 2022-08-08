import collections
from urllib.parse import urlparse

from httpsec.model import Response

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


def get_pool_key_normalizer(data: collections.OrderedDict):
    key = ""
    for k, v in data.items():
        key += "%s:%s" % (k, v)
    return key


class HTTPAdapter(object):
    responseCls = Response

    def __init__(self):
        num_pools = 4
        self.pools = RecentlyUsedContainer(num_pools, dispose_func=lambda p: p.close())
        self.num_connections = 0
        self.connection_classes_by_scheme = connection_classes_by_scheme

    def _new_conn(self, **kwargs) -> HTTPConnection:
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        scheme = kwargs.pop("scheme")
        connection_class = self.connection_classes_by_scheme.get(scheme)
        conn = connection_class(**kwargs)
        return conn

    def get_conn(self, pool_key):
        conn = self.pools.get(pool_key)
        return conn

    def send(self, method, url=None, proxy=None, timeout=None):
        parsed = urlparse(url)
        # conn keys
        # 这里对连接池key 进行聚合
        context = collections.OrderedDict(
            {'scheme': parsed.scheme, 'host': parsed.hostname, 'port': parsed.port, "timeout": timeout[0]})
        read_timeout = timeout[1]
        request_url = f"{parsed.path or '/'}?{parsed.query}#{parsed.fragment}"
        if proxy:
            if proxy.startswith("http"):
                proxy_parsed = urlparse(proxy)
                context['scheme'] = proxy_parsed.scheme
                context['host'] = proxy_parsed.hostname
                context['port'] = proxy_parsed.port
                request_url = url
            else:
                # sock5
                context['proxy'] = proxy
                context.update({"connect_opts": parser_socket_proxy_opts(proxy)})

        pool_key_constructor = get_pool_key_normalizer(context)
        conn = self.get_conn(pool_key_constructor)
        if conn is None:
            conn = self._new_conn(**context)
        assert conn is not None
        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False
        try:
            conn.request(method, request_url)
            conn.sock.settimeout(read_timeout)
            http_response = conn.getresponse()
            response = self.responseCls.from_http_response(url, http_response)
            clean_exit = True
        except Exception as e:
            log.exception(e)
            raise e
        finally:
            if not clean_exit:
                # We hit some kind of exception, handled or otherwise. We need
                # to throw the connection away unless explicitly told not to.
                # Close the connection, set the variable to None, and make sure
                # we put the None back in the pool to avoid leaking it.
                conn = conn and conn.close()
                release_this_conn = True
        self.pools[pool_key_constructor] = conn
        return response

    def close(self):
        """
        Close all pooled connections and disable the pool.
        """
        for con in self.pools.values():
            con.close()

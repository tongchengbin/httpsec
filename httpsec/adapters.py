import urllib
from urllib.parse import urlparse

import socks

from httpsec.connection import HTTPConnection, HTTPSConnection, SOCKSConnection
from httpsec.utils import RecentlyUsedContainer
import logging

log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)

connection_classes_by_scheme = {"http": HTTPConnection, "https": HTTPSConnection, "socks": SOCKSConnection}


class HTTPAdapter(object):
    def __init__(self):
        num_pools = 4
        self.pools = RecentlyUsedContainer(num_pools, dispose_func=lambda p: p.close())
        self.num_connections = 0
        self.connection_classes_by_scheme = connection_classes_by_scheme

    def _new_conn(self, parsed: urllib.parse.ParseResult, **kwargs) -> HTTPConnection:
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        log.info(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            parsed.hostname,
            parsed.port or "80",
        )
        connection_class = self.connection_classes_by_scheme.get(parsed.scheme)
        conn = connection_class(host=parsed.hostname, port=parsed.port, **kwargs)
        return conn

    def get_conn(self, parsed, proxy):
        kw = {}
        if proxy:
            proxy_parsed = urlparse(proxy)
            if proxy_parsed.scheme.startswith("http"):
                conn = self.pools.get(proxy_parsed)
            else:
                # socks5 connect is real host
                # todo 如果同一个链接 第一次没有使用代理  第二次设置代理也不会生效 这里需要添加proxy key
                conn = self.pools.get(parsed)
                if conn is None:
                    return self.http_for_proxy_socks(parsed, proxy_parsed)
        else:
            conn = self.pools.get(parsed)

        if conn is None:
            conn = self._new_conn(parsed, **kw)
        return conn

    def send(self, method, url=None, proxy=None):
        parsed = urlparse(url)
        if proxy and urlparse(proxy).scheme.startswith("http"):
            url = f"{parsed.path}?{parsed.query}#{parsed.fragment}"
        conn = self.get_conn(parsed, proxy)
        assert conn is not None
        conn.request(method, url)
        response = conn.getresponse()
        return response

    def http_for_proxy_socks(self, parsed, proxy_parsed):
        """
            创建一个socket 代理连接
        """
        assert proxy_parsed is not None
        connection_class = self.connection_classes_by_scheme.get('socks')
        if proxy_parsed.scheme == "socks5":
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
            raise ValueError("Unsupported SOCKS Version")

        socks_options = {
            "socks_version": socks_version,
            "proxy_host": proxy_parsed.hostname,
            "proxy_port":proxy_parsed.port,
            "username": proxy_parsed.hostname,
            "password": proxy_parsed.password,
            "rDNS": rDNS,
            "timeout": None
        }
        conn = connection_class(parsed.hostname, port=parsed.port, socks_opts=socks_options)
        return conn


from urllib3.poolmanager import ProxyManager

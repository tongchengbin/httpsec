from __future__ import annotations
import urllib3
from requests.exceptions import InvalidSchema

from httpsec.connectionpool import HttpConnectionPool, HttpsConnectionPool

try:
    from urllib3.contrib.socks import SOCKSProxyManager as OriginSocketManager
except ImportError:
    def SOCKSProxyManager(*args, **kwargs):
        raise InvalidSchema("Missing dependencies for SOCKS support.")
pool_classes_by_scheme = {
    "http": HttpConnectionPool,
    "https": HttpsConnectionPool
}


class PoolManager(urllib3.PoolManager):
    def __init__(self, **connection_pool_kw):
        super(PoolManager, self).__init__(**connection_pool_kw)
        self.pool_classes_by_scheme = pool_classes_by_scheme


class ProxyManager(urllib3.ProxyManager):
    def __init__(self,proxy_url, **connection_pool_kw):
        super(ProxyManager, self).__init__(proxy_url,**connection_pool_kw)
        self.pool_classes_by_scheme = pool_classes_by_scheme


class SOCKSProxyManager(OriginSocketManager):
    def __init__(self, **connection_pool_kw):
        super(SOCKSProxyManager, self).__init__(**connection_pool_kw)
        self.pool_classes_by_scheme = pool_classes_by_scheme

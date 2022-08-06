from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

from httpsec.connection import HttpConnection, HttpsConnection
from httpsec.response import Response


class HttpConnectionPool(HTTPConnectionPool):
    ConnectionCls = HttpConnection
    ResponseCls = Response

    def urlopen(
            self,
            method,
            url,
            body=...,
            headers=...,
            retries=...,
            redirect=...,
            assert_same_host=...,
            timeout=...,
            pool_timeout=...,
            release_conn=...,
            **response_kw,
    ) -> Response: ...


class HttpsConnectionPool(HTTPSConnectionPool):
    ConnectionCls = HttpsConnection
    ResponseCls = Response

from __future__ import annotations

from urllib.parse import urljoin
from urllib3 import PoolManager, Retry
from urllib3.connection import port_by_scheme, log
from urllib3.exceptions import MaxRetryError, LocationValueError
from urllib3.poolmanager import ProxyConfig, PoolKey
from urllib3.request import RequestMethods
from urllib3.util import parse_url

import httpsec.connectionpool
from httpsec.url import URL
from httpsec.connectionpool import HttpConnectionPool, HttpsConnectionPool

pool_classes_by_scheme = {
    "http": HttpConnectionPool,
    "https": HttpsConnectionPool
}


class HttpManager(PoolManager, RequestMethods):
    def __init__(self, **connection_pool_kw):
        super(HttpManager, self).__init__(**connection_pool_kw)
        self.pool_classes_by_scheme = pool_classes_by_scheme

    def urlopen(self, method, url: str | URL, redirect=True, **kw):
        """
         经过session.request -> pool manager.urlopen
        :param method:
        :param url:
        :param redirect:
        :param kw:
        :return:
        """
        if isinstance(url, URL):
            parsed = url
        else:
            parsed = parse_url(url)
        if "headers" not in kw:
            kw["headers"] = self.headers.copy()
        proxies = kw.get('proxies')
        proxy = proxies.get(parsed.scheme)
        proxy_ssl_context = None
        use_forwarding_for_https = False
        proxy_config = ProxyConfig(proxy_ssl_context, use_forwarding_for_https)

        if proxy:
            parsed_proxy = parse_url(proxy)
            kw["_proxy"] = parsed_proxy
            kw["_proxy_headers"] = {}
            kw["_proxy_config"] = proxy_config
            headers = kw.get("headers", self.headers)
            kw["headers"] = self._set_proxy_headers(parsed.netloc, headers)
        conn = self.connection_from_host(parsed.host, port=parsed.port, scheme=parsed.scheme, **kw)
        kw["assert_same_host"] = False
        kw["redirect"] = False
        if proxy:
            response = conn.urlopen(method, url, **kw)
        else:
            response = conn.urlopen(method, parsed.request_uri, **kw)

        redirect_location = redirect and response.get_redirect_location()
        if not isinstance(redirect_location, str):
            return response

        # Support relative URLs for redirecting.
        redirect_location = urljoin(url, redirect_location)

        # RFC 7231, Section 6.4.4
        if response.status == 303:
            method = "GET"

        retries = kw.get("retries")
        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect)

        # Strip headers marked as unsafe to forward to the redirected location.
        # Check remove_headers_on_redirect to avoid a potential network call within
        # conn.is_same_host() which may use socket.gethostbyname() in the future.
        if retries.remove_headers_on_redirect and not conn.is_same_host(
                redirect_location
        ):
            headers = kw["headers"].keys()
            for header in headers:
                if header.lower() in retries.remove_headers_on_redirect:
                    kw["headers"].pop(header, None)

        try:
            retries = retries.increment(method, url, response=response, _pool=conn)
        except MaxRetryError:
            if retries.raise_on_redirect:
                response.drain_conn()
                raise
            return response

        kw["retries"] = retries
        kw["redirect"] = redirect

        log.info("Redirecting %s -> %s", url, redirect_location)

        response.drain_conn()
        return self.urlopen(method, redirect_location, **kw)

    @staticmethod
    def _set_proxy_headers(netloc, headers=None):
        """
        Sets headers needed by proxies: specifically, the Accept and Host
        headers. Only sets headers not provided by the user.
        """
        headers_ = {"Accept": "*/*"}
        if netloc:
            headers_["Host"] = netloc
        if headers:
            headers_.update(headers)
        return headers_

    def connection_from_host(self, host, port=None, scheme="http", proxies=None,
                             **pool_kwargs) -> httpsec.connectionpool.HttpConnectionPool:
        """
        Get a :class:`urllib3.connectionpool.ConnectionPool` based on the host, port, and scheme.

        If ``port`` isn't given, it will be derived from the ``scheme`` using
        ``urllib3.connectionpool.port_by_scheme``. If ``pool_kwargs`` is
        provided, it is merged with the instance's ``connection_pool_kw``
        variable and used to create the new connection pool, if one is
        needed.
        """

        proxy = proxies.get(scheme)
        if proxy:
            if scheme != "https":
                proxy_parsed = parse_url(proxy)
                host = proxy_parsed.hostname
                port = proxy_parsed.port
                scheme = proxy_parsed.scheme

        if not host:
            raise LocationValueError("No host specified.")
        request_context = self.connection_pool_kw.copy()
        if pool_kwargs:
            for key, value in pool_kwargs.items():
                if "key_%s" % key not in PoolKey.__dict__:
                    continue
                if value is None:
                    try:
                        del request_context[key]
                    except KeyError:
                        pass
                else:
                    request_context[key] = value
        request_context["scheme"] = scheme or "http"
        if not port:
            port = port_by_scheme.get(request_context["scheme"].lower(), 80)
        request_context["port"] = port
        request_context["host"] = host

        return self.connection_from_context(request_context)

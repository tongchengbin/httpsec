import socket

import socks

from httpsec import httpclient


class HTTPConnection(httpclient.HTTPConnection):
    pass


class HTTPSConnection(httpclient.HTTPConnection):
    pass


class SOCKSConnection(HTTPConnection):
    """
    A plain-text HTTP connection that connects via a SOCKS proxy.
    """

    def __init__(self, host, port=None, timeout=getattr(socket, "_GLOBAL_DEFAULT_TIMEOUT"),
                 source_address=None, blocksize=8192, **kwargs):
        super(SOCKSConnection, self).__init__(host, port, timeout=timeout, source_address=source_address,
                                              blocksize=blocksize)
        socks_options = kwargs.get('socks_opts')
        self.socks_options = socks_options
        self._create_connection = self.fork_create_connection

    def fork_create_connection(self, address, *args, **extra_kw):
        conn = socks.create_connection(
            address,
            proxy_type=self.socks_options["socks_version"],
            proxy_addr=self.socks_options["proxy_host"],
            proxy_port=self.socks_options["proxy_port"],
            proxy_username=self.socks_options["username"],
            proxy_password=self.socks_options["password"],
            proxy_rdns=self.socks_options["rDNS"],
            timeout=self.timeout,
        )
        return conn

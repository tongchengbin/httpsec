import socket

import socks

from httpsec import httpclient


class HTTPConnection(httpclient.HTTPConnection):
    def __init__(self, *args, **kw):
        # Pre-set source_address.
        self.source_address = kw.get("source_address")

        #: The socket options provided by the user. If no options are
        #: provided, we use the default options.
        # self.socket_options = kw.pop("socket_options", self.default_socket_options)

        # Proxy options provided by the user.
        # self.proxy = kw.pop("proxy", None)
        # self.proxy_config = kw.pop("proxy_config", None)

        httpclient.HTTPConnection.__init__(self, *args, **kw)


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

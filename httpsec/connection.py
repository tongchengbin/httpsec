import socket

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



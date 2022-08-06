from urllib3.connection import HTTPConnection, HTTPSConnection
from http import client
from httpsec.httpclient import HTTPClientResponse


class HttpConnection(HTTPConnection):
    response_class = HTTPClientResponse

    def __init__(self, *args, **kw):
        self._buffer = []
        super().__init__(*args, **kw)
        self.request_header_bytes = bytes()
        self.request_body_bytes = bytes()

    def _send_output(self, message_body=None, encode_chunked=False):
        self.request_header_bytes = b"\r\n".join(self._buffer)
        self.request_body_bytes = message_body
        return super(HttpConnection, self)._send_output(message_body=message_body, encode_chunked=encode_chunked)

    def getresponse(self):
        response = super(HttpConnection, self).getresponse()
        setattr(response, "request_header_bytes", self.request_header_bytes)
        setattr(response, "request_body_bytes", self.request_body_bytes)
        return response


class HttpsConnection(HttpConnection,HTTPSConnection):
    pass

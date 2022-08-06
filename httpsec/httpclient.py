from http.client import HTTPResponse
from http import client


class HTTPClientResponse(HTTPResponse):
    def __init__(self, sock, debuglevel=0, method=None, url=None):
        super().__init__(sock, debuglevel, method, url)
        self.response_header_bytes = bytes()

    def _read_status(self):
        first_line = self.fp.readline(client._MAXLINE + 1)
        self.response_header_bytes += first_line
        line = str(first_line, "iso-8859-1")
        if len(line) > client._MAXLINE:
            raise client.LineTooLong("status line")
        if self.debuglevel > 0:
            print("reply:", repr(line))
        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise client.RemoteDisconnected("Remote end closed connection without"
                                            " response")
        try:
            version, status, reason = line.split(None, 2)
        except ValueError:
            try:
                version, status = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail.
                version = ""
        if not version.startswith("HTTP/"):
            self._close_conn()
            raise client.BadStatusLine(line)

        # The status code is a three-digit number
        try:
            status = int(status)
            if status < 100 or status > 999:
                raise client.BadStatusLine(line)
        except ValueError:
            raise client.BadStatusLine(line)
        return version, status, reason

    def begin(self):
        if self.headers is not None:
            # we've already started reading the response
            return

        # read until we get a non-100 response
        while True:
            version, status, reason = self._read_status()
            if status != client.CONTINUE:
                break
            # skip the header from the 100 response
            while True:
                skip = self.fp.readline(client._MAXLINE + 1)
                if len(skip) > client._MAXLINE:
                    raise client.LineTooLong("header line")
                skip = skip.strip()
                if not skip:
                    break
                if self.debuglevel > 0:
                    print("header:", skip)
        self.code = self.status = status
        self.reason = reason.strip()
        if version in ("HTTP/1.0", "HTTP/0.9"):
            # Some servers might still return "0.9", treat it as 1.0 anyway
            self.version = 10
        elif version.startswith("HTTP/1."):
            self.version = 11  # use HTTP/1.1 code for HTTP/1.x where x>=1
        else:
            raise client.UnknownProtocol(version)

        self.headers = self.msg = self.parse_headers(self.fp)

        if self.debuglevel > 0:
            for hdr, val in self.headers.items():
                print("header:", hdr + ":", val)

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.headers.get("transfer-encoding")
        if tr_enc and tr_enc.lower() == "chunked":
            self.chunked = True
            self.chunk_left = None
        else:
            self.chunked = False

        # will the connection close at the end of the response?
        self.will_close = self._check_close()

        # do we have a Content-Length?
        # NOTE: RFC 2616, S4.4, #3 says we ignore this if tr_enc is "chunked"
        self.length = None
        length = self.headers.get("content-length")

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.headers.get("transfer-encoding")
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
            else:
                if self.length < 0:  # ignore nonsensical negative lengths
                    self.length = None
        else:
            self.length = None

        # does the body have a fixed length? (of zero)
        if (status == client.NO_CONTENT or status == client.NOT_MODIFIED or
                100 <= status < 200 or  # 1xx codes
                self._method == "HEAD"):
            self.length = 0

        # if the connection remains open, and we aren't using chunked, and
        # a content-length was not provided, then assume that the connection
        # WILL close.
        if (not self.will_close and
                not self.chunked and
                self.length is None):
            self.will_close = True

    def parse_headers(self, fp, _class=client.HTTPMessage):
        """Parses only RFC2822 headers from a file pointer.

        email Parser wants to see strings rather than bytes.
        But a TextIOWrapper around self.rfile would buffer too many bytes
        from the stream, bytes which we later need to read as bytes.
        So we read the correct bytes here, as bytes, for email Parser
        to parse.

        """
        headers = []
        while True:
            line = fp.readline(client._MAXLINE + 1)
            self.response_header_bytes += line
            if len(line) > client._MAXLINE:
                raise client.LineTooLong("header line")
            headers.append(line)
            if len(headers) > client._MAXHEADERS:
                raise client.HTTPException("got more than %d headers" % client._MAXHEADERS)
            if line in (b'\r\n', b'\n', b''):
                break
        hstring = b''.join(headers).decode('iso-8859-1')
        return client.email.parser.Parser(_class=_class).parsestr(hstring)

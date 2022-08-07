from urllib3.response import HTTPResponse

DEFAULT_REDIRECT_LIMIT = 30
CONTENT_CHUNK_SIZE = 10 * 1024
ITER_CHUNK_SIZE = 512


class Response(HTTPResponse):
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    def __init__(self, body="",
                 headers=None,
                 status=0,
                 version=0,
                 reason=None,
                 strict=0,
                 preload_content=True,
                 decode_content=True,
                 original_response=None,
                 pool=None,
                 connection=None,
                 msg=None,
                 retries=None,
                 enforce_content_length=False,
                 request_method=None,
                 request_url=None,
                 auto_close=True,
                 **kwargs):
        super().__init__(headers=headers, body=body, status=status, version=version, strict=strict,
                         preload_content=preload_content, decode_content=decode_content,
                         original_response=original_response, pool=pool, connection=connection, retries=retries,
                         msg=msg,
                         enforce_content_length=enforce_content_length, request_method=request_method)
        self.status_code = self.status
        self.version = version
        self.reason = reason
        self.auto_close = auto_close
        self.request_url = request_url

    @property
    def text(self):
        return self.data.decode()

    @property
    def content(self):
        return self.data

    def __str__(self):
        return "status <%d>" % self.status_code

import urllib.parse

from urllib3.util.url import url_attrs


class URL(object):
    __slots__ = url_attrs

    def __init__(self, base_url=None, scheme=None, auth=None, host=None, query=None, port=None, path=None,
                 fragment=None):
        self.auth = self.scheme = self.host = self.port = self.query = self.path = None
        if base_url:
            parsed = urllib.parse.urlparse(base_url)
            self.scheme = parsed.scheme
            self.path = parsed.path
            self.port = parsed.port
            self.host = parsed.hostname
            self.fragment = parsed.fragment
            self.query = parsed.query

        if scheme:
            self.scheme = scheme
        if auth is not None:
            self.auth = auth
        if host is not None:
            self.host = host
        if query is not None:
            self.query = query
        if port is not None:
            self.port = port
        if path is not None:
            self.path = path

        print(2222222, self.auth)
        if self.fragment is not None:
            self.fragment = fragment

    @property
    def hostname(self):
        """For backwards-compatibility with urlparse. We're nice like that."""
        return self.host

    @property
    def request_uri(self):
        """Absolute path including the query string."""
        uri = ""
        if self.path is None:
            uri += "/"
        else:
            uri += self.path
        if self.query is not None:
            uri += "?" + self.query
        return uri

    @property
    def netloc(self):
        """Network location including host and port"""
        if self.port:
            return "%s:%d" % (self.host, self.port)
        return self.host

    @property
    def url(self):
        uri = u""

        # We use "is not None" we want things to happen with empty strings (or 0 port)
        if self.scheme is not None:
            uri += self.scheme + u"://"
        print(11111111111, self.auth)
        if self.auth is not None:
            uri += self.auth + u"@"
        if self.host is not None:
            uri += self.host
        if self.port is not None:
            uri += u":" + str(self.port)
        uri += self.request_uri
        if self.fragment is not None:
            uri += u"#" + self.fragment

        return uri

    def __str__(self):
        return self.url


class SafeURL(URL):
    pass

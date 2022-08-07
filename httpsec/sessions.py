import os
import requests

import httpsec
from httpsec.adapters import HTTPAdapter


class Session(requests.Session):
    def __init__(self):
        super(Session, self).__init__()
        self.adapters.clear()
        self.mount('http', HTTPAdapter())
        self.mount('https', HTTPAdapter())

    def prepare_request(self, request):
        p = super(Session, self).prepare_request(request)
        if issubclass(request.url.__class__, httpsec.URL):
            p.url = request.url.base_url
            p.safe_url = request.url
        return p


def session():
    return Session()

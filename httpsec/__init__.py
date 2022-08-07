from .api import delete, get, head, options, patch, post, put, request

from .url import URL, SafeURL
import requests

__all__ = [
    "delete", "get", "head", "options", "patch", "post", "put", "request", "sessions", "URL", "Session", "SafeURL"
]

from .sessions import Session, session

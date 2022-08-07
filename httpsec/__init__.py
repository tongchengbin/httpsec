from .api import delete, get, head, options, patch, post, put, request

from .url import URL
import requests
__all__ = [
    "delete", "get", "head", "options", "patch", "post", "put", "request", "sessions", "URL", "Session"
]

from .sessions import Session, session

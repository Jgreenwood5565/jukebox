"""Count failed logins per client address and username.

Shared by the login page, the admin login and HTTP basic auth of the API, so
none of them can be used to guess passwords. The counts live in the cache,
which is per process; gunicorn runs a single one (see the Dockerfile).
"""

import hashlib

from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    """The client's address, taken from X-Forwarded-For behind a trusted proxy."""
    address = request.META.get("REMOTE_ADDR", "")
    proxies = settings.JUKEBOX_TRUSTED_PROXIES
    if address in proxies:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
        # proxies append the address they saw, anything left of it came from the client
        for candidate in reversed([part.strip() for part in forwarded]):
            if candidate and candidate not in proxies:
                return candidate
    return address


def _key(request, username):
    client = f"{client_ip(request)}:{username.strip().lower()}"
    return "jukebox:login-attempts:" + hashlib.sha256(client.encode()).hexdigest()


def is_locked(request, username):
    return cache.get(_key(request, username), 0) >= settings.JUKEBOX_LOGIN_ATTEMPTS


def login_failed(request, username):
    key = _key(request, username)
    cache.add(key, 0, settings.JUKEBOX_LOGIN_LOCKOUT)
    try:
        cache.incr(key)
    except ValueError:
        # expired in between
        pass


def login_succeeded(request, username):
    cache.delete(_key(request, username))

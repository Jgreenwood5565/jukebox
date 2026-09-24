from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from . import throttle


class ThrottledBasicAuthentication(BasicAuthentication):
    """HTTP basic auth with the same failed login limit as the login page."""

    def authenticate_credentials(self, userid, password, request=None):
        if throttle.is_locked(request, userid):
            raise AuthenticationFailed("Too many failed login attempts, try again later.")
        try:
            return super().authenticate_credentials(userid, password, request)
        except AuthenticationFailed:
            throttle.login_failed(request, userid)
            raise

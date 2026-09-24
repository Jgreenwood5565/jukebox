from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, override_settings

from jukebox.jukebox_core.throttle import client_ip

from .base import ApiTestBase


class SecurityTest(ApiTestBase):
    @override_settings(JUKEBOX_LOGIN_ATTEMPTS=3)
    def testBasicAuthIsRateLimited(self):
        password = self.passwords[self.user.id]
        self.passwords[self.user.id] = "wrong"
        for _ in range(3):
            self.assertIn(self.httpGet("/api/v1/ping").status_code, (401, 403))
        # locked out, even with the right password
        self.passwords[self.user.id] = password
        self.assertIn(self.httpGet("/api/v1/ping").status_code, (401, 403))

    def testClientAddressBehindTrustedProxy(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.8", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9"
        )
        # not trusted: the forwarded header is ignored
        self.assertEqual(client_ip(request), "10.0.0.8")
        with self.settings(JUKEBOX_TRUSTED_PROXIES=["10.0.0.8"]):
            # the proxy appended the real address, the part before it is made up
            self.assertEqual(client_ip(request), "203.0.113.9")

    def testAdminLoginUsesTheJukeboxLogin(self):
        response = Client().get("/admin/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login?next="))

    def testContentSecurityPolicy(self):
        policy = Client().get("/login")["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)

    def testWeakPasswordsAreRejected(self):
        for password in ("short", "1234567890123", "password123"):
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_password(password)
        validate_password("correct horse battery")

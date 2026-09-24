from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from jukebox.jukebox_core.models import Artist, Queue, Song


@override_settings(
    SOCIAL_AUTH_ENABLED_BACKENDS=["github"],
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class WebTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("listener", "l@example.org", "pw")

    def testIndexRequiresLogin(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/login?next=/", fetch_redirect_response=False)

    def testLoginPage(self):
        response = self.client.get("/login")
        self.assertContains(response, 'href="/login/github/"')
        self.assertContains(response, 'name="password"')

    def testLocalLogin(self):
        response = self.client.post("/login", {"username": "listener", "password": "pw"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def testLocalLoginKeepsNext(self):
        response = self.client.get("/login?next=/admin/")
        self.assertContains(response, 'href="/login/github/?next=/admin/"')
        response = self.client.post(
            "/login", {"username": "listener", "password": "pw", "next": "/admin/"}
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def testLocalLoginRejectsWrongPassword(self):
        response = self.client.post("/login", {"username": "listener", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "login_error")
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(JUKEBOX_LOGIN_ATTEMPTS=3)
    def testLocalLoginIsRateLimited(self):
        for _ in range(3):
            self.client.post("/login", {"username": "listener", "password": "nope"})
        response = self.client.post("/login", {"username": "listener", "password": "pw"})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        # other users are not affected
        User.objects.create_user("other", password="pw2")
        response = self.client.post("/login", {"username": "other", "password": "pw2"})
        self.assertEqual(response.status_code, 302)

    @override_settings(JUKEBOX_LOCAL_LOGIN=False)
    def testLocalLoginCanBeDisabled(self):
        self.assertNotContains(self.client.get("/login"), 'name="password"')
        response = self.client.post("/login", {"username": "listener", "password": "pw"})
        self.assertEqual(response.status_code, 405)
        self.assertNotIn("_auth_user_id", self.client.session)

    def testThemeDefaultsToDark(self):
        self.assertContains(self.client.get("/login"), 'data-theme="dark"')

    def testThemeSwitch(self):
        self.client.force_login(self.user)
        response = self.client.get("/theme/set/light")
        self.assertRedirects(response, "/")
        self.assertContains(self.client.get("/"), 'data-theme="light"')
        self.client.get("/theme/set/neon")
        self.assertContains(self.client.get("/"), 'data-theme="light"')

    def testAddUserCommand(self):
        from unittest import mock

        from django.core.management import call_command

        with mock.patch("getpass.getpass", return_value="correct horse battery"):
            call_command("jukebox_adduser", "dj", "--name", "Dee Jay", "--admin", stdout=None)
        user = User.objects.get(username="dj")
        self.assertTrue(user.check_password("correct horse battery"))
        self.assertEqual(user.get_full_name(), "Dee Jay")
        self.assertTrue(user.is_superuser)

    def testLoginRedirectsAuthenticatedUser(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get("/login"), "/")

    def testIndex(self):
        artist = Artist.objects.create(Name="<script>alert(1)</script>")
        Song.objects.create(Artist=artist, Title="t", Length=1, Filename="/x.mp3", Year=1999)
        self.client.force_login(self.user)

        response = self.client.get("/")
        self.assertContains(response, '<option value="1999">1999</option>', html=True)
        self.assertContains(response, "jquery-3.7.1.min.js")
        self.assertEqual(self.client.session.get_expiry_age(), settings.SESSION_TTL)

    def testWebPlayer(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/"), 'id="listen"')
        with self.settings(JUKEBOX_WEB_PLAYER=False):
            self.assertNotContains(self.client.get("/"), 'id="listen"')

    def testLogoutRequiresPost(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertRedirects(self.client.post("/logout"), "/login")
        self.assertNotIn("_auth_user_id", self.client.session)

    def testLanguage(self):
        response = self.client.get("/language/set/de")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "de")

        response = self.client.get("/language/set/xx")
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def testJavascriptCatalog(self):
        response = self.client.get("/jsi18n/", HTTP_ACCEPT_LANGUAGE="de")
        self.assertContains(response, "Stimme")

    def testStaticFiles(self):
        response = self.client.get("/static/js/music.js")
        self.assertEqual(response.status_code, 200)

    def testFeedShowsMostVotedSong(self):
        artist = Artist.objects.create(Name="artist")
        song_a = Song.objects.create(Artist=artist, Title="first", Length=1, Filename="/a.mp3")
        song_b = Song.objects.create(Artist=artist, Title="popular", Length=1, Filename="/b.mp3")
        other = User.objects.create_user("other")
        Queue.objects.create(Song=song_a).User.add(self.user)
        queue_b = Queue.objects.create(Song=song_b)
        queue_b.User.add(self.user, other)

        response = self.client.get("/feed/")
        self.assertContains(response, "<title>popular</title>")
        self.assertNotContains(response, "<title>first</title>")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class UserManagementTest(TestCase):
    password = "correct horse battery"

    def setUp(self):
        self.admin = User.objects.create_user("boss", password="pw", is_staff=True)
        self.listener = User.objects.create_user("listener", password="pw")
        self.client.force_login(self.admin)

    def testOnlyAdmins(self):
        client = self.client_class()
        self.assertRedirects(
            client.get("/users"), "/login?next=/users", fetch_redirect_response=False
        )
        client.force_login(self.listener)
        self.assertEqual(client.get("/users").status_code, 403)
        self.assertEqual(client.post(f"/users/{self.admin.id}/delete").status_code, 403)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())
        self.assertNotContains(client.get("/"), "Manage users")

    def testList(self):
        response = self.client.get("/users")
        self.assertContains(response, "listener")
        self.assertContains(self.client.get("/"), 'href="/users"')

    def testAddUser(self):
        response = self.client.post(
            "/users",
            {
                "add-username": "newbie",
                "add-name": "New Bie",
                "add-password1": self.password,
                "add-password2": self.password,
                "add-is_staff": "on",
            },
        )
        self.assertRedirects(response, "/users")
        user = User.objects.get(username="newbie")
        self.assertEqual(user.get_full_name(), "New Bie")
        self.assertTrue(user.is_staff and user.is_superuser)
        self.assertTrue(user.check_password(self.password))

    def testAddUserChecksPasswords(self):
        response = self.client.post(
            "/users",
            {"add-username": "newbie", "add-password1": "short", "add-password2": "short"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "too short", status_code=400)
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def testEdit(self):
        response = self.client.post(
            f"/users/{self.listener.id}",
            {f"user{self.listener.id}-name": "Lis Tener", f"user{self.listener.id}-is_staff": "on"},
        )
        self.assertRedirects(response, "/users")
        self.listener.refresh_from_db()
        self.assertEqual(self.listener.get_full_name(), "Lis Tener")
        self.assertTrue(self.listener.is_staff)
        # an unchecked box disables the account
        self.assertFalse(self.listener.is_active)

    def testCantLockYourselfOut(self):
        prefix = f"user{self.admin.id}"
        self.client.post(f"/users/{self.admin.id}", {f"{prefix}-is_active": "on"})
        self.client.post(f"/users/{self.admin.id}", {f"{prefix}-is_staff": "on"})
        self.client.post(f"/users/{self.admin.id}/delete")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_staff and self.admin.is_active)

    def testSetPassword(self):
        prefix = f"password{self.listener.id}"
        response = self.client.post(
            f"/users/{self.listener.id}/password",
            {f"{prefix}-new_password1": self.password, f"{prefix}-new_password2": self.password},
        )
        self.assertRedirects(response, "/users")
        self.listener.refresh_from_db()
        self.assertTrue(self.listener.check_password(self.password))

    def testSetOwnPasswordKeepsYouLoggedIn(self):
        prefix = f"password{self.admin.id}"
        self.client.post(
            f"/users/{self.admin.id}/password",
            {f"{prefix}-new_password1": self.password, f"{prefix}-new_password2": self.password},
        )
        self.assertEqual(self.client.get("/users").status_code, 200)

    def testDelete(self):
        self.assertRedirects(self.client.post(f"/users/{self.listener.id}/delete"), "/users")
        self.assertFalse(User.objects.filter(id=self.listener.id).exists())
        self.assertEqual(self.client.get(f"/users/{self.listener.id}/delete").status_code, 405)

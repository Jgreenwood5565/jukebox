from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from jukebox.jukebox_core.models import Artist, Queue, Song


@override_settings(SOCIAL_AUTH_ENABLED_BACKENDS=["github"])
class WebTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("listener", "l@example.org", "pw")

    def testIndexRequiresLogin(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/login?next=/", fetch_redirect_response=False)

    def testLoginPage(self):
        response = self.client.get("/login")
        self.assertContains(response, 'href="/login/github/"')

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

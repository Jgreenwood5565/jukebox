import base64

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from jukebox.jukebox_core.models import Album, Artist, Genre, Song


# every basic auth request checks the password, keep that fast
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ApiTestBase(TestCase):
    username = "TestUser"
    email = "test@domain.org"
    password = "TestPassword"

    def setUp(self):
        self.passwords = {}
        # register test user and setup auth
        self.user = self.addUser(self.username, self.email, self.password)

    def httpGet(self, url, params=None, user=None):  # noqa: N802
        return Client().get(url, params or {}, HTTP_AUTHORIZATION=self.getAuth(user))

    def httpPost(self, url, params=None, user=None):  # noqa: N802
        return Client().post(url, params or {}, HTTP_AUTHORIZATION=self.getAuth(user))

    def httpDelete(self, url, params=None, user=None):  # noqa: N802
        return Client().delete(url, params or {}, HTTP_AUTHORIZATION=self.getAuth(user))

    def getAuth(self, user=None):  # noqa: N802
        if user is None:
            user = self.user
        credentials = f"{user.username}:{self.passwords[user.id]}".encode()
        return "Basic " + base64.b64encode(credentials).decode("ascii")

    def addArtist(self, name="TestArist"):  # noqa: N802
        return Artist.objects.create(Name=name)

    def addAlbum(self, title="TestTitle"):  # noqa: N802
        return Album.objects.create(Title=title)

    def addGenre(self, name="TestGenre"):  # noqa: N802
        return Genre.objects.create(Name=name)

    def addSong(  # noqa: N802
        self,
        artist,
        album=None,
        genre=None,
        title="TestTitle",
        year=2000,
        length=100,
        filename="/path/to/test.mp3",
    ):
        return Song.objects.create(
            Artist=artist,
            Album=album,
            Genre=genre,
            Title=title,
            Year=year,
            Length=length,
            Filename=filename,
        )

    def addUser(self, username, email, password):  # noqa: N802
        user = User.objects.create_user(username, email, password)
        self.passwords[user.id] = password
        return user

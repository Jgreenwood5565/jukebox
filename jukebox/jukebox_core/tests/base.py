import base64
import struct

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from mutagen.flac import FLAC, Picture

from jukebox.jukebox_core.models import Album, Artist, Genre, Song


# every basic auth request checks the password, keep that fast
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ApiTestBase(TestCase):
    username = "TestUser"
    email = "test@domain.org"
    password = "TestPassword"

    def setUp(self):
        # login attempts, listeners and skip votes
        cache.clear()
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


def write_flac(filename, seconds, picture=None, **tags):
    """Write a FLAC file without audio frames, enough for mutagen and the indexer."""
    # just the STREAMINFO block: 44.1 kHz, stereo, 16 bit and the sample count
    rate = 44100
    info = (rate << 44) | (1 << 41) | (15 << 36) | (rate * seconds)
    streaminfo = struct.pack(">HH", 4096, 4096) + bytes(6) + info.to_bytes(8, "big") + bytes(16)
    with open(filename, "wb") as f:
        # last metadata block, type STREAMINFO
        f.write(b"fLaC" + bytes([0x80]) + len(streaminfo).to_bytes(3, "big") + streaminfo)
    flac = FLAC(filename)
    for key, value in tags.items():
        flac[key] = value
    if picture is not None:
        embedded = Picture()
        embedded.type = 3
        embedded.mime = "image/png"
        embedded.data = picture
        flac.add_picture(embedded)
    flac.save()
    return filename

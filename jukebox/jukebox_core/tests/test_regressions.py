import json
import os
import tempfile
from datetime import timedelta
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.utils import timezone
from mutagen.easyid3 import EasyID3

from jukebox.jukebox_core import api
from jukebox.jukebox_core.api import parse_search_string
from jukebox.jukebox_core.models import Favourite, History, Player, Queue, Song
from jukebox.jukebox_core.utils import FileIndexer

from .base import ApiTestBase

API_URLS = [
    "/api/v1/songs",
    "/api/v1/songs/current",
    "/api/v1/artists",
    "/api/v1/albums",
    "/api/v1/genres",
    "/api/v1/years",
    "/api/v1/history",
    "/api/v1/history/my",
    "/api/v1/queue",
    "/api/v1/favourites",
    "/api/v1/ping",
]


class AuthenticationTest(ApiTestBase):
    def testAnonymousRequestsAreRejected(self):
        client = Client()
        for url in API_URLS:
            with self.subTest(url=url):
                self.assertIn(client.get(url).status_code, (401, 403))
        self.assertIn(client.post("/api/v1/songs/skip").status_code, (401, 403))
        self.assertIn(client.post("/api/v1/queue", {"id": 1}).status_code, (401, 403))

    def testWrongPasswordIsRejected(self):
        self.passwords[self.user.id] = "wrong"
        self.assertIn(self.httpGet("/api/v1/songs").status_code, (401, 403))

    @override_settings(JUKEBOX_WEB_PLAYER=False)
    def testSkipRequiresPost(self):
        self.assertEqual(self.httpGet("/api/v1/songs/skip").status_code, 405)
        with mock.patch("jukebox.jukebox_core.api.os.kill") as kill:
            Player.objects.create(Pid=4242)
            response = self.httpPost("/api/v1/songs/skip")
        self.assertEqual(response.status_code, 204)
        kill.assert_called_once()

    def testSkipForgetsVanishedPlayers(self):
        Player.objects.create(Pid=4242)
        with mock.patch("jukebox.jukebox_core.api.os.kill", side_effect=ProcessLookupError):
            api.songs().skipCurrentSong()
        self.assertFalse(Player.objects.exists())

    def testSessionCsrfIsEnforced(self):
        song = self.addSong(artist=self.addArtist())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.get("/api/v1/queue").status_code, 200)
        self.assertEqual(client.post("/api/v1/queue", {"id": song.id}).status_code, 403)


class InputValidationTest(ApiTestBase):
    def testQueueAddValidation(self):
        self.assertEqual(self.httpPost("/api/v1/queue", {}).status_code, 400)
        self.assertEqual(self.httpPost("/api/v1/queue", {"id": "abc"}).status_code, 400)
        self.assertEqual(self.httpPost("/api/v1/queue", {"id": 999}).status_code, 404)

    def testQueueAddReturnsVoteCount(self):
        song = self.addSong(artist=self.addArtist())
        other = self.addUser("Other", "other@domain.org", "OtherPassword")

        content = json.loads(self.httpPost("/api/v1/queue", {"id": song.id}).content)
        self.assertEqual(content, {"id": song.id, "count": 1})
        content = json.loads(self.httpPost("/api/v1/queue", {"id": song.id}, other).content)
        self.assertEqual(content, {"id": song.id, "count": 2})
        # voting twice doesn't count twice
        content = json.loads(self.httpPost("/api/v1/queue", {"id": song.id}, other).content)
        self.assertEqual(content, {"id": song.id, "count": 2})

    def testQueueRemoveUnknown(self):
        self.assertEqual(self.httpDelete("/api/v1/queue/999").status_code, 404)

    def testFavouriteAddIsIdempotent(self):
        song = self.addSong(artist=self.addArtist())
        self.assertEqual(self.httpPost("/api/v1/favourites", {"id": song.id}).status_code, 201)
        self.assertEqual(self.httpPost("/api/v1/favourites", {"id": song.id}).status_code, 200)
        self.assertEqual(Favourite.objects.count(), 1)

    def testFavouritesArePrivate(self):
        song = self.addSong(artist=self.addArtist())
        other = self.addUser("Other", "other@domain.org", "OtherPassword")
        self.httpPost("/api/v1/favourites", {"id": song.id}, other)

        self.assertEqual(self.httpGet(f"/api/v1/favourites/{song.id}").status_code, 404)
        self.assertEqual(self.httpDelete(f"/api/v1/favourites/{song.id}").status_code, 404)
        self.assertEqual(Favourite.objects.count(), 1)

    def testInvalidListParametersDontFail(self):
        self.addSong(artist=self.addArtist())
        for query in (
            "page=abc",
            "page=-1",
            "count=0",
            "order_by=unknown",
            "order_by=title&order_direction=sideways",
            "filter_genre=999",
            "search_term=year:abc",
            "search_term=genre:unknown",
        ):
            with self.subTest(query=query):
                self.assertEqual(self.httpGet("/api/v1/songs?" + query).status_code, 200)

    def testSearchIsCaseInsensitive(self):
        song = self.addSong(artist=self.addArtist(name="the beatles"), title="yesterday")
        result = json.loads(self.httpGet("/api/v1/songs?search_term=Beatles").content)
        self.assertEqual([item["id"] for item in result["itemList"]], [song.id])


class SearchStringTest(TestCase):
    def parse(self, term):
        return parse_search_string(api.SEARCH_KEYWORDS, term)

    def testPlainTerm(self):
        self.assertEqual(self.parse("  some   words "), {"term": "some words"})

    def testKeywords(self):
        self.assertEqual(
            self.parse("title:help artist:(the beatles) year:1965 rest"),
            {"title": "help", "artist": "the beatles", "year": "1965", "term": "rest"},
        )

    def testNestedBrackets(self):
        self.assertEqual(
            self.parse("title:(a (live) version) artist:b"),
            {"title": "a (live) version", "artist": "b", "term": ""},
        )

    def testUnclosedBracket(self):
        self.assertEqual(self.parse("title:(a b"), {"title": "a b", "term": ""})

    def testKeywordMustStartAWord(self):
        self.assertEqual(self.parse("subtitle:foo"), {"term": "subtitle:foo"})

    def testSearchTermFillsFilters(self):
        genre = ApiTestBase.addGenre(None, name="rock")
        songs_api = api.songs()
        songs_api.set_search_term("genre:Rock year:1999 artist:(foo bar) baz")
        self.assertEqual(songs_api.filter_genre, genre.id)
        self.assertEqual(songs_api.filter_year, 1999)
        self.assertEqual(songs_api.search_artist_name, "foo bar")
        self.assertEqual(songs_api.search_term, "baz")


class PlaybackTest(ApiTestBase):
    def testNextSongSkipsMissingFiles(self):
        missing = self.addSong(artist=self.addArtist(), filename="/does/not/exist.mp3")
        existing = self.addSong(artist=self.addArtist(), filename=__file__)
        api.queue.add(self.queueApi(), missing.id)

        self.assertEqual(api.songs().getNextSong(), existing)
        self.assertFalse(Song.objects.filter(id=missing.id).exists())
        self.assertFalse(Queue.objects.exists())

    def testNextSongRecordsVoters(self):
        song = self.addSong(artist=self.addArtist(), filename=__file__)
        self.queueApi().add(song.id)

        api.songs().getNextSong()
        self.assertEqual(list(History.objects.get().User.all()), [self.user])

    def testNextSongPrefersMostVotes(self):
        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)
        other = self.addUser("Other", "other@domain.org", "OtherPassword")
        self.queueApi().add(song_a.id)
        self.queueApi().add(song_b.id)
        self.queueApi(other).add(song_b.id)

        self.assertEqual(api.songs().getNextSong(), song_b)
        self.assertEqual(api.songs().getNextSong(), song_a)

    def testNextSongOnEmptyLibrary(self):
        with self.assertRaises(Song.DoesNotExist):
            api.songs().getNextSong()

    def testNextSongUsesPreferencesOfActiveUsers(self):
        liked = self.addArtist(name="liked")
        song = self.addSong(artist=liked, filename=__file__)
        for _ in range(5):
            self.addSong(artist=self.addArtist(name="other"), filename=__file__)
        Favourite.objects.create(Song=song, User=self.user)

        client = Client()
        client.force_login(self.user)
        self.assertEqual(api.songs().getNextSong(), song)

    def testCurrentSongRemaining(self):
        song = self.addSong(artist=self.addArtist(), length=300)
        entry = History.objects.create(Song=song)
        History.objects.filter(id=entry.id).update(Created=timezone.now() - timedelta(seconds=100))

        current = json.loads(self.httpGet("/api/v1/songs/current").content)
        self.assertEqual(current["id"], song.id)
        self.assertIsInstance(current["remaining"], int)
        self.assertAlmostEqual(current["remaining"], 200, delta=2)

    def testCurrentSongEmpty(self):
        self.assertEqual(json.loads(self.httpGet("/api/v1/songs/current").content), {})

    def testVoterNameFallsBackToUsername(self):
        song = self.addSong(artist=self.addArtist())
        self.queueApi().add(song.id)
        result = json.loads(self.httpGet("/api/v1/queue").content)
        self.assertEqual(result["itemList"][0]["users"][0]["name"], self.username)

    def testPlayers(self):
        players_api = api.players()
        players_api.add(123)
        self.assertEqual(players_api.remove(123), {"pid": 123})
        # removing an unknown player is fine
        players_api.remove(123)
        self.assertFalse(Player.objects.exists())

    def queueApi(self, user=None):  # noqa: N802
        queue_api = api.queue()
        queue_api.set_user_id((user or self.user).id)
        return queue_api


class FileIndexerTest(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def writeMp3(self, name, **tags):  # noqa: N802
        # a few frames of silence: MPEG-1 layer III, 128 kbit/s, 44.1 kHz
        filename = os.path.join(self.tmp.name, name)
        with open(filename, "wb") as f:
            for _ in range(40):
                f.write(b"\xff\xfb\x90\x64" + b"\x00" * 413)
        id3 = EasyID3()
        for key, value in tags.items():
            id3[key] = value
        id3.save(filename)
        return filename

    def testIndex(self):
        filename = self.writeMp3(
            "song.MP3",
            artist="Artist",
            title="Title",
            album="Album",
            genre="Rock",
            date="2001-05-03",
        )
        song = FileIndexer().index(filename)
        self.assertEqual(song.Artist.Name, "artist")
        self.assertEqual(song.Title, "title")
        self.assertEqual(song.Album.Title, "album")
        self.assertEqual(song.Genre.Name, "rock")
        self.assertEqual(song.Year, 2001)
        # indexing twice is a no-op
        self.assertIsNone(FileIndexer().index(filename))
        self.assertEqual(Song.objects.count(), 1)

    def testSkipsFilesWithoutArtist(self):
        filename = self.writeMp3("a.mp3", title="Title")
        with self.assertLogs("jukebox.jukebox_core.utils", "WARNING"):
            self.assertIsNone(FileIndexer().index(filename))

    def testSkipsBrokenAndUnsupportedFiles(self):
        broken = os.path.join(self.tmp.name, "broken.mp3")
        with open(broken, "wb") as f:
            f.write(b"not an mp3")
        with self.assertLogs("jukebox.jukebox_core.utils", "WARNING"):
            self.assertIsNone(FileIndexer().index(broken))
        self.assertIsNone(FileIndexer().index(os.path.join(self.tmp.name, "cover.jpg")))

    def testDeleteDirectoryKeepsSiblings(self):
        artist = self.addArtist()
        self.addSong(artist=artist, filename="/music/rock/a.mp3")
        self.addSong(artist=artist, filename="/music/rock/sub/b.mp3")
        keep = self.addSong(artist=artist, filename="/music/rockabilly/c.mp3")

        FileIndexer().delete("/music/rock")
        self.assertEqual(list(Song.objects.all()), [keep])

    def testIndexCommand(self):
        from django.core.management import call_command

        self.writeMp3("one.mp3", artist="A", title="One")
        os.mkdir(os.path.join(self.tmp.name, "sub"))
        self.writeMp3("sub/two.mp3", artist="A", title="Two")
        call_command("jukebox_index", path=self.tmp.name, stdout=open(os.devnull, "w"))
        self.assertEqual(Song.objects.count(), 2)

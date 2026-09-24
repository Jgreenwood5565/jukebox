import json
import os
import tempfile
from datetime import timedelta

from django.test import Client, override_settings
from django.utils import timezone

from jukebox.jukebox_core.models import History

from .base import ApiTestBase

AUDIO = bytes(range(256)) * 4


class RadioTest(ApiTestBase):
    def addOnAir(self, song, seconds_ago):  # noqa: N802
        entry = History.objects.create(Song=song)
        History.objects.filter(id=entry.id).update(
            Created=timezone.now() - timedelta(seconds=seconds_ago)
        )
        return entry

    def getCurrent(self):  # noqa: N802
        return json.loads(self.httpGet("/api/v1/songs/current").content)

    def testStartsPlayingWhenNothingPlayed(self):
        song = self.addSong(artist=self.addArtist(), filename=__file__)

        current = self.getCurrent()
        self.assertEqual(current["id"], song.id)
        self.assertEqual(current["historyId"], History.objects.get().id)
        self.assertEqual(current["length"], song.Length)
        self.assertAlmostEqual(current["position"], 0, delta=2)

    def testKeepsSongWhileOnAir(self):
        song = self.addSong(artist=self.addArtist(), length=100, filename=__file__)
        entry = self.addOnAir(song, 40)

        current = self.getCurrent()
        self.assertEqual(current["historyId"], entry.id)
        self.assertAlmostEqual(current["position"], 40, delta=2)
        self.assertAlmostEqual(current["remaining"], 60, delta=2)
        self.assertEqual(History.objects.count(), 1)

    def testPlaysQueuedSongWhenOver(self):
        old = self.addSong(artist=self.addArtist(), length=100, filename=__file__)
        queued = self.addSong(artist=self.addArtist(), filename=__file__)
        entry = self.addOnAir(old, 150)
        self.httpPost("/api/v1/queue", {"id": queued.id})

        current = self.getCurrent()
        self.assertEqual(current["id"], queued.id)
        self.assertNotEqual(current["historyId"], entry.id)
        self.assertEqual(current["votes"], 1)

    def testEmptyLibrary(self):
        self.assertEqual(self.getCurrent(), {})

    def testSkipPlaysNextSong(self):
        song = self.addSong(artist=self.addArtist(), length=100, filename=__file__)
        entry = self.addOnAir(song, 10)

        self.assertEqual(self.httpPost("/api/v1/songs/skip").status_code, 204)
        self.assertEqual(History.objects.count(), 2)
        self.assertNotEqual(self.getCurrent()["historyId"], entry.id)

    @override_settings(JUKEBOX_WEB_PLAYER=False)
    def testDisabledLeavesPlayingToPlugins(self):
        self.addSong(artist=self.addArtist(), filename=__file__)

        self.assertEqual(self.getCurrent(), {})
        self.assertFalse(History.objects.exists())


class StreamTest(ApiTestBase):
    def setUp(self):
        super().setUp()
        handle, self.path = tempfile.mkstemp(suffix=".mp3")
        with os.fdopen(handle, "wb") as file:
            file.write(AUDIO)
        self.addCleanup(os.remove, self.path)
        self.song = self.addSong(artist=self.addArtist(), filename=self.path)
        self.url = f"/api/v1/songs/{self.song.id}/stream"

    def stream(self, **headers):
        client = Client()
        client.force_login(self.user)
        return client.get(self.url, headers=headers)

    def content(self, response):
        return b"".join(response.streaming_content)

    def testWholeFile(self):
        response = self.stream(accept="audio/webm,audio/ogg,audio/*;q=0.9")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Content-Length"], str(len(AUDIO)))
        self.assertEqual(self.content(response), AUDIO)

    def testRanges(self):
        size = len(AUDIO)
        for header, start, end in (
            ("bytes=10-19", 10, 19),
            ("bytes=1000-", 1000, size - 1),
            ("bytes=-5", size - 5, size - 1),
            ("bytes=1020-99999", 1020, size - 1),
        ):
            with self.subTest(header=header):
                response = self.stream(range=header)
                self.assertEqual(response.status_code, 206)
                self.assertEqual(response["Content-Range"], f"bytes {start}-{end}/{size}")
                self.assertEqual(response["Content-Length"], str(end - start + 1))
                self.assertEqual(self.content(response), AUDIO[start : end + 1])

    def testUnsatisfiableRange(self):
        for header in ("bytes=5000-", "bytes=20-10", "bytes=-0"):
            with self.subTest(header=header):
                response = self.stream(range=header)
                self.assertEqual(response.status_code, 416)
                self.assertEqual(response["Content-Range"], f"bytes */{len(AUDIO)}")

    def testUnsupportedRangeSendsWholeFile(self):
        response = self.stream(range="bytes=0-1,5-6")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.content(response), AUDIO)

    def testBasicAuth(self):
        response = self.httpGet(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.content(response), AUDIO)

    def testAnonymousIsRejected(self):
        self.assertIn(Client().get(self.url).status_code, (401, 403))

    def testUnknownSong(self):
        self.assertEqual(self.httpGet("/api/v1/songs/999/stream").status_code, 404)

    def testVanishedFile(self):
        self.song.Filename = self.path + ".gone"
        self.song.save()
        self.assertEqual(self.httpGet(self.url).status_code, 404)

    @override_settings(JUKEBOX_WEB_PLAYER=False)
    def testDisabled(self):
        self.assertEqual(self.httpGet(self.url).status_code, 404)

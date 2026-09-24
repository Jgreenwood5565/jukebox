import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from unittest import mock

from django.test import Client, override_settings
from django.utils import timezone

from jukebox.jukebox_core import media
from jukebox.jukebox_core.models import History

from .base import ApiTestBase, write_flac

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

        response = self.httpPost("/api/v1/songs/skip")
        # the only listener, one vote is a majority
        self.assertEqual(json.loads(response.content), {"skipped": True})
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

    @override_settings(JUKEBOX_TRANSCODE=False)
    def testFlacContentType(self):
        flac = self.path[:-4] + ".flac"
        os.rename(self.path, flac)
        self.addCleanup(os.rename, flac, self.path)
        self.song.Filename = flac
        self.song.save()
        response = self.stream()
        self.assertEqual(response["Content-Type"], "audio/flac")
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


class SkipVoteTest(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.song = self.addSong(artist=self.addArtist(), length=100, filename=__file__)
        self.entry = History.objects.create(Song=self.song)
        self.other = self.addUser("Other", "other@domain.org", "OtherPassword")

    def listen(self, user=None):
        return json.loads(self.httpGet("/api/v1/songs/current", {"listening": 1}, user).content)

    def skip(self, user=None, history_id=None):
        params = {"historyId": history_id or self.entry.id}
        return json.loads(self.httpPost("/api/v1/songs/skip", params, user).content)

    def testNeedsMajorityOfListeners(self):
        self.listen()
        self.listen(self.other)

        result = self.skip()
        self.assertEqual(result["skipped"], False)
        self.assertEqual((result["skipVotes"], result["skipNeeded"]), (1, 2))
        self.assertTrue(result["skipVoted"])
        # voting again doesn't count twice
        self.assertEqual(self.skip()["skipVotes"], 1)
        self.assertEqual(History.objects.count(), 1)

        # others see the votes
        current = self.listen(self.other)
        self.assertEqual((current["skipVotes"], current["skipVoted"]), (1, False))

        self.assertEqual(self.skip(self.other), {"skipped": True})
        self.assertEqual(History.objects.count(), 2)

    def testAdminSkipsRightAway(self):
        self.user.is_staff = True
        self.user.save()
        self.listen()
        self.listen(self.other)
        self.assertEqual(self.skip(), {"skipped": True})

    def testLateVoteDoesntSkipTheNextSong(self):
        self.listen()
        self.listen(self.other)
        self.assertEqual(self.skip(history_id=self.entry.id + 100), {"skipped": False})
        self.assertEqual(self.listen()["skipVotes"], 0)

    def testListenersTimeOut(self):
        self.listen()
        self.listen(self.other)
        with mock.patch("jukebox.jukebox_core.api.time.time", return_value=10**10):
            # the other listener went away, the vote alone is a majority now
            self.assertEqual(self.skip(), {"skipped": True})


class CoverTest(ApiTestBase):
    def setUp(self):
        super().setUp()
        media.cover_source.cache_clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def addFlac(self, name="song.flac", picture=None):  # noqa: N802
        path = write_flac(os.path.join(self.tmp.name, name), 100, picture=picture)
        return self.addSong(artist=self.addArtist(), filename=path, length=100)

    def testEmbeddedCover(self):
        song = self.addFlac(picture=b"embedded png")
        response = self.httpGet(f"/api/v1/songs/{song.id}/cover")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, b"embedded png")
        self.assertIn("max-age", response["Cache-Control"])

    def testCoverFileNextToTheSong(self):
        song = self.addFlac(picture=b"embedded png")
        with open(os.path.join(self.tmp.name, "Cover.JPG"), "wb") as f:
            f.write(b"folder jpeg")
        response = self.httpGet(f"/api/v1/songs/{song.id}/cover")
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response.content, b"folder jpeg")

    def testNoCover(self):
        song = self.addFlac()
        self.assertEqual(self.httpGet(f"/api/v1/songs/{song.id}/cover").status_code, 404)
        self.assertEqual(self.httpGet("/api/v1/songs/999/cover").status_code, 404)

    def testCurrentSongLinksTheCover(self):
        song = self.addFlac(picture=b"embedded png")
        current = json.loads(self.httpGet("/api/v1/songs/current").content)
        self.assertEqual(current["cover"], f"/api/v1/songs/{song.id}/cover")

    def testCurrentSongWithoutCover(self):
        self.addFlac()
        self.assertIsNone(json.loads(self.httpGet("/api/v1/songs/current").content)["cover"])


def fake_ffmpeg(*args, **kwargs):
    # stands in for ffmpeg, writes some "MP3" data
    return subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'mp3' * 1000)"],
        stdout=subprocess.PIPE,
    )


@mock.patch("jukebox.jukebox_core.media.ffmpeg", return_value="/usr/bin/ffmpeg")
class TranscodeTest(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = write_flac(os.path.join(self.tmp.name, "song.flac"), 100)
        self.song = self.addSong(artist=self.addArtist(), filename=path, length=100)
        self.url = f"/api/v1/songs/{self.song.id}/stream"

    def testCommand(self, ffmpeg):
        command = media.transcode_command("/music/a.flac", 12.5)
        self.assertEqual(command[0], "/usr/bin/ffmpeg")
        self.assertEqual(command[command.index("-ss") + 1], "12.50")
        self.assertEqual(command[command.index("-i") + 1], "/music/a.flac")
        self.assertEqual(command[command.index("-b:a") + 1], "192k")
        self.assertEqual(command[-1], "pipe:1")

    def testStreamsMp3(self, ffmpeg):
        with mock.patch("jukebox.jukebox_core.media.transcode", side_effect=fake_ffmpeg) as run:
            response = self.httpGet(self.url, {"start": "42.5"})
            content = b"".join(response.streaming_content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response["Accept-Ranges"], "none")
        self.assertEqual(content, b"mp3" * 1000)
        run.assert_called_once_with(self.song.Filename, 42.5)

    def testInvalidStart(self, ffmpeg):
        for start in ("abc", "nan", "inf", "-5"):
            with self.subTest(start=start):
                with mock.patch(
                    "jukebox.jukebox_core.media.transcode", side_effect=fake_ffmpeg
                ) as run:
                    response = self.httpGet(self.url, {"start": start})
                    b"".join(response.streaming_content)
                run.assert_called_once_with(self.song.Filename, 0)

    def testMp3IsNotTranscoded(self, ffmpeg):
        self.assertFalse(media.needs_transcoding("/music/song.MP3"))
        self.assertTrue(media.needs_transcoding("/music/song.flac"))
        with self.settings(JUKEBOX_TRANSCODE=False):
            self.assertFalse(media.needs_transcoding("/music/song.flac"))

    def testCurrentSongSaysTranscoded(self, ffmpeg):
        current = json.loads(self.httpGet("/api/v1/songs/current").content)
        self.assertTrue(current["transcoded"])
        with self.settings(JUKEBOX_TRANSCODE=False):
            current = json.loads(self.httpGet("/api/v1/songs/current").content)
            self.assertFalse(current["transcoded"])

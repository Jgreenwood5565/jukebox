import json

from jukebox.jukebox_core import api

from .base import ApiTestBase


# ATTENTION: order tests
# favourites are ordered by insertion date DESC per default
class ApiHistoryTest(ApiTestBase):
    def testIndexEmpty(self):
        result = json.loads(self.httpGet("/api/v1/history").content)
        self.assertEqual(len(result["itemList"]), 0)

    def addSongToQueue(self, song, user=None):
        if user is None:
            user = self.user

        return self.httpPost("/api/v1/queue", {"id": song.id}, user)

    def getNextSong(self):
        songs_api = api.songs()
        return songs_api.getNextSong()

    def testAddAndIndex(self):
        song = self.addSong(artist=self.addArtist(), filename=__file__)

        # check that song is not in history
        result = json.loads(self.httpGet("/api/v1/history").content)
        self.assertEqual(len(result["itemList"]), 0)

        # add to queue and play the song
        self.addSongToQueue(song)
        self.getNextSong()

        # check history
        result = json.loads(self.httpGet("/api/v1/history").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song.id)

    def testAddAndIndexMy(self):
        # register second user
        user = self.addUser("TestUser2", "test2@domain.org", "TestPassword2")

        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)

        # check that song is not in history
        result = json.loads(self.httpGet("/api/v1/history/my").content)
        self.assertEqual(len(result["itemList"]), 0)

        # add to queue and play the song
        self.addSongToQueue(song_a, user)
        self.addSongToQueue(song_b)
        self.getNextSong()

        # overall history contains the song
        result = json.loads(self.httpGet("/api/v1/history").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)

        # my history should still be empty
        result = json.loads(self.httpGet("/api/v1/history/my").content)
        self.assertEqual(len(result["itemList"]), 0)

        # play my song
        self.getNextSong()

        # overall history contains both songs
        result = json.loads(self.httpGet("/api/v1/history").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        # check my history
        result = json.loads(self.httpGet("/api/v1/history/my").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)

    def testIndexOrderByTitle(self):
        song_a = self.addSong(artist=self.addArtist(), title="A Title", filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), title="B Title", filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=title").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=title").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=title&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=title&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByArtist(self):
        song_a = self.addSong(artist=self.addArtist("A Name"), filename=__file__)
        song_b = self.addSong(artist=self.addArtist("B Name"), filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=artist").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=artist").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=artist&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=artist&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByAlbum(self):
        artist = self.addArtist()
        song_a = self.addSong(
            artist=artist, album=self.addAlbum(title="A Title"), filename=__file__
        )
        song_b = self.addSong(
            artist=artist, album=self.addAlbum(title="B Title"), filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=album").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=album").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=album&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=album&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByYear(self):
        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), year=2010, filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=year").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=year").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=year&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=year&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByGenre(self):
        song_a = self.addSong(
            artist=self.addArtist(), genre=self.addGenre(name="A Name"), filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(), genre=self.addGenre(name="B Name"), filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=genre").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=genre").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=genre&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=genre&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByCreated(self):
        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?order_by=created").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(self.httpGet("/api/v1/history/my?order_by=created").content)
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)

        result = json.loads(
            self.httpGet("/api/v1/history?order_by=created&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

        result = json.loads(
            self.httpGet("/api/v1/history/my?order_by=created&order_direction=desc").content
        )
        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertEqual(result["itemList"][1]["id"], song_a.id)

    def testCount(self):
        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)
        song_c = self.addSong(artist=self.addArtist(), filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.addSongToQueue(song_c)
        self.getNextSong()
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history/my?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)
        self.assertEqual(result["itemList"][2]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history/my?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertEqual(result["itemList"][1]["id"], song_b.id)
        self.assertEqual(result["itemList"][2]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)
        song_c = self.addSong(artist=self.addArtist(), filename=__file__)
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.addSongToQueue(song_c)
        self.getNextSong()
        self.getNextSong()
        self.getNextSong()

        result = json.loads(self.httpGet("/api/v1/history?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history/my?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history/my?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/history/my?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

import json

from .base import ApiTestBase


class ApiArtistsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = json.loads(self.httpGet("/api/v1/artists").content)

        self.assertEqual(len(result["itemList"]), 0)

    def testIndex(self):
        artist = self.addArtist()

        result = json.loads(self.httpGet("/api/v1/artists").content)

        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], artist.id)

    def testIndexOrderBy(self):
        artist_a = self.addArtist(name="A Name")
        artist_b = self.addArtist(name="B Name")

        result = json.loads(self.httpGet("/api/v1/artists?order_by=artist").content)

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], artist_a.id)
        self.assertEqual(result["itemList"][1]["id"], artist_b.id)

        result = json.loads(
            self.httpGet("/api/v1/artists?order_by=artist&order_direction=desc").content
        )

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], artist_b.id)
        self.assertEqual(result["itemList"][1]["id"], artist_a.id)

    def testCount(self):
        artist_a = self.addArtist()
        artist_b = self.addArtist()
        artist_c = self.addArtist()

        result = json.loads(self.httpGet("/api/v1/artists?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], artist_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/artists?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["id"], artist_a.id)
        self.assertEqual(result["itemList"][1]["id"], artist_b.id)
        self.assertEqual(result["itemList"][2]["id"], artist_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        artist_a = self.addArtist()
        artist_b = self.addArtist()
        artist_c = self.addArtist()

        result = json.loads(self.httpGet("/api/v1/artists?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], artist_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/artists?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], artist_b.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/artists?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], artist_c.id)
        self.assertFalse(result["hasNextPage"])

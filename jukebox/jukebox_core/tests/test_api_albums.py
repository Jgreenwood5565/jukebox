import json

from .base import ApiTestBase


class ApiAlbumsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = json.loads(self.httpGet("/api/v1/albums").content)

        self.assertEqual(len(result["itemList"]), 0)

    def testIndex(self):
        album = self.addAlbum()

        result = json.loads(self.httpGet("/api/v1/albums").content)

        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], album.id)

    def testIndexOrderByAlbum(self):
        album_a = self.addAlbum(title="A Title")
        album_b = self.addAlbum(title="B Title")

        result = json.loads(self.httpGet("/api/v1/albums?order_by=album").content)

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], album_a.id)
        self.assertEqual(result["itemList"][1]["id"], album_b.id)

        result = json.loads(
            self.httpGet("/api/v1/albums?order_by=album&order_direction=desc").content
        )

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], album_b.id)
        self.assertEqual(result["itemList"][1]["id"], album_a.id)

    def testCount(self):
        album_a = self.addAlbum("AAA")
        album_b = self.addAlbum("BBB")
        album_c = self.addAlbum("CCC")

        result = json.loads(self.httpGet("/api/v1/albums?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], album_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/albums?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["id"], album_a.id)
        self.assertEqual(result["itemList"][1]["id"], album_b.id)
        self.assertEqual(result["itemList"][2]["id"], album_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        album_a = self.addAlbum("AAA")
        album_b = self.addAlbum("BBB")
        album_c = self.addAlbum("CCC")

        result = json.loads(self.httpGet("/api/v1/albums?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], album_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/albums?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], album_b.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/albums?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], album_c.id)
        self.assertFalse(result["hasNextPage"])

import json

from .base import ApiTestBase


class ApiGenresTest(ApiTestBase):
    def testIndexEmpty(self):
        result = json.loads(self.httpGet("/api/v1/genres").content)

        self.assertEqual(len(result["itemList"]), 0)

    def testIndex(self):
        genre = self.addGenre()

        result = json.loads(self.httpGet("/api/v1/genres").content)

        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], genre.id)

    def testIndexOrderBy(self):
        genre_a = self.addGenre(name="A Name")
        genre_b = self.addGenre(name="B Name")

        result = json.loads(self.httpGet("/api/v1/genres?order_by=genre").content)

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], genre_a.id)
        self.assertEqual(result["itemList"][1]["id"], genre_b.id)

        result = json.loads(
            self.httpGet("/api/v1/genres?order_by=genre&order_direction=desc").content
        )

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["id"], genre_b.id)
        self.assertEqual(result["itemList"][1]["id"], genre_a.id)

    def testCount(self):
        genre_a = self.addGenre()
        genre_b = self.addGenre()
        genre_c = self.addGenre()

        result = json.loads(self.httpGet("/api/v1/genres?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], genre_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/genres?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["id"], genre_a.id)
        self.assertEqual(result["itemList"][1]["id"], genre_b.id)
        self.assertEqual(result["itemList"][2]["id"], genre_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        genre_a = self.addGenre()
        genre_b = self.addGenre()
        genre_c = self.addGenre()

        result = json.loads(self.httpGet("/api/v1/genres?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], genre_a.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/genres?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], genre_b.id)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/genres?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["id"], genre_c.id)
        self.assertFalse(result["hasNextPage"])

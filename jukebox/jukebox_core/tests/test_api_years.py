import json

from .base import ApiTestBase


class ApiYearsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = json.loads(self.httpGet("/api/v1/years").content)

        self.assertEqual(len(result["itemList"]), 0)

    def testIndex(self):
        year = 2000
        self.addSong(artist=self.addArtist(), year=year)

        result = json.loads(self.httpGet("/api/v1/years").content)

        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["year"], year)

    def testIndexOrderBy(self):
        year_a = 2000
        year_b = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)

        result = json.loads(self.httpGet("/api/v1/years?order_by=year").content)

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["year"], year_a)
        self.assertEqual(result["itemList"][1]["year"], year_b)

        result = json.loads(
            self.httpGet("/api/v1/years?order_by=year&order_direction=desc").content
        )

        self.assertEqual(len(result["itemList"]), 2)
        self.assertEqual(result["itemList"][0]["year"], year_b)
        self.assertEqual(result["itemList"][1]["year"], year_a)

    def testCount(self):
        year_a = 2000
        year_b = 2005
        year_c = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)
        self.addSong(artist=self.addArtist(), year=year_c)

        result = json.loads(self.httpGet("/api/v1/years?count=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["year"], year_a)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/years?count=3").content)
        self.assertEqual(len(result["itemList"]), 3)
        self.assertEqual(result["itemList"][0]["year"], year_a)
        self.assertEqual(result["itemList"][1]["year"], year_b)
        self.assertEqual(result["itemList"][2]["year"], year_c)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        year_a = 2000
        year_b = 2005
        year_c = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)
        self.addSong(artist=self.addArtist(), year=year_c)

        result = json.loads(self.httpGet("/api/v1/years?count=1&page=1").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["year"], year_a)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/years?count=1&page=2").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["year"], year_b)
        self.assertTrue(result["hasNextPage"])

        result = json.loads(self.httpGet("/api/v1/years?count=1&page=3").content)
        self.assertEqual(len(result["itemList"]), 1)
        self.assertEqual(result["itemList"][0]["year"], year_c)
        self.assertFalse(result["hasNextPage"])

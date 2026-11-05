"""Live tests — hit the real emlakjet.com. Cautious: a handful of requests,
spaced ~0.8s apart by the http layer.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set EMLAKJET_SKIP_LIVE=1)
"""
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from emlakjet_mcp import http as _H
from emlakjet_mcp import listings as _L

pytestmark = pytest.mark.live
SKIP = os.environ.get("EMLAKJET_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="EMLAKJET_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_search_page_parses(self):
        html = _H.fetch_search("satilik", "daire", "istanbul", page=1)
        rows = _L.parse_search(html)
        self.assertGreater(len(rows), 0, "search page should list homes")
        priced = [r for r in rows if r["price_try"]]
        self.assertGreater(len(priced), 0)
        for r in rows[:5]:
            self.assertTrue(r["id"] and r["id"].isdigit())
            self.assertTrue(r["url"].startswith("https://www.emlakjet.com/ilan/"))
        print(f"\nLIVE: {len(rows)} listings on page 1; "
              f"cheapest seen: {min(r['price_try'] for r in priced):,} TRY")

    def test_district_search(self):
        html = _H.fetch_search("satilik", "daire", "istanbul", "kadikoy", page=1)
        rows = _L.parse_search(html)
        self.assertGreater(len(rows), 0)
        for r in rows[:5]:
            self.assertIn("Kadıköy", r["location"])
        print(f"\nLIVE Kadıköy: {len(rows)} listings")

    def test_rent_search(self):
        html = _H.fetch_search("kiralik", "daire", "ankara", page=1)
        rows = _L.parse_search(html)
        self.assertGreater(len(rows), 0)
        print(f"\nLIVE Ankara rent: {len(rows)} listings; "
              f"cheapest: {min(r['price_try'] for r in rows if r['price_try']):,} TRY/mo")

    def test_detail_page_parses(self):
        html = _H.fetch_search("satilik", "daire", "istanbul", page=1)
        rows = _L.parse_search(html)
        self.assertGreater(len(rows), 0)
        d = _L.parse_detail(_H.fetch_detail(rows[0]["url"]))
        self.assertTrue(d["title"])
        self.assertTrue(d["price_try"])
        self.assertGreater(len(d["specs"]), 5)
        self.assertTrue(d["description"])
        print(f"\nLIVE detail: {d['title'][:60]} | {d['price_try']:,} TRY")

    def test_detail_by_id(self):
        d = _L.parse_detail(_H.fetch_detail("20044346"))
        self.assertEqual(d["id"], "20044346")
        self.assertEqual(d["price_try"], 5950000)
        print(f"\nLIVE detail by id: {d['title'][:60]}")

    def test_districts_list(self):
        html = _H.fetch_search("satilik", "daire", "istanbul", page=1)
        districts = _L.parse_districts(html, "istanbul")
        self.assertGreater(len(districts), 20)
        slugs = [x["slug"] for x in districts]
        self.assertIn("kadikoy", slugs)
        self.assertIn("besiktas", slugs)
        print(f"\nLIVE: {len(districts)} Istanbul districts")


if __name__ == "__main__":
    unittest.main()

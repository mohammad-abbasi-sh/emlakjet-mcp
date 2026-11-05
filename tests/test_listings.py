"""Offline tests — parse real captured emlakjet.com fixtures (no network)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from emlakjet_mcp import listings as _L

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _schema_script(doc: dict) -> str:
    return ('<html><head><script id="listing-realestate-schema" '
            f'type="application/ld+json">{json.dumps(doc, ensure_ascii=False)}'
            '</script></head></html>')


def _ldjson_script(doc: dict) -> str:
    return ('<html><head><script type="application/ld+json">'
            f'{json.dumps(doc, ensure_ascii=False)}</script></head></html>')


class TestParseSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((FIX / "search_listings.json").read_text())
        cls.html = _schema_script(cls.doc)

    def test_three_listings_parsed(self):
        rows = _L.parse_search(self.html)
        self.assertEqual(len(rows), 3)

    def test_first_listing_fields(self):
        r = _L.parse_search(self.html)[0]
        self.assertEqual(r["id"], "20062034")
        self.assertEqual(r["price_try"], 1349000)
        self.assertEqual(r["price_currency"], "TRY")
        self.assertEqual(r["rooms"], "Stüdyo")
        self.assertEqual(r["area_m2"], 60)
        self.assertEqual(r["location"], "Cumhuriyet Mahallesi, Esenyurt")
        self.assertEqual(r["floor"], "3. Kat")
        self.assertEqual(r["tag"], "YENİ")
        self.assertTrue(r["url"].startswith("https://www.emlakjet.com/ilan/"))

    def test_second_listing_rooms_and_area(self):
        r = _L.parse_search(self.html)[1]
        self.assertEqual(r["id"], "20046781")
        self.assertEqual(r["rooms"], "3+1")
        self.assertEqual(r["area_m2"], 145)
        self.assertEqual(r["price_try"], 4699000)

    def test_missing_schema_returns_empty(self):
        self.assertEqual(_L.parse_search("<html></html>"), [])

    def test_non_listing_blocks_ignored(self):
        doc = {"@graph": [{"@type": "BreadcrumbList"},
                          {"@type": "RealEstateListing", "name": "x",
                           "offers": {"price": 100, "url": "https://www.emlakjet.com/ilan/x-12345"}}]}
        self.assertEqual(len(_L.parse_search(_schema_script(doc))), 1)


class TestPageSummary(unittest.TestCase):
    def test_count_and_cheapest(self):
        desc = (FIX / "meta_description.txt").read_text()
        html = f'<html><head><meta name="description" content="{desc}"></head></html>'
        s = _L.parse_page_summary(html)
        self.assertEqual(s["total_listings"], 21024)
        self.assertEqual(s["cheapest_price_try"], 310000)

    def test_no_meta_returns_empty(self):
        self.assertEqual(_L.parse_page_summary("<html></html>"), {})


class TestDistricts(unittest.TestCase):
    def test_districts_parsed(self):
        html = (FIX / "districts.html").read_text()
        ds = _L.parse_districts(html, "istanbul")
        self.assertEqual(len(ds), 6)
        slugs = [d["slug"] for d in ds]
        self.assertIn("esenyurt", slugs)
        self.assertIn("beylikduzu", slugs)
        self.assertEqual(len(slugs), len(set(slugs)))  # deduped
        es = [d for d in ds if d["slug"] == "esenyurt"][0]
        self.assertIn("Esenyurt", es["name"])

    def test_other_city_prefix_ignored(self):
        html = ('<a href="/satilik-daire/ankara-cankaya/">Ankara Çankaya</a>'
                '<a href="/satilik-daire/istanbul-kadikoy/">Kadıköy</a>')
        ds = _L.parse_districts(html, "istanbul")
        self.assertEqual([d["slug"] for d in ds], ["kadikoy"])


class TestParseDetail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((FIX / "detail_graph.json").read_text())
        cls.html = _ldjson_script(cls.doc)

    def test_detail_fields(self):
        d = _L.parse_detail(self.html)
        self.assertEqual(d["id"], "20044346")
        self.assertEqual(d["price_try"], 5950000)
        self.assertEqual(d["price_currency"], "TRY")
        self.assertEqual(d["rooms_count"], 3)
        self.assertEqual(d["area_m2"], 95)
        self.assertEqual(d["address"]["district"], "Sancaktepe")
        self.assertEqual(d["address"]["city"], "İstanbul")
        self.assertTrue(d["description"].startswith("Sancaktepe Yenidoğan"))
        self.assertGreater(len(d["description"]), 500)

    def test_detail_specs(self):
        d = _L.parse_detail(self.html)
        self.assertEqual(d["specs"]["Isıtma Tipi"], "Kombi Doğalgaz")
        self.assertEqual(d["specs"]["Krediye Uygunluk"], "Krediye Uygun")
        self.assertEqual(d["specs"]["Site İçerisinde"], "Evet")
        self.assertEqual(d["specs"]["Tapu Durumu"], "Kat Mülkiyeti")
        self.assertGreaterEqual(len(d["specs"]), 10)

    def test_no_data_returns_error(self):
        d = _L.parse_detail("<html></html>")
        self.assertIn("error", d)


class TestFilterListings(unittest.TestCase):
    ROWS = [
        {"rooms": "2+1", "price_try": 1000000, "area_m2": 80},
        {"rooms": "3+1", "price_try": 5000000, "area_m2": 145},
        {"rooms": "Stüdyo", "price_try": 800000, "area_m2": 45},
        {"rooms": "2+1", "price_try": None, "area_m2": None},
    ]

    def test_rooms_filter(self):
        out = _L.filter_listings(self.ROWS, rooms="2+1")
        self.assertEqual(len(out), 2)

    def test_price_band(self):
        out = _L.filter_listings(self.ROWS, min_price=900000,
                                 max_price=2000000)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["price_try"], 1000000)

    def test_min_m2(self):
        out = _L.filter_listings(self.ROWS, min_m2=100)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["rooms"], "3+1")


class TestPriceStats(unittest.TestCase):
    def test_stats_with_per_m2(self):
        rows = [{"price_try": p, "area_m2": a}
                for p, a in [(100, 50), (200, 50), (300, 100), (400, 100)]]
        s = _L.price_stats(rows)
        self.assertEqual(s["count"], 4)
        self.assertEqual(s["min"], 100)
        self.assertEqual(s["max"], 400)
        self.assertEqual(s["median"], 250)
        self.assertEqual(s["average"], 250)
        self.assertEqual(s["median_price_per_m2_try"], 3.5)

    def test_empty(self):
        self.assertEqual(_L.price_stats([]), {"count": 0})

    def test_ignores_missing_prices(self):
        s = _L.price_stats([{"price_try": 100}, {"price_try": None}, {}])
        self.assertEqual(s["count"], 1)


class TestSearchUrlValidation(unittest.TestCase):
    def test_default_url(self):
        from emlakjet_mcp import http as _H
        self.assertEqual(
            _H.search_url(),
            "https://www.emlakjet.com/satilik-daire/istanbul/"
            "?filtreler=ilan-sayisi=50")

    def test_district_and_page(self):
        from emlakjet_mcp import http as _H
        self.assertEqual(
            _H.search_url("kiralik", "daire", "ankara", "cankaya", page=2),
            "https://www.emlakjet.com/kiralik-daire/ankara-cankaya/"
            "?sayfa=2&filtreler=ilan-sayisi=50")

    def test_bad_listing_type_rejected(self):
        from emlakjet_mcp import http as _H
        with self.assertRaises(_H.EmlakjetError):
            _H.search_url("sat", "daire", "istanbul")

    def test_bad_property_type_rejected(self):
        from emlakjet_mcp import http as _H
        with self.assertRaises(_H.EmlakjetError):
            _H.search_url("satilik", "saray", "istanbul")

    def test_bad_slug_rejected(self):
        from emlakjet_mcp import http as _H
        with self.assertRaises(_H.EmlakjetError):
            _H.search_url("satilik", "daire", "../../etc")

    def test_bad_detail_url_rejected(self):
        from emlakjet_mcp import http as _H
        with self.assertRaises(_H.EmlakjetError):
            _H.fetch_detail("https://evil.example.com/ilan/1")


if __name__ == "__main__":
    unittest.main()

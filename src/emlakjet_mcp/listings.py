"""Domain logic: parse emlakjet.com SSR pages into compact dicts (stdlib only).

Data sources (all embedded in the public HTML, no JS needed):
- Search pages: one <script id="listing-realestate-schema"> JSON-LD block
  with a @graph of schema.org RealEstateListing items (id, title, price,
  location, rooms, m2, floor, tag, image, datePosted).
- Detail pages: a JSON-LD @graph with a Product (name, description, image,
  offers.price) and a RealEstateListing (address, itemOffered: rooms,
  floorSize, 14 additional properties, dateModified).
- District browser: plain <a href="/satilik-daire/<city>-<district>/"> links
  on the city search page.
- Page summary: the <meta name="description"> carries total listing count
  and the cheapest price ("21.024 adet ... 310.000 TL'den başlayan").
"""
from __future__ import annotations

import html as _html
import json
import re

_SCHEMA_RE = re.compile(
    r'<script id="listing-realestate-schema"[^>]*>(.*?)</script>', re.S)
_LDJSON_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_META_DESC_RE = re.compile(
    r'<meta name="description" content="([^"]*)"')
_COUNT_RE = re.compile(r"([\d.]+)\s*adet")
_MIN_PRICE_RE = re.compile(r"([\d.]+)\s*TL[‘’']den ba[şs]layan")
_DISTRICT_RE = re.compile(
    r'<a[^>]*href="(/[^"]*-daire/[^"]*?)/?"[^>]*>([^<]*)</a>')
_M2_RE = re.compile(r"([\d.]+)\s*m")


def _num(value) -> int | float | None:
    """Turkish-formatted number ('21.024', 5950000, '145 m²') -> int."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    m = _M2_RE.match(s)
    if m:
        s = m.group(1)
    try:
        return int(s.replace(".", "").replace(",", ""))
    except ValueError:
        return None


def _listing_id(url: str) -> str | None:
    m = re.search(r"-(\d{5,})/?$", url or "")
    return m.group(1) if m else None


def _props(item: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in item.get("additionalProperty") or []:
        if isinstance(p, dict) and p.get("name"):
            out[str(p["name"])] = str(p.get("value", ""))
    return out


def parse_search(html_text: str) -> list[dict]:
    """Parse a search-results page into compact listing dicts."""
    m = _SCHEMA_RE.search(html_text)
    if not m:
        return []
    try:
        doc = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for it in doc.get("@graph") or []:
        if not isinstance(it, dict) or it.get("@type") != "RealEstateListing":
            continue
        offers = it.get("offers") or {}
        url = offers.get("url") or it.get("url") or ""
        props = _props(it)
        out.append({
            "id": _listing_id(url),
            "title": (it.get("name") or "").strip(),
            "price_try": _num(offers.get("price")),
            "price_currency": offers.get("priceCurrency") or "",
            "type": props.get("İlan Tipi", ""),
            "location": props.get("Konum", ""),
            "rooms": props.get("Oda Sayısı", ""),
            "area_m2": _num(props.get("Metrekare")),
            "floor": props.get("Kat", ""),
            "tag": props.get("İlan Etiketi", ""),
            "date_posted": it.get("datePosted") or "",
            "url": url,
            "image": it.get("image") or "",
        })
    return out


def parse_page_summary(html_text: str) -> dict:
    """Total listing count + cheapest price from the meta description."""
    m = _META_DESC_RE.search(html_text)
    if not m:
        return {}
    desc = _html.unescape(m.group(1))
    out: dict = {"description": desc}
    cm = _COUNT_RE.search(desc)
    if cm:
        out["total_listings"] = _num(cm.group(1))
    pm = _MIN_PRICE_RE.search(desc)
    if pm:
        out["cheapest_price_try"] = _num(pm.group(1))
    return out


def parse_districts(html_text: str, city: str, listing_type: str = "satilik",
                    property_type: str = "daire") -> list[dict]:
    """District links for a city search page: slug + display name."""
    prefix = f"/{listing_type}-{property_type}/{city}-"
    seen: dict[str, str] = {}
    for href, text in _DISTRICT_RE.findall(html_text):
        if not href.startswith(prefix):
            continue
        slug = href[len(prefix):].strip("/")
        if slug and slug not in seen:
            seen[slug] = _html.unescape(text).strip()
    return [{"slug": s, "name": n} for s, n in sorted(seen.items())]


def parse_detail(html_text: str) -> dict:
    """Parse a listing detail page into a full detail dict."""
    product: dict = {}
    listing: dict = {}
    for block in _LDJSON_RE.findall(html_text):
        try:
            doc = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and "@graph" in doc:
            for it in doc["@graph"]:
                if not isinstance(it, dict):
                    continue
                if it.get("@type") == "Product":
                    product = it
                elif it.get("@type") == "RealEstateListing":
                    listing = it
    if not product and not listing:
        return {"error": "no listing data found on this page"}
    offers = product.get("offers") or {}
    offered = listing.get("itemOffered") or {}
    floor_size = offered.get("floorSize") or {}
    address = listing.get("address") or {}
    props = _props(offered)
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
    return {
        "id": _listing_id(offers.get("url") or product.get("url") or ""),
        "title": _html.unescape(product.get("name", "")).strip(),
        "price_try": _num(offers.get("price")),
        "price_currency": offers.get("priceCurrency") or "",
        "description": _html.unescape(
            product.get("description", "")).strip(),
        "rooms_count": offered.get("numberOfRooms"),
        "area_m2": _num(floor_size.get("value")),
        "address": {
            "neighbourhood": address.get("streetAddress", ""),
            "district": address.get("addressLocality", ""),
            "city": address.get("addressRegion", ""),
            "country": address.get("addressCountry", ""),
        },
        "updated": listing.get("dateModified") or "",
        "specs": props,
        "images": images[:8],
        "url": offers.get("url") or product.get("url") or "",
    }


def filter_listings(rows: list[dict], rooms: str = "", min_price: int = 0,
                    max_price: int = 0, min_m2: int = 0) -> list[dict]:
    """Client-side filters (the site has no server-side room/price filter
    params): exact rooms match ('2+1', 'Stüdyo'), price band, min area."""
    out = []
    for r in rows:
        if rooms and (r.get("rooms") or "").lower() != rooms.lower():
            continue
        p = r.get("price_try")
        if min_price and (not isinstance(p, (int, float)) or p < min_price):
            continue
        if max_price and (not isinstance(p, (int, float)) or p > max_price):
            continue
        a = r.get("area_m2")
        if min_m2 and (not isinstance(a, (int, float)) or a < min_m2):
            continue
        out.append(r)
    return out


def price_stats(listings: list[dict]) -> dict:
    """Min/max/median/average price (TRY) + median price per m²."""
    prices = sorted(l["price_try"] for l in listings
                    if isinstance(l.get("price_try"), (int, float)))
    if not prices:
        return {"count": 0}
    n = len(prices)
    mid = n // 2
    median = prices[mid] if n % 2 else (prices[mid - 1] + prices[mid]) / 2
    per_m2 = sorted(
        l["price_try"] / l["area_m2"] for l in listings
        if isinstance(l.get("price_try"), (int, float))
        and isinstance(l.get("area_m2"), (int, float)) and l["area_m2"])
    pm_mid = len(per_m2) // 2
    per_m2_median = (per_m2[pm_mid] if len(per_m2) % 2
                     else (per_m2[pm_mid - 1] + per_m2[pm_mid]) / 2
                     ) if per_m2 else None
    return {
        "count": n,
        "currency": "TRY",
        "min": prices[0],
        "max": prices[-1],
        "median": median,
        "average": round(sum(prices) / n, 2),
        "median_price_per_m2_try": (round(per_m2_median, 2)
                                    if per_m2_median is not None else None),
    }

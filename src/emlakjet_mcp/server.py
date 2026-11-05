"""MCP server: unofficial read-only access to emlakjet.com listings."""
from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import listings as _listings

mcp = FastMCP("emlakjet-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for emlakjet.com, Türkiye's real-estate \
portal. Data comes from emlakjet.com's public server-rendered pages: \
search pages carry schema.org RealEstateListing JSON-LD (id, title, price \
in TRY, location, rooms, m², floor, tag), detail pages carry a Product \
plus RealEstateListing JSON-LD (full description, address, 14 spec fields \
such as heating, parking, title deed, elevator, balcony). City slugs look \
like "istanbul", "ankara", "izmir", "antalya"; district slugs like "kadikoy" \
(see emlakjet_list_districts). Rooms are "1+1", "2+1", "3+1" or "Stüdyo". \
Prices are in Turkish Lira (TRY) unless noted. Read-only, no login, no API \
key. Be polite: the server spaces requests ~0.8s apart. Built by Mohammad \
Abbasi (mohammad-abbasi-sh) — Turkey MCP factory.\
"""


def _err(e: Exception) -> str:
    return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def emlakjet_search(listing_type: str = "satilik",
                    property_type: str = "daire",
                    city: str = "istanbul", district: str = "",
                    rooms: str = "", min_price: int = 0,
                    max_price: int = 0, min_m2: int = 0,
                    page: int = 1) -> str:
    """Search real-estate listings. listing_type: "satilik" (for sale) or \
"kiralik" (for rent); property_type: "daire", "konut" or "villa"; city: slug \
like "istanbul"; district: slug like "kadikoy" (optional); rooms: "2+1" \
(optional, exact match); min_price/max_price in TRY, min_m2 in m² \
(optional, applied to the fetched page); page: 1..50. Returns compact listings \
with id, title, price_try, location, rooms, area_m2, floor, tag, URL — plus \
the page summary (total listings on the site for this search, cheapest price)."""
    try:
        html = _http.fetch_search(listing_type, property_type, city,
                                  district, page=page)
        rows = _listings.parse_search(html)
        rows = _listings.filter_listings(rows, rooms=rooms,
                                         min_price=min_price,
                                         max_price=max_price, min_m2=min_m2)
        summary = _listings.parse_page_summary(html)
    except _http.EmlakjetError as e:
        return _err(e)
    return json.dumps(
        {"listing_type": listing_type, "property_type": property_type,
         "city": city, "district": district, "page": page,
         "count": len(rows), "listings": rows, "summary": summary},
        ensure_ascii=False,
    )


@mcp.tool()
def emlakjet_listing_detail(url_or_id: str) -> str:
    """Full detail of one listing: title, price (TRY), description, address \
(neighbourhood/district/city), rooms count, area in m², 14 spec fields \
(heating, parking, title deed, elevator, balcony, usage, loan eligibility…), \
images. url_or_id: the listing URL from emlakjet_search, or its numeric id."""
    try:
        html = _http.fetch_detail(url_or_id)
        d = _listings.parse_detail(html)
    except _http.EmlakjetError as e:
        return _err(e)
    return json.dumps(d, ensure_ascii=False)


@mcp.tool()
def emlakjet_list_districts(city: str = "istanbul",
                            listing_type: str = "satilik",
                            property_type: str = "daire") -> str:
    """Districts of a city with listing pages: slug (use with \
emlakjet_search) and display name. city: slug like "istanbul"."""
    try:
        html = _http.fetch_search(listing_type, property_type, city, page=1)
        districts = _listings.parse_districts(html, city, listing_type,
                                              property_type)
    except _http.EmlakjetError as e:
        return _err(e)
    return json.dumps(
        {"city": city, "count": len(districts), "districts": districts},
        ensure_ascii=False,
    )


@mcp.tool()
def emlakjet_price_stats(listing_type: str = "satilik",
                         property_type: str = "daire",
                         city: str = "istanbul", district: str = "",
                         rooms: str = "", pages: int = 3) -> str:
    """Market stats for a city (and optional district/rooms): count, min, \
max, median and average price (TRY) plus median price per m², across the \
first N search pages (pages: 1..5, default 3; 50 listings per page)."""
    pages = max(1, min(int(pages), 5))
    rows: list[dict] = []
    try:
        for p in range(1, pages + 1):
            html = _http.fetch_search(listing_type, property_type, city,
                                      district, page=p)
            rows.extend(_listings.parse_search(html))
    except _http.EmlakjetError as e:
        return _err(e)
    rows = _listings.filter_listings(rows, rooms=rooms)
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in rows:
        if r.get("id") and r["id"] not in seen:
            seen.add(r["id"])
            deduped.append(r)
    stats = _listings.price_stats(deduped)
    stats.update({"listing_type": listing_type,
                  "property_type": property_type, "city": city,
                  "district": district, "rooms": rooms,
                  "pages_scanned": pages})
    return json.dumps(stats, ensure_ascii=False)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())

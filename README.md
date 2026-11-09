# emlakjet-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/emlakjet-mcp

Unofficial **read-only** MCP server for **emlakjet.com**, Türkiye's real-estate portal — live listing search (for sale / for rent, by city and district), full listing details with description and 14 spec fields, a district browser, and market price stats (including median price per m²).

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with emlakjet.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "emlakjet": {
      "command": "uvx",
      "args": ["emlakjet-mcp"]
    }
  }
}
```

Or run locally: `python -m emlakjet_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `emlakjet_search` | Search listings — `listing_type` "satilik"/"kiralik", `property_type` "daire"/"konut"/"villa", `city` ("istanbul"), `district` ("kadikoy"), `rooms` ("2+1"), `min_price`/`max_price` (TRY), `min_m2`, `page` 1..50 |
| `emlakjet_listing_detail` | Full detail of one listing (URL from search, or numeric id): price, description, address, rooms, m², 14 spec fields, images |
| `emlakjet_list_districts` | Districts of a city with listing pages: slug + display name |
| `emlakjet_price_stats` | Market stats: count, min/max/median/average price (TRY) + median price per m² over N pages |

Example output (`emlakjet_search` / satilik daire, istanbul):

```json
{"listing_type": "satilik", "property_type": "daire", "city": "istanbul",
 "page": 1, "count": 50, "listings": [
  {"id": "20062034", "title": "Yıldırım Yapı'dan Metrobüsün Dibinde …",
   "price_try": 1349000, "rooms": "Stüdyo", "area_m2": 60,
   "location": "Cumhuriyet Mahallesi, Esenyurt", "floor": "3. Kat",
   "url": "https://www.emlakjet.com/ilan/…-20062034"}],
 "summary": {"total_listings": 21024, "cheapest_price_try": 310000}}
```

Example output (`emlakjet_listing_detail` / id 20044346):

```json
{"id": "20044346", "title": "Aciliyetten Sancaktepede Site İçi İskanlı Daire",
 "price_try": 5950000, "price_currency": "TRY", "rooms_count": 3, "area_m2": 95,
 "address": {"neighbourhood": "Merve Mahallesi", "district": "Sancaktepe",
  "city": "İstanbul", "country": "TR"},
 "specs": {"Isıtma Tipi": "Kombi Doğalgaz", "Otopark": "Açık & Kapalı Otopark",
  "Kullanım Durumu": "Mülk Sahibi Oturuyor", "Krediye Uygunluk": "Krediye Uygun",
  "Site İçerisinde": "Evet", "Tapu Durumu": "Kat Mülkiyeti", …}}
```

Example output (`emlakjet_price_stats` / istanbul kadikoy, 1 page):

```json
{"count": 50, "currency": "TRY", "min": 5650000, "max": 48000000,
 "median": 17100000.0, "average": 18228800.0,
 "median_price_per_m2_try": 162792.21, "pages_scanned": 1}
```

Notes:
- Data comes from emlakjet.com's public server-rendered pages (schema.org RealEstateListing/Product JSON-LD) — no key, no login, read-only.
- Room/price/area filters are applied to the fetched page (the site exposes no server-side room/price filter); the search returns up to 50 listings per page.
- The site's sort keys were tested live and do not reorder the server-rendered listings, so no sort parameter is offered — sort the returned listings instead.
- Spec labels are Turkish (Isıtma Tipi, Otopark, Kullanım Durumu, Krediye Uygunluk, Site İçerisinde, Tapu Durumu, Takas, Asansör, Mutfak, Eşya Durumu, Balkon…).
- Requests are spaced ~0.8s apart to stay polite.
- Environments behind an MITM proxy: set `SSL_CERT_FILE` to a CA bundle that trusts the proxy.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_listings.py` — offline, parses real captured fixtures
- `tests/test_live.py` — 6 cautious live requests against emlakjet.com (needs `SSL_CERT_FILE` behind the lab proxy)

## License

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)

"""HTTP layer for emlakjet_mcp — polite reads of public SSR pages.

emlakjet.com serves fully server-rendered pages with no bot wall: listing
data comes from embedded schema.org JSON-LD (RealEstateListing on search
pages, Product + RealEstateListing on detail pages). We keep requests
gentle (one at a time, ~0.8s apart) and read-only.

URL scheme (verified live 2026-11-05):
  /{satilik|kiralik}-{daire|konut|villa}/{city}[-{district}]/   (search)
  ?sayfa=N                     pagination (page 2+)
  ?filtreler=ilan-sayisi=50    50 listings per page (verified)
  /ilan/<slug>-<id>            detail (bare /ilan/<id> redirects there)

NOTE: the site's sort keys (filtreler=siralama=...) were tested live and do
NOT reorder the server-rendered listings, so no sort is offered.
"""
from __future__ import annotations

import os
import re
import time

import httpx

BASE = "https://www.emlakjet.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT = 25.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

LISTING_TYPES = ("satilik", "kiralik")
PROPERTY_TYPES = ("daire", "konut", "villa")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DETAIL_RE = re.compile(r"^https://www\.emlakjet\.com/ilan/[a-z0-9\-]+$")

_last_fetch = 0.0


class EmlakjetError(RuntimeError):
    pass


def _client() -> httpx.Client:
    # NOTE: proxy URL is read from the environment but never logged.
    # trust_env=False because httpx fails to parse bracketed IPv6 entries
    # (e.g. [::1]) that some environments put in no_proxy.
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    # Standard SSL_CERT_FILE convention lets MITM-proxied environments
    # point at a CA bundle that trusts the proxy; default uses certifi,
    # which is correct for normal users.
    verify: object = True
    cafile = os.environ.get("SSL_CERT_FILE")
    if cafile:
        import ssl

        verify = ssl.create_default_context(cafile=cafile)
    return httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"},
        timeout=TIMEOUT,
        proxy=proxy or None,
        verify=verify,
        trust_env=False,
        follow_redirects=True,
    )


def _slug(value: str, what: str) -> str:
    s = value.strip().lower()
    if not _SLUG_RE.fullmatch(s):
        raise EmlakjetError(
            f"bad {what} slug: {value!r} — use lowercase letters, digits "
            "and dashes, e.g. 'istanbul', 'kadikoy'")
    return s


def search_url(listing_type: str = "satilik", property_type: str = "daire",
               city: str = "istanbul", district: str = "",
               page: int = 1) -> str:
    lt = listing_type.strip().lower()
    if lt not in LISTING_TYPES:
        raise EmlakjetError(
            f"listing_type must be one of {LISTING_TYPES}, got {listing_type!r}")
    pt = property_type.strip().lower()
    if pt not in PROPERTY_TYPES:
        raise EmlakjetError(
            f"property_type must be one of {PROPERTY_TYPES}, "
            f"got {property_type!r}")
    city = _slug(city, "city")
    path = f"/{lt}-{pt}/{city}"
    if district:
        path += f"-{_slug(district, 'district')}"
    url = f"{BASE}{path}/"
    params: list[str] = []
    if page and int(page) > 1:
        params.append(f"sayfa={int(page)}")
    # Only ONE filtreler param is allowed (a second one 404s, verified
    # 2026-11-05). NOTE: the site's sort keys (siralama=...) were tested
    # live and do NOT reorder the server-rendered listings, so no sort
    # parameter is offered — callers sort the returned listings instead.
    params.append("filtreler=ilan-sayisi=50")
    return url + "?" + "&".join(params)


def fetch(url: str) -> str:
    """GET a page; raises EmlakjetError on failure or bot-wall."""
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        with _client() as c:
            r = c.get(url)
    except httpx.HTTPError as e:
        raise EmlakjetError(f"network error fetching {url}: {e}") from e
    _last_fetch = time.monotonic()
    if r.status_code != 200:
        raise EmlakjetError(f"emlakjet.com returned HTTP {r.status_code} for {url}")
    text = r.text
    if "PerimeterX" in text or "px-captcha" in text or "Cloudflare" in text:
        raise EmlakjetError("emlakjet.com is showing a bot check for this request")
    return text


def fetch_search(listing_type: str = "satilik", property_type: str = "daire",
                 city: str = "istanbul", district: str = "",
                 page: int = 1) -> str:
    if page is not None and (int(page) < 1 or int(page) > 50):
        raise EmlakjetError("page must be between 1 and 50")
    return fetch(search_url(listing_type, property_type, city, district,
                            page=int(page) if page else 1))


def fetch_detail(url_or_id: str) -> str:
    u = url_or_id.strip()
    if u.isdigit():
        u = f"{BASE}/ilan/{u}"
    elif u.startswith("/"):
        u = BASE + u
    if not _DETAIL_RE.fullmatch(u):
        raise EmlakjetError(
            "detail must be an emlakjet.com /ilan/ listing URL or a numeric "
            "listing id (get one from emlakjet_search first)"
        )
    return fetch(u)

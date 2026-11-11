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

import re
import time


BASE = "https://www.emlakjet.com"

TIMEOUT = 25.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

LISTING_TYPES = ("satilik", "kiralik")
PROPERTY_TYPES = ("daire", "konut", "villa")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DETAIL_RE = re.compile(r"^https://www\.emlakjet\.com/ilan/[a-z0-9\-]+$")

_last_fetch = 0.0


class EmlakjetError(RuntimeError):
    pass





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


from curl_cffi import requests as _r

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport. Added 2026-11-10 (fleet audit fix).
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _r.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise EmlakjetError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise EmlakjetError(f"network error fetching {url}: {last_exc}") from last_exc


def fetch(url: str) -> str:
    """GET a page; raises EmlakjetError on failure or bot-wall."""
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _request(url, _HEADERS)
    except EmlakjetError:
        raise
    except Exception as e:
        raise EmlakjetError(f"network error fetching {url}: {e}") from e
    _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise EmlakjetError(
            "emlakjet.com refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise EmlakjetError(
            "emlakjet.com rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code != 200:
        raise EmlakjetError(f"emlakjet.com returned HTTP {resp.status_code} for {url}")
    text = resp.text
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


def health_check() -> dict:
    """One polite probe of the source site.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `emlakjet_health` tool
    and the daily smoke CI. Added 2026-11-10 (fleet audit fix).
    """
    url = "https://www.emlakjet.com/"
    try:
        fetch(f"{BASE}/")
    except EmlakjetError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}

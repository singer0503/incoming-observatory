"""NASA/JPL CNEOS public-API client — the primary live feed.

Stable, documented, JSON, no API key: https://ssd-api.jpl.nasa.gov/doc/
We cache every response to disk and hash it into provenance, because published
numbers must stay reproducible even as the upstream catalogue updates daily.

Endpoints wrapped:
  - CAD    close-approach data            https://ssd-api.jpl.nasa.gov/doc/cad.html
  - Sentry impact-risk table              https://ssd-api.jpl.nasa.gov/doc/sentry.html
  - Scout  real-time NEOCP hazard         https://ssd-api.jpl.nasa.gov/doc/scout.html
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = "https://ssd-api.jpl.nasa.gov"
CACHE_DIR = Path(__file__).resolve().parents[3] / "cache" / "cneos"


def _cache_key(endpoint: str, params: dict[str, Any]) -> Path:
    raw = endpoint + "?" + json.dumps(params, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{endpoint}_{digest}.json"


def _get(endpoint: str, params: dict[str, Any], *, use_cache: bool = True) -> dict:
    """GET a CNEOS endpoint, caching the raw JSON. Network is only touched on miss."""
    cache_path = _cache_key(endpoint, params)
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text())

    import httpx  # imported lazily so the offline ledger needs no network deps

    url = f"{BASE}/{endpoint}.api"
    # CNEOS fair-use: one request at a time, no parallel hammering.
    resp = httpx.get(url, params=params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    data["_fetched_utc"] = datetime.now(timezone.utc).isoformat()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def close_approaches(date_min: str = "now", date_max: str = "+60", dist_max: str = "0.05") -> dict:
    """Upcoming close approaches within dist_max (au). Default: next 60 days inside 0.05 au."""
    return _get("cad", {"date-min": date_min, "date-max": date_max, "dist-max": dist_max})


def sentry() -> dict:
    """The impact-risk table (objects with a non-zero computed impact probability)."""
    return _get("sentry", {})


def scout() -> dict:
    """Real-time hazard assessment for objects still on the MPC confirmation page (NEOCP)."""
    return _get("scout", {})


def sbdb(sstr: str, *, use_cache: bool = True) -> dict:
    """Small-Body DataBase lookup for one object (orbit elements incl. eccentricity)."""
    return _get("sbdb", {"sstr": sstr}, use_cache=use_cache)


def sbdb_elements(sstr: str, *, use_cache: bool = True) -> dict:
    """Return {'fullname','e','a','q','first_obs','orbit_class'} for one object."""
    d = sbdb(sstr, use_cache=use_cache)
    obj = d.get("object", {})
    orb = d.get("orbit", {})
    els = {e["name"]: e.get("value") for e in orb.get("elements", [])}
    oc = obj.get("orbit_class") or {}
    return {
        "fullname": obj.get("fullname"),
        "e": float(els["e"]) if els.get("e") is not None else None,
        "a": float(els["a"]) if els.get("a") not in (None, "") else None,
        "q": float(els["q"]) if els.get("q") is not None else None,
        "first_obs": orb.get("first_obs"),
        "orbit_class": oc.get("name"),
    }

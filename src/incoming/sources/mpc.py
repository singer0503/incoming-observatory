"""IAU Minor Planet Center — raw discovery observations.

This is the source that lets us *independently recompute* warning time instead of
trusting an agency's announced figure. Every MPC observation carries a precise epoch
(Julian Date); the earliest epoch for an object is its discovery moment. Warning time
is then simply (arrival - first observation).

We fetch via astroquery and cache each object's first-observation result, so a recompute
is reproducible and runs offline once the snapshot exists.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[3] / "cache" / "mpc"


def _slug(designation: str) -> str:
    return designation.replace(" ", "_").replace("/", "-")


def fetch_first_observation(designation: str, *, use_cache: bool = True) -> dict:
    """Return {'designation','first_obs_jd','first_obs_utc','n_obs','fetched_utc','source'}.

    Raises on network/lookup failure so callers can mark the object as unavailable.
    """
    cache_path = CACHE_DIR / f"{_slug(designation)}.json"
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text())

    import warnings

    from astropy.time import Time
    from astroquery.mpc import MPC

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obs = MPC.get_observations(designation)

    # epoch is an astropy Quantity in days (Julian Date); the minimum is the discovery.
    jds = [float(x) for x in obs["epoch"].value]
    first_jd = min(jds)
    first_utc = Time(first_jd, format="jd", scale="utc").to_datetime(timezone.utc)

    rec = {
        "designation": designation,
        "first_obs_jd": first_jd,
        "first_obs_utc": first_utc.isoformat(),
        "n_obs": int(len(jds)),
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "source": "IAU Minor Planet Center via astroquery.mpc.get_observations",
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(rec, indent=2, sort_keys=True))
    return rec

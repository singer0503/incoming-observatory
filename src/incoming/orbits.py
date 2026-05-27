"""Export real orbital elements + positions for the situational map.

Pulls SBDB elements for the top impact-risk objects and the interstellar visitors,
adds the planets (standard J2000 elements), and writes web/data/orbits.json. Each body
carries its osculating elements so the frontend can propagate the *same* Kepler math and
animate on real orbits. Elements are cached to a version-controlled snapshot so the build
is reproducible and runs offline.
"""
from __future__ import annotations

import json
from pathlib import Path

from incoming import ephemeris as eph
from incoming import provenance, triage, warning_time
from incoming.sources import cneos

SNAPSHOT = warning_time.REPO_ROOT / "data" / "sbdb_elements.json"
ALERTS = warning_time.REPO_ROOT / "web" / "data" / "alerts.json"


def _planet_elements(name: str, jd: float) -> dict:
    base, rate = eph._PLANETS[name]
    T = (jd - eph.J2000) / 36525.0
    a, e, i, L, peri, Om = (base[k] + rate[k] * T for k in range(6))
    n = 0.9856076686 / (a ** 1.5)  # mean motion, deg/day
    return {"a": a, "e": e, "i": i, "om": Om, "w": peri - Om,
            "ma": (L - peri + 180) % 360 - 180, "n": n, "epoch": jd}


def fetch_elements(designation: str, *, snap: dict, live: bool) -> dict | None:
    if designation in snap:
        return snap[designation]
    if not live:
        return None
    try:
        d = cneos.sbdb(designation)
        els = {x["name"]: x.get("value") for x in d.get("orbit", {}).get("elements", [])}
        rec = eph.elements_to_dict(els, d.get("orbit", {}).get("epoch"))
        if rec:
            rec["fullname"] = d.get("object", {}).get("fullname")
        snap[designation] = rec
        return rec
    except Exception:
        return None


def build(*, live: bool = False, top_n: int = 40, out_dir: Path | None = None) -> dict:
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    jd = eph.jd_now()
    snap = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {}
    bodies = []

    # planets (always available, no network)
    for name in eph._PLANETS:
        els = _planet_elements(name, jd)
        x, y, z = eph.state_xyz(jd=jd, **els)
        bodies.append({"kind": "planet", "name": name, "elements": els, "xyz_au": [x, y, z]})

    # top impact-risk objects from Sentry
    risk_added = 0
    if ALERTS.exists():
        alerts = json.loads(ALERTS.read_text())
        for o in alerts[:top_n]:
            els = fetch_elements(o["designation"], snap=snap, live=live)
            if not els:
                continue
            x, y, z = eph.state_xyz(jd=jd, **{k: els[k] for k in
                                              ("a", "e", "i", "om", "w", "ma", "n", "epoch")})
            bodies.append({
                "kind": "risk", "name": o.get("fullname") or o["designation"],
                "attrs": {"level": o.get("level"), "palermo_cum": o.get("palermo_cum"),
                          "impact_prob": o.get("impact_prob"), "diameter_km": o.get("diameter_km"),
                          "impact_year_range": o.get("impact_year_range")},
                "elements": {k: els[k] for k in ("a", "e", "i", "om", "w", "ma", "n", "epoch")},
                "xyz_au": [x, y, z]})
            risk_added += 1

    # interstellar visitors
    iso_added = 0
    for des in triage.KNOWN_ISO:
        els = fetch_elements(des, snap=snap, live=live)
        if not els:
            continue
        core = {k: els[k] for k in ("a", "e", "i", "om", "w", "ma", "n", "epoch")}
        x, y, z = eph.state_xyz(jd=jd, **core)
        bodies.append({"kind": "interstellar", "name": els.get("fullname") or des,
                       "attrs": {"e": els["e"]}, "elements": core, "xyz_au": [x, y, z]})
        iso_added += 1

    if live:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(snap, indent=2, sort_keys=True))

    payload = {"epoch_jd": jd, "n_bodies": len(bodies), "bodies": bodies}
    text = json.dumps(payload, indent=2)
    web = warning_time.REPO_ROOT / "web" / "data"
    web.mkdir(parents=True, exist_ok=True)
    (web / "orbits.json").write_text(text)
    (out_dir / "orbits.json").write_text(text)

    inputs = {}
    if SNAPSHOT.exists():
        inputs["sbdb_elements.json"] = provenance.sha256_file(SNAPSHOT)
    provenance.write(provenance.build_provenance(input_hashes=inputs),
                     out_dir / "provenance_orbits.json")
    print(f"  orbits -> {web / 'orbits.json'}")
    print(f"  {len(eph._PLANETS)} planets, {risk_added} risk objects, {iso_added} interstellar "
          f"(real Kepler positions at JD {jd:.1f})")
    return payload

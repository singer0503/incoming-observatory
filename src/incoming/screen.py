"""NEOCP firehose screening — auto-triage the newest, unconfirmed objects.

The Minor Planet Center's NEO Confirmation Page (NEOCP) is the firehose of fresh
discoveries that have *not yet* been confirmed or assigned an orbit. This is where an
imminent impactor or an interstellar visitor first shows up — hours after detection,
on an observation arc often well under a day. NASA's Scout computes real-time hazard
scores for these objects; we consume that public feed and screen it openly.

Each object is sorted into a screening category and priority, so a human (or a downstream
alert) can look at the few that matter instead of the whole firehose. This is what makes
the project an *open* analogue of the closed-source Scout/Meerkat screening.

Honest scope: NEOCP arcs are short and orbits are highly uncertain — this is **triage,
not confirmation**. We flag what merits a closer look (and a follow-up `incoming triage`
once the object earns a designation); we do not assert impacts or interstellar origin
from a few hours of data. `vInf` here is the *geocentric* encounter speed, not proof of
interstellar origin.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from incoming import provenance, warning_time
from incoming.sources import cneos

FIXTURE = warning_time.REPO_ROOT / "tests" / "fixtures" / "scout_sample.json"


def _f(x) -> float | None:
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def _diameter_km(H: float | None, albedo: float = 0.14) -> float | None:
    """Rough diameter from absolute magnitude H (standard relation, assumed albedo)."""
    if H is None:
        return None
    return round((1329.0 / math.sqrt(albedo)) * 10 ** (-H / 5.0), 4)


def classify_neocp(obj: dict) -> dict:
    """Pure screening classifier for one Scout/NEOCP object. Testable, no I/O."""
    neo = _f(obj.get("neoScore")) or 0
    pha = _f(obj.get("phaScore")) or 0
    geo = _f(obj.get("geocentricScore")) or 0
    tiss = _f(obj.get("tisserandScore")) or 0
    moid = _f(obj.get("moid"))
    elong = _f(obj.get("elong"))
    vinf = _f(obj.get("vInf"))
    arc = _f(obj.get("arc"))
    H = _f(obj.get("H"))

    if geo >= 50:
        category, rank = "LIKELY-ARTIFACT", 0  # probably an Earth-orbiting object, not an asteroid
    elif pha >= 50 and moid is not None and moid <= 0.05:
        category, rank = "IMPACT-WATCH", 5
    elif pha >= 50:
        category, rank = "PHA-CANDIDATE", 4
    elif tiss >= 50:
        category, rank = "UNUSUAL/COMETARY", 3  # check for hyperbolic orbit as the arc grows
    elif neo >= 50:
        category, rank = "NEO-CANDIDATE", 2
    else:
        category, rank = "LOW-PRIORITY", 1

    flags = []
    if elong is not None and elong < 40:
        flags.append("sunward")  # near the Sun — the blind-spot direction
    if vinf is not None and vinf > 30:
        flags.append("fast(check-hyperbolic)")  # geocentric speed only; not proof of interstellar
    if arc is not None and arc < 0.1:
        flags.append("ultra-short-arc")
    dia = _diameter_km(H)
    if dia is not None and dia >= 0.14:
        flags.append("large(>=140m)")

    return {"category": category, "rank": rank, "flags": flags, "diameter_est_km": dia}


def screen_neocp(*, scout_data: dict | None = None, live: bool = False) -> pd.DataFrame:
    if scout_data is None:
        scout_data = cneos.scout() if live else cneos._get("scout", {}, use_cache=True)
    rows = []
    for o in scout_data.get("data", []):
        c = classify_neocp(o)
        rows.append(
            {
                "object": o.get("objectName"),
                "category": c["category"],
                "rank": c["rank"],
                "neoScore": _f(o.get("neoScore")),
                "phaScore": _f(o.get("phaScore")),
                "moid_au": _f(o.get("moid")),
                "diameter_est_km": c["diameter_est_km"],
                "arc_days": _f(o.get("arc")),
                "nObs": o.get("nObs"),
                "flags": ",".join(c["flags"]),
                "source": "JPL CNEOS Scout (MPC NEOCP)",
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=["object", "category", "rank", "neoScore", "phaScore", "moid_au",
                     "diameter_est_km", "arc_days", "nObs", "flags", "source"]
        )
    return pd.DataFrame(rows).sort_values(["rank", "phaScore"], ascending=False).reset_index(drop=True)


def run(*, live: bool = False, out_dir: Path | None = None) -> pd.DataFrame:
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    df = screen_neocp(live=live)

    counts = df["category"].value_counts().to_dict() if len(df) else {}
    print("=" * 88)
    print("  NEOCP FIREHOSE SCREENING  —  auto-triage of unconfirmed new discoveries (CNEOS Scout)")
    print("=" * 88)
    print(f"  Objects currently on the confirmation page: {len(df)}")
    print(f"  {counts}")
    print("-" * 88)
    print(f"  {'priority':<18}{'object':<12}{'NEO':>5}{'PHA':>5}{'moid(au)':>10}"
          f"{'~D(km)':>9}{'arc(d)':>8}  flags")
    print("-" * 88)
    for _, r in df.iterrows():
        moid = "—" if pd.isna(r["moid_au"]) else f"{r['moid_au']:.3f}"
        dia = "—" if pd.isna(r["diameter_est_km"]) else f"{r['diameter_est_km']:.3f}"
        arc = "—" if pd.isna(r["arc_days"]) else f"{r['arc_days']:.2f}"
        neo = "—" if pd.isna(r["neoScore"]) else f"{int(r['neoScore'])}"
        pha = "—" if pd.isna(r["phaScore"]) else f"{int(r['phaScore'])}"
        print(f"  {r['category']:<18}{str(r['object']):<12}{neo:>5}{pha:>5}{moid:>10}"
              f"{dia:>9}{arc:>8}  {r['flags']}")
    print("=" * 88)
    print("  Triage, not confirmation: NEOCP arcs are hours long and orbits are uncertain.")
    print("  Re-run `incoming triage <desig>` once an object is confirmed and gets an orbit.")
    print("=" * 88)

    payload = df.to_json(orient="records", indent=2)
    (out_dir / "neocp_screen.json").write_text(payload)
    web = warning_time.REPO_ROOT / "web" / "data"
    web.mkdir(parents=True, exist_ok=True)
    (web / "neocp_screen.json").write_text(payload)
    prov = provenance.build_provenance(input_hashes={})
    prov.outputs["fetched_utc"] = datetime.now(timezone.utc).isoformat()
    prov.outputs["mode"] = "live" if live else "cache"
    prov.outputs["n_objects"] = int(len(df))
    provenance.write(prov, out_dir / "provenance_screen.json")
    print(f"  screen -> {out_dir / 'neocp_screen.json'}")
    return df

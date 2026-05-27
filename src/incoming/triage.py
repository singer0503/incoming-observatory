"""Hyperbolic / interstellar triage — "did something just arrive from outside?"

An object bound to the Sun has orbital eccentricity e < 1. An object on an unbound,
hyperbolic path (e > 1) is not gravitationally captured: it came from interstellar space
(or, near e ≈ 1, is a long-period comet that may be marginally hyperbolic from outgassing
or a short observation arc). Only three interstellar objects have ever been confirmed —
1I/'Oumuamua (e≈1.2), 2I/Borisov (e≈3.4), 3I/ATLAS (e≈6.1) — and Vera Rubin/LSST is
expected to turn that trickle into one every few months.

This module classifies objects by eccentricity from JPL SBDB and flags interstellar
candidates. It is the building block for screening the MPC confirmation-page firehose.

Honest scope: eccentricity is the first-order discriminator; the rigorous one is the
hyperbolic excess velocity v∞. We compute v∞ when the semi-major axis is available and
otherwise classify on e alone, stating which we used.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from incoming import provenance, warning_time
from incoming.sources import cneos

SNAPSHOT = warning_time.REPO_ROOT / "data" / "interstellar_objects.json"
KNOWN_ISO = ["1I", "2I", "3I"]  # every confirmed interstellar object, to date

# Sun's gravitational parameter, au^3 / day^2 (for v∞ from a hyperbolic orbit).
_MU_SUN_AU3_DAY2 = 2.959122082855911e-4
_AU_PER_DAY_TO_KM_S = 1731.456837


def classify(e: float | None, a: float | None = None) -> dict:
    """Classify an orbit by eccentricity. Returns label, interstellar flag, v_inf (km/s)."""
    if e is None:
        return {"label": "unknown", "interstellar_candidate": False, "v_inf_km_s": None}

    v_inf = None
    if a is not None and a < 0:  # hyperbolic: v∞ = sqrt(-mu / a)
        v_inf = round(math.sqrt(-_MU_SUN_AU3_DAY2 / a) * _AU_PER_DAY_TO_KM_S, 2)

    if e >= 1.05:
        label, iso = "interstellar (clearly hyperbolic)", True
    elif e > 1.0:
        label, iso = "marginally hyperbolic (long-period comet or short arc?)", False
    elif e >= 0.99:
        label, iso = "near-parabolic (long-period comet)", False
    else:
        label, iso = "bound (solar-system object)", False
    return {"label": label, "interstellar_candidate": iso, "v_inf_km_s": v_inf}


def triage_objects(designations: list[str], *, live: bool = False) -> pd.DataFrame:
    """Classify each designation. live=True fetches from SBDB and updates the snapshot."""
    snap = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {}
    rows = []
    for des in designations:
        rec = snap.get(des)
        if rec is None and live:
            try:
                rec = cneos.sbdb_elements(des)
            except Exception as exc:
                rec = {"error": str(exc)}
            snap[des] = rec
        rec = rec or {"error": "not in snapshot; run with --live"}

        if "e" in rec:
            c = classify(rec.get("e"), rec.get("a"))
            rows.append(
                {
                    "query": des,
                    "fullname": rec.get("fullname"),
                    "e": rec.get("e"),
                    "v_inf_km_s": c["v_inf_km_s"],
                    "orbit_class": rec.get("orbit_class"),
                    "classification": c["label"],
                    "interstellar_candidate": c["interstellar_candidate"],
                }
            )
        else:
            rows.append({"query": des, "fullname": None, "classification": "lookup_failed"})

    if live:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(snap, indent=2, sort_keys=True))
    return pd.DataFrame(rows)


def run(designations: list[str] | None = None, *, live: bool = False,
        out_dir: Path | None = None) -> pd.DataFrame:
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    df = triage_objects(designations or KNOWN_ISO, live=live)

    print("=" * 78)
    print("  HYPERBOLIC / INTERSTELLAR TRIAGE  —  did it come from outside the solar system?")
    print("=" * 78)
    for _, r in df.iterrows():
        flag = "  ⟵ INTERSTELLAR" if r.get("interstellar_candidate") else ""
        e = "—" if pd.isna(r.get("e")) else f"{r['e']:.3f}"
        vinf = "" if pd.isna(r.get("v_inf_km_s")) else f"  v∞≈{r['v_inf_km_s']} km/s"
        print(f"  {str(r.get('fullname') or r['query']):<26} e={e:<7}{vinf}")
        print(f"     -> {r['classification']}{flag}")
    n_iso = int(df.get("interstellar_candidate", pd.Series(dtype=bool)).sum())
    print("-" * 78)
    print(f"  Interstellar candidates flagged: {n_iso} / {len(df)}")
    print("=" * 78)

    payload = df.to_json(orient="records", indent=2)
    (out_dir / "triage.json").write_text(payload)
    web = warning_time.REPO_ROOT / "web" / "data"
    web.mkdir(parents=True, exist_ok=True)
    (web / "triage.json").write_text(payload)

    inputs = {}
    if SNAPSHOT.exists():
        inputs["interstellar_objects.json"] = provenance.sha256_file(SNAPSHOT)
    provenance.write(
        provenance.build_provenance(input_hashes=inputs),
        out_dir / "provenance_triage.json",
    )
    return df

"""Independently recompute warning time from raw MPC discovery observations.

The headline of this project is "how long did we see it coming?" — so the numbers had
better not come from a press release. For every detected impactor we pull the raw MPC
observations, take the earliest epoch as the discovery moment, and compute

    warning_hours = impact_utc - first_observation_utc

then compare against the agency-reported figure. The recomputed values are written to a
*version-controlled snapshot* (data/mpc_first_obs.json) so the result is reproducible and
runs offline thereafter — that curated snapshot is the durable asset, not the code.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from incoming import provenance, warning_time
from incoming.sources import mpc

SNAPSHOT = warning_time.REPO_ROOT / "data" / "mpc_first_obs.json"
# Recompute is "in agreement" with the reported figure within this many hours.
TOLERANCE_H = 2.0


def _parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def load_snapshot(path: Path = SNAPSHOT) -> dict[str, dict]:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_snapshot(snap: dict[str, dict], path: Path = SNAPSHOT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=2, sort_keys=True))


def recompute(*, live: bool = False, out_dir: Path | None = None) -> pd.DataFrame:
    """Build the recomputed-vs-reported comparison.

    live=False : use the committed snapshot only (offline, reproducible).
    live=True  : fetch any missing objects from MPC and update the snapshot.
    """
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = warning_time.load_records()
    impactors = df[df["detected_before_impact"]].copy()
    snap = load_snapshot()

    rows = []
    for _, r in impactors.iterrows():
        desig = r["designation"]
        rec = snap.get(desig)
        if rec is None and live:
            try:
                rec = mpc.fetch_first_observation(desig)
                snap[desig] = rec
            except Exception as e:  # object not resolvable in MPC, or fetch failed
                rec = {"error": str(e)}
                snap[desig] = rec

        status, recomputed, delta, first_utc, n_obs = "no_mpc_data", None, None, None, None
        if rec and "first_obs_utc" in rec:
            first_utc = rec["first_obs_utc"]
            n_obs = rec.get("n_obs")
            recomputed = round(
                (_parse_utc(r["impact_utc"]) - _parse_utc(first_utc)).total_seconds() / 3600.0, 2
            )
            delta = round(recomputed - float(r["warning_hours"]), 2)
            status = "agrees" if abs(delta) <= TOLERANCE_H else "DISCREPANCY"

        rows.append(
            {
                "designation": desig,
                "impact_utc": r["impact_utc"],
                "warning_reported_h": float(r["warning_hours"]),
                "warning_recomputed_h": recomputed,
                "delta_h": delta,
                "first_obs_utc": first_utc,
                "n_obs": n_obs,
                "status": status,
            }
        )

    if live:
        save_snapshot(snap)

    out = pd.DataFrame(rows)
    _print_report(out)
    _write_outputs(out, out_dir, live)
    return out


def _print_report(out: pd.DataFrame) -> None:
    done = out[out["warning_recomputed_h"].notna()]
    print("=" * 78)
    print("  INDEPENDENT RECOMPUTE — warning time from raw MPC discovery observations")
    print("=" * 78)
    hdr = f"  {'object':<11}{'reported':>9}{'recomputed':>12}{'Δ (h)':>8}{'n_obs':>7}  status"
    print(hdr)
    print("  " + "-" * 74)
    for _, r in out.iterrows():
        rc = "—" if pd.isna(r["warning_recomputed_h"]) else f"{r['warning_recomputed_h']:.2f}"
        dl = "—" if pd.isna(r["delta_h"]) else f"{r['delta_h']:+.2f}"
        nb = "—" if pd.isna(r["n_obs"]) else f"{int(r['n_obs'])}"
        print(f"  {r['designation']:<11}{r['warning_reported_h']:>9.1f}{rc:>12}{dl:>8}{nb:>7}  {r['status']}")
    print("  " + "-" * 74)
    if len(done):
        med = done["delta_h"].abs().median()
        print(f"  Independently recomputed {len(done)}/{len(out)} objects from MPC raw observations.")
        print(f"  Median |Δ| vs agency-reported: {med:.2f} h   (tolerance {TOLERANCE_H} h)")
        bad = (done["status"] == "DISCREPANCY").sum()
        print(f"  Agreements: {len(done) - bad}    Discrepancies (> tolerance): {bad}")
    else:
        print("  No snapshot yet — run `incoming recompute --live` to fetch from MPC.")
    print("=" * 78)


def _write_outputs(out: pd.DataFrame, out_dir: Path, live: bool) -> None:
    parquet = out_dir / "warning_recomputed.parquet"
    out.to_parquet(parquet, index=False)
    recomputed_json = out.to_json(orient="records", indent=2)
    (out_dir / "recomputed.json").write_text(recomputed_json)
    # Publish to the web preview so the 3D view can show "independently verified".
    web_data = warning_time.REPO_ROOT / "web" / "data"
    web_data.mkdir(parents=True, exist_ok=True)
    (web_data / "recomputed.json").write_text(recomputed_json)

    inputs = {"known_impactors.csv": provenance.sha256_file(warning_time.DATA_CSV)}
    if SNAPSHOT.exists():
        inputs["mpc_first_obs.json"] = provenance.sha256_file(SNAPSHOT)
    prov = provenance.build_provenance(
        input_hashes=inputs,
        output_hashes={"warning_recomputed.parquet": provenance.sha256_file(parquet)},
    )
    prov.outputs["recompute_mode"] = "live" if live else "snapshot"
    provenance.write(prov, out_dir / "provenance_recompute.json")
    print(f"  data -> {parquet}")
    print(f"  provenance -> {out_dir / 'provenance_recompute.json'}")

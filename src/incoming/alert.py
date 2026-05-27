"""Open imminent-impactor / impact-risk alert layer.

NASA's Scout and ESA's Meerkat already do real-time impact alerting — but both are
**closed-source**. Their *inputs* are public (the JPL CNEOS Sentry and Scout APIs). This
module is the first open, self-hostable, transparent alert layer on top of those feeds:
you can read exactly how severity is assigned, run it yourself, and extend it.

Honest scope: we do **not** recompute orbits or impact probabilities — that is NASA's
rigorous work. We are an open *aggregator and classifier* over their public hazard data,
with provenance on every snapshot, so an alert can always be traced back to its source.

Severity follows the Palermo Technical Scale (the field-standard log measure of impact
hazard vs. background risk) and the Torino Scale (0–10 public-communication scale).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from incoming import provenance, warning_time
from incoming.sources import cneos


def classify_severity(ps_cum: float | None, ts_max: int | None) -> dict:
    """Map Palermo (cumulative) + Torino scale to an alert level. Pure / testable."""
    ps = ps_cum if ps_cum is not None else -99.0
    ts = ts_max if ts_max is not None else 0
    if ps >= 0.0 or ts >= 5:
        level, rank = "SEVERE", 3
    elif ps >= -2.0 or ts >= 1:
        level, rank = "ELEVATED", 2
    else:
        level, rank = "ROUTINE", 1
    return {"level": level, "rank": rank}


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_alerts(*, live: bool = False, limit: int = 15,
                 out_dir: Path | None = None) -> pd.DataFrame:
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    sentry = cneos.sentry() if live else cneos._get("sentry", {}, use_cache=True)
    rows = []
    for o in sentry.get("data", []):
        ps_cum = _f(o.get("ps_cum"))
        ts_max = int(_f(o.get("ts_max")) or 0)
        sev = classify_severity(ps_cum, ts_max)
        rows.append(
            {
                "designation": o.get("des"),
                "fullname": o.get("fullname"),
                "impact_prob": _f(o.get("ip")),
                "palermo_cum": ps_cum,
                "torino_max": ts_max,
                "diameter_km": _f(o.get("diameter")),
                "v_inf_km_s": _f(o.get("v_inf")),
                "impact_year_range": o.get("range"),
                "n_impacts": o.get("n_imp"),
                "level": sev["level"],
                "rank": sev["rank"],
                "source": "JPL CNEOS Sentry",
            }
        )

    df = pd.DataFrame(rows).sort_values(
        ["rank", "palermo_cum"], ascending=[False, False]
    ).reset_index(drop=True)

    _print_alerts(df, limit)
    _write(df, out_dir, live)
    return df


def _print_alerts(df: pd.DataFrame, limit: int) -> None:
    counts = df["level"].value_counts().to_dict()
    print("=" * 84)
    print("  OPEN IMPACT-RISK ALERTS  —  aggregated from JPL CNEOS Sentry (public)")
    print("=" * 84)
    print(f"  Risk-listed objects: {len(df)}   "
          f"SEVERE={counts.get('SEVERE',0)}  ELEVATED={counts.get('ELEVATED',0)}  "
          f"ROUTINE={counts.get('ROUTINE',0)}")
    print("-" * 84)
    print(f"  {'level':<9}{'object':<16}{'Palermo':>9}{'Torino':>7}{'impact_prob':>14}  window")
    print("-" * 84)
    for _, r in df.head(limit).iterrows():
        ip = "—" if pd.isna(r["impact_prob"]) else f"{r['impact_prob']:.2e}"
        pc = "—" if pd.isna(r["palermo_cum"]) else f"{r['palermo_cum']:.2f}"
        print(f"  {r['level']:<9}{str(r['designation']):<16}{pc:>9}{r['torino_max']:>7}"
              f"{ip:>14}  {r['impact_year_range']}")
    print("=" * 84)
    print("  Note: open aggregator over NASA's public hazard data — not an independent")
    print("  orbit/probability computation. Palermo < -2 is routine background risk.")
    print("=" * 84)


def _write(df: pd.DataFrame, out_dir: Path, live: bool) -> None:
    payload = df.to_json(orient="records", indent=2)
    (out_dir / "alerts.json").write_text(payload)
    web = warning_time.REPO_ROOT / "web" / "data"
    web.mkdir(parents=True, exist_ok=True)
    (web / "alerts.json").write_text(payload)
    prov = provenance.build_provenance(input_hashes={})
    prov.outputs["fetched_utc"] = datetime.now(timezone.utc).isoformat()
    prov.outputs["mode"] = "live" if live else "cache"
    prov.outputs["n_objects"] = int(len(df))
    provenance.write(prov, out_dir / "provenance_alert.json")
    print(f"  alerts -> {out_dir / 'alerts.json'}")

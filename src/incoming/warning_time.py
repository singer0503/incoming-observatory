"""The warning-time ledger: how long did we actually see it coming?

Loads the bundled, sourced seed dataset of Earth impactors, validates each record
against the warning-record schema, computes the headline statistics, and emits a
provenance-stamped dataset. This is the offline-runnable core; the live feature
(recomputing warning time from raw MPC discovery observations) builds on this shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from incoming import provenance

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = REPO_ROOT / "data" / "known_impactors.csv"
SCHEMA = REPO_ROOT / "schemas" / "warning_record.schema.json"

BLINDSPOT_LABELS = {
    "sunward": "Sunward (Sun-direction blind spot)",
    "long_period_comet": "Long-period comet",
    "interstellar": "Interstellar object",
    "short_arc": "Found late / short observation arc",
    "none": "Other / unclassified",
}


def load_records(csv_path: Path = DATA_CSV) -> pd.DataFrame:
    """Read the seed dataset (comment lines starting with '#' are skipped)."""
    df = pd.read_csv(csv_path, comment="#", skip_blank_lines=True)
    df["warning_hours"] = pd.to_numeric(df["warning_hours"])
    df["detected_before_impact"] = df["detected_before_impact"].astype(bool)
    return df


def validate_records(df: pd.DataFrame) -> int:
    """Validate every row against schemas/warning_record.schema.json. Returns count."""
    import jsonschema

    schema = json.loads(SCHEMA.read_text())
    for rec in df.to_dict(orient="records"):
        # Optional fields may be NaN from pandas; drop them before validation.
        clean = {k: v for k, v in rec.items() if pd.notna(v)}
        jsonschema.validate(instance=clean, schema=schema)
    return len(df)


def summarize(df: pd.DataFrame) -> dict:
    detected = df[df["detected_before_impact"]]
    return {
        "n_total": int(len(df)),
        "n_detected_before_impact": int(len(detected)),
        "n_missed": int((~df["detected_before_impact"]).sum()),
        "warning_hours_min": float(detected["warning_hours"].min()),
        "warning_hours_median": float(detected["warning_hours"].median()),
        "warning_hours_max": float(detected["warning_hours"].max()),
        "longest_warning_object": detected.loc[detected["warning_hours"].idxmax(), "designation"],
        "blindspot_counts": df["blindspot"].value_counts().to_dict(),
    }


def print_summary(df: pd.DataFrame, s: dict) -> None:
    print("=" * 64)
    print("  HOW BLIND ARE WE?  —  warning time before Earth arrival")
    print("=" * 64)
    print(f"  Objects in ledger:                 {s['n_total']}")
    print(f"  Ever detected BEFORE impact:        {s['n_detected_before_impact']}")
    print(f"  Notable misses (zero warning):      {s['n_missed']}")
    print("-" * 64)
    print("  Warning time, for the ones we DID catch (HOURS, not days):")
    print(f"    shortest : {s['warning_hours_min']:>6.1f} h")
    print(f"    median   : {s['warning_hours_median']:>6.1f} h")
    print(f"    longest  : {s['warning_hours_max']:>6.1f} h   ({s['longest_warning_object']})")
    print("-" * 64)
    print("  Every pre-impact detection, sorted by warning time:")
    det = df[df["detected_before_impact"]].sort_values("warning_hours")
    for _, r in det.iterrows():
        bar = "#" * max(1, round(r["warning_hours"]))
        print(f"    {r['designation']:<12} {r['warning_hours']:>5.1f}h  {bar}")
    print("=" * 64)


def plot(df: pd.DataFrame, out: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    det = df[df["detected_before_impact"]].sort_values("warning_hours")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(det["designation"], det["warning_hours"], color="#c0392b")
    ax.set_xlabel("Warning time before impact (HOURS)")
    ax.set_title("Every asteroid we caught before it hit Earth — and how little warning we had")
    ax.axvline(24, color="#2c3e50", ls="--", lw=1)
    ax.text(24.3, 0.2, "1 day", color="#2c3e50", fontsize=9)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def build_ledger(out_dir: Path = REPO_ROOT / "outputs", make_plot: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_records()
    validate_records(df)
    s = summarize(df)
    print_summary(df, s)

    # Publish the dataset + a machine-readable summary, then stamp provenance.
    parquet_path = out_dir / "warning_times.parquet"
    summary_path = out_dir / "summary.json"
    df.to_parquet(parquet_path, index=False)
    summary_path.write_text(json.dumps(s, indent=2, sort_keys=True))

    ledger_json = df.to_json(orient="records", indent=2)
    (out_dir / "ledger.json").write_text(ledger_json)
    # Also publish into the web preview so the 3D view works out of the box.
    web_data = REPO_ROOT / "web" / "data"
    web_data.mkdir(parents=True, exist_ok=True)
    (web_data / "ledger.json").write_text(ledger_json)

    if make_plot:
        plot(df, out_dir / "warning_times.png")
        print(f"  plot -> {out_dir / 'warning_times.png'}")

    prov = provenance.build_provenance(
        input_hashes={"known_impactors.csv": provenance.sha256_file(DATA_CSV)},
        output_hashes={
            "warning_times.parquet": provenance.sha256_file(parquet_path),
            "summary.json": provenance.sha256_file(summary_path),
        },
    )
    provenance.write(prov, out_dir / "provenance.json")
    print(f"  data -> {parquet_path}")
    print(f"  provenance -> {out_dir / 'provenance.json'}")
    return s

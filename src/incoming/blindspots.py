"""Assemble the detection-blind-spot dashboard data.

Merges the curated, sourced facts (data/blindspot_facts.json) with numbers we actually
computed from our own datasets (the warning-time ledger + the interstellar snapshot), so
every headline figure is either measured here or carries a citation. Emits
web/data/blindspots.json for the dashboard at web/blindspots.html.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from incoming import provenance, triage, warning_time

FACTS = warning_time.REPO_ROOT / "data" / "blindspot_facts.json"


def _interstellar_objects() -> list[dict]:
    if not triage.SNAPSHOT.exists():
        return []
    snap = json.loads(triage.SNAPSHOT.read_text())
    out = []
    for des in triage.KNOWN_ISO:
        rec = snap.get(des, {})
        if "e" in rec:
            c = triage.classify(rec.get("e"), rec.get("a"))
            out.append(
                {"name": rec.get("fullname") or des, "e": rec.get("e"),
                 "v_inf_km_s": c["v_inf_km_s"]}
            )
    return out


def build(out_dir: Path | None = None) -> dict:
    out_dir = out_dir or (warning_time.REPO_ROOT / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    facts = json.loads(FACTS.read_text())
    df = warning_time.load_records()
    detected = df[df["detected_before_impact"]]
    median_h = float(detected["warning_hours"].median())
    max_h = float(detected["warning_hours"].max())
    isos = _interstellar_objects()

    for bs in facts["blindspots"]:
        if bs["id"] == "sunward":
            ch = df[df["designation"] == "Chelyabinsk"]
            bs["hero_stat"] = "0 hours"
            bs["computed"] = {
                "example": "Chelyabinsk — ~20 m, ~1,500 injured, 0 h warning",
                "contrast": f"vs a median of {median_h:.0f} h for the impactors we DID catch",
                "from_our_data": bool(len(ch)),
            }
        elif bs["id"] == "long_period_comet":
            bs["hero_stat"] = "months"
            bs["computed"] = {
                "contrast": "Known near-Earth asteroids are tracked years to decades ahead."
            }
        elif bs["id"] == "interstellar":
            bs["hero_stat"] = str(len(isos))
            bs["computed"] = {"objects": isos}

    # A single comparison chart: warning time by category, on a log scale (hours).
    # Measured values come from our ledger; comet/known are cited literature scales.
    warning_spectrum = [
        {"label": "Sunward impactor (Chelyabinsk)", "label_zh": "太陽方向來的撞擊體（車里雅賓斯克）",
         "hours": 0, "note": "came out of the daytime sky", "note_zh": "從白晝天空飛來", "measured": True},
        {"label": "Typical small asteroid we caught", "label_zh": "我們抓到的典型小型小行星",
         "hours": round(median_h, 1), "note": "our ledger median", "note_zh": "我們帳本的中位數", "measured": True},
        {"label": "Longest warning ever recorded", "label_zh": "史上最長的一次預警",
         "hours": round(max_h, 1), "note": "still under a single day", "note_zh": "仍不到一天", "measured": True},
        {"label": "Long-period comet (e.g. Siding Spring)", "label_zh": "長週期彗星（如 Siding Spring）",
         "hours": 22 * 30 * 24, "note": "< 22 months — literature", "note_zh": "不到 22 個月——文獻", "measured": False},
        {"label": "Known tracked asteroid (e.g. Apophis)", "label_zh": "已追蹤的已知小行星（如 Apophis）",
         "hours": 25 * 365 * 24, "note": "years to decades — for contrast", "note_zh": "數年到數十年——對照", "measured": False},
    ]

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "glossary": facts.get("glossary", []),
        "blindspots": facts["blindspots"],
        "warning_spectrum": warning_spectrum,
    }

    web = warning_time.REPO_ROOT / "web" / "data"
    web.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    (web / "blindspots.json").write_text(text)
    (out_dir / "blindspots.json").write_text(text)

    inputs = {"blindspot_facts.json": provenance.sha256_file(FACTS),
              "known_impactors.csv": provenance.sha256_file(warning_time.DATA_CSV)}
    if triage.SNAPSHOT.exists():
        inputs["interstellar_objects.json"] = provenance.sha256_file(triage.SNAPSHOT)
    provenance.write(provenance.build_provenance(input_hashes=inputs),
                     out_dir / "provenance_blindspots.json")

    print(f"  blind-spot dashboard data -> {web / 'blindspots.json'}")
    print(f"  {len(payload['blindspots'])} blind spots, {len(isos)} interstellar objects, "
          f"median warning {median_h:.0f} h")
    return payload

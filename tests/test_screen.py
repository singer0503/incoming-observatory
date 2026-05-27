"""NEOCP screening tests — pure classifier + fixture-driven, fully offline."""
import json

from incoming import screen


def _fixture():
    return json.loads(screen.FIXTURE.read_text())


def test_impact_watch_high_pha_small_moid():
    obj = {"phaScore": 88, "neoScore": 95, "moid": "0.001", "geocentricScore": 0}
    assert screen.classify_neocp(obj)["category"] == "IMPACT-WATCH"


def test_geocentric_object_is_artifact():
    obj = {"geocentricScore": 90, "phaScore": 80, "moid": "0.001"}
    # an Earth-orbiting object must be deprioritised even with a high PHA score
    assert screen.classify_neocp(obj)["category"] == "LIKELY-ARTIFACT"


def test_cometary_flagged_unusual():
    obj = {"tisserandScore": 70, "neoScore": 60, "phaScore": 20, "geocentricScore": 0}
    assert screen.classify_neocp(obj)["category"] == "UNUSUAL/COMETARY"


def test_sunward_and_fast_flags():
    obj = {"elong": "35", "vInf": "45.0", "neoScore": 60, "geocentricScore": 0,
           "tisserandScore": 70, "phaScore": 20, "arc": "0.4", "H": "18"}
    flags = screen.classify_neocp(obj)["flags"]
    assert "sunward" in flags and "fast(check-hyperbolic)" in flags


def test_screen_fixture_sorts_impact_watch_first():
    df = screen.screen_neocp(scout_data=_fixture())
    assert len(df) == 5
    assert df.iloc[0]["category"] == "IMPACT-WATCH"
    cats = set(df["category"])
    assert {"IMPACT-WATCH", "LIKELY-ARTIFACT", "UNUSUAL/COMETARY"} <= cats

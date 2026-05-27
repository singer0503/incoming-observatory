"""Blind-spot dashboard assembly tests (offline)."""
from incoming import blindspots


def test_three_blindspots_with_sources():
    d = blindspots.build()
    ids = {b["id"] for b in d["blindspots"]}
    assert ids == {"sunward", "long_period_comet", "interstellar"}
    for b in d["blindspots"]:
        assert b["sources"], f"{b['id']} must cite sources"
        assert b.get("plain") and b.get("plain_zh"), f"{b['id']} needs bilingual plain text"


def test_sunward_hero_is_zero_warning():
    d = blindspots.build()
    sun = next(b for b in d["blindspots"] if b["id"] == "sunward")
    assert sun["hero_stat"] == "0 hours"


def test_warning_spectrum_spans_hours_to_years():
    d = blindspots.build()
    hrs = [s["hours"] for s in d["warning_spectrum"]]
    assert min(hrs) == 0
    assert max(hrs) > 24 * 365  # at least one multi-year contrast bar

"""Triage tests — pure classification logic (offline) + snapshot check if present."""
import pytest

from incoming import triage


def test_bound_orbit_not_interstellar():
    c = triage.classify(0.2)
    assert c["interstellar_candidate"] is False
    assert "bound" in c["label"]


def test_clearly_hyperbolic_is_interstellar():
    c = triage.classify(6.14, a=-0.26)  # 3I/ATLAS-like
    assert c["interstellar_candidate"] is True
    assert c["v_inf_km_s"] and c["v_inf_km_s"] > 40  # ~58 km/s


def test_marginally_hyperbolic_not_flagged():
    # e just over 1 (long-period comet / short arc) must NOT be over-claimed as interstellar.
    assert triage.classify(1.001)["interstellar_candidate"] is False


def test_known_interstellar_snapshot():
    if not triage.SNAPSHOT.exists():
        pytest.skip("no interstellar snapshot; run `incoming triage --live`")
    df = triage.triage_objects(triage.KNOWN_ISO, live=False)
    # all three confirmed interstellar objects must be flagged
    assert int(df["interstellar_candidate"].sum()) == 3

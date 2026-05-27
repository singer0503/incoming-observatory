"""Recompute tests — run offline against the committed MPC snapshot.

These verify that the independent (first-observation -> impact) recompute reproduces
known values and stays consistent with the committed data/mpc_first_obs.json snapshot.
No network is used; if the snapshot is missing the tests skip.
"""
import pytest

from incoming import recompute


@pytest.fixture(scope="module")
def out():
    if not recompute.SNAPSHOT.exists():
        pytest.skip("no committed MPC snapshot; run `incoming recompute --live` first")
    return recompute.recompute(live=False)


def test_all_seed_impactors_recomputed(out):
    done = out[out["warning_recomputed_h"].notna()]
    assert len(done) >= 10


def test_2008tc3_recompute_matches_known_value(out):
    row = out.set_index("designation").loc["2008 TC3"]
    # Independently derived from 800+ raw MPC observations: ~20 h.
    assert 19.0 <= row["warning_recomputed_h"] <= 21.0
    assert row["status"] == "agrees"


def test_recompute_is_in_hours_not_days(out):
    done = out[out["warning_recomputed_h"].notna()]
    assert done["warning_recomputed_h"].max() < 24

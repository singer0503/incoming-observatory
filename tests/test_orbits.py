"""Orbits exporter tests — offline, using the committed SBDB element snapshot."""
import math

import pytest

from incoming import orbits


@pytest.fixture(scope="module")
def payload():
    if not orbits.SNAPSHOT.exists():
        pytest.skip("no SBDB element snapshot; run `incoming orbits --live` first")
    return orbits.build(live=False)


def test_planets_present_and_earth_near_one_au(payload):
    earth = next(b for b in payload["bodies"] if b["name"] == "Earth")
    r = math.sqrt(sum(c * c for c in earth["xyz_au"]))
    assert 0.98 <= r <= 1.02


def test_every_body_has_full_elements(payload):
    for b in payload["bodies"]:
        for k in ("a", "e", "i", "om", "w", "ma", "n", "epoch"):
            assert k in b["elements"]


def test_interstellar_are_hyperbolic(payload):
    isos = [b for b in payload["bodies"] if b["kind"] == "interstellar"]
    assert len(isos) >= 1
    assert all(b["elements"]["e"] > 1 for b in isos)

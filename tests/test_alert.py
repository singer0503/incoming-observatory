"""Alert tests — severity classification is a pure, offline function."""
from incoming import alert


def test_routine_background_risk():
    # Palermo well below -2 with Torino 0 is background noise.
    assert alert.classify_severity(-2.69, 0)["level"] == "ROUTINE"


def test_elevated_band():
    assert alert.classify_severity(-1.4, 0)["level"] == "ELEVATED"


def test_severe_on_positive_palermo_or_high_torino():
    assert alert.classify_severity(0.1, 0)["level"] == "SEVERE"
    assert alert.classify_severity(-9.0, 6)["level"] == "SEVERE"


def test_missing_values_default_routine():
    assert alert.classify_severity(None, None)["level"] == "ROUTINE"

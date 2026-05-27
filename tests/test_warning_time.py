"""Smoke + sanity tests: the ledger must load, validate, and match known values."""
from incoming import warning_time


def test_records_load_and_validate():
    df = warning_time.load_records()
    assert len(df) >= 12
    # Every row passes the warning-record JSON schema.
    assert warning_time.validate_records(df) == len(df)


def test_known_warning_values():
    df = warning_time.load_records()
    by_name = df.set_index("designation")["warning_hours"].to_dict()
    # 2008 TC3 was the longest real warning ever: ~20 hours.
    assert 18 <= by_name["2008 TC3"] <= 22
    # Chelyabinsk came from the sunward blind spot: zero warning.
    assert by_name["Chelyabinsk"] == 0


def test_summary_says_warning_is_hours_not_days():
    df = warning_time.load_records()
    s = warning_time.summarize(df)
    # The whole point: even the *longest* real warning is under a day.
    assert s["warning_hours_max"] < 24
    assert s["n_detected_before_impact"] >= 10

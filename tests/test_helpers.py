from datetime import datetime, timedelta

from app.utils.helpers import resolve_date_range_since


def test_resolve_date_range_since_all_time_returns_none():
    assert resolve_date_range_since("All time") is None


def test_resolve_date_range_since_unknown_preset_returns_none():
    assert resolve_date_range_since("Not a real preset") is None


def test_resolve_date_range_since_last_1_day():
    since = resolve_date_range_since("Last 1 day")
    assert since is not None
    expected = datetime.now() - timedelta(days=1)
    assert abs((since - expected).total_seconds()) < 5


def test_resolve_date_range_since_last_3_days():
    since = resolve_date_range_since("Last 3 days")
    assert since is not None
    expected = datetime.now() - timedelta(days=3)
    assert abs((since - expected).total_seconds()) < 5


def test_resolve_date_range_since_last_7_days_is_roughly_a_week_ago():
    since = resolve_date_range_since("Last 7 days")
    assert since is not None
    expected = datetime.now() - timedelta(days=7)
    assert abs((since - expected).total_seconds()) < 5


def test_resolve_date_range_since_last_30_days():
    since = resolve_date_range_since("Last 30 days")
    assert since is not None
    expected = datetime.now() - timedelta(days=30)
    assert abs((since - expected).total_seconds()) < 5

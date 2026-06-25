"""Unit tests for services/report_utils.py — no DB required."""

from datetime import date
from decimal import Decimal

import pytest

from cashpilot.services.report_utils import (
    calculate_comparison_range,
    calculate_date_range,
    calculate_delta,
    calculate_growth_percent,
    calculate_previous_period,
    end_of_month,
    format_date_range,
    get_trend_arrow,
    start_of_month,
    start_of_week,
)


# ---------------------------------------------------------------------------
# calculate_growth_percent
# ---------------------------------------------------------------------------


def test_growth_percent_positive():
    result = calculate_growth_percent(Decimal("110"), Decimal("100"))
    assert result == Decimal("10.0")


def test_growth_percent_negative():
    result = calculate_growth_percent(Decimal("80"), Decimal("100"))
    assert result == Decimal("-20.0")


def test_growth_percent_zero_previous_returns_none():
    assert calculate_growth_percent(Decimal("50"), Decimal("0")) is None


def test_growth_percent_both_zero_returns_none():
    assert calculate_growth_percent(Decimal("0"), Decimal("0")) is None


def test_growth_percent_negative_input_raises():
    with pytest.raises(ValueError):
        calculate_growth_percent(Decimal("-1"), Decimal("100"))
    with pytest.raises(ValueError):
        calculate_growth_percent(Decimal("100"), Decimal("-1"))


def test_growth_percent_precision():
    result = calculate_growth_percent(Decimal("133"), Decimal("100"))
    assert result == Decimal("33.0")


# ---------------------------------------------------------------------------
# get_trend_arrow
# ---------------------------------------------------------------------------


def test_trend_arrow_positive():
    assert get_trend_arrow(Decimal("10")) == "↑"


def test_trend_arrow_negative():
    assert get_trend_arrow(Decimal("-5")) == "↓"


def test_trend_arrow_zero():
    assert get_trend_arrow(Decimal("0")) == "→"


def test_trend_arrow_none():
    assert get_trend_arrow(None) == "→"


# ---------------------------------------------------------------------------
# calculate_delta
# ---------------------------------------------------------------------------


def test_delta_up():
    d = calculate_delta(Decimal("120"), Decimal("100"))
    assert d["direction"] == "up"
    assert d["color"] == "success"
    assert d["percent"] == Decimal("20.0")
    assert d["value"] == Decimal("20")


def test_delta_down():
    d = calculate_delta(Decimal("70"), Decimal("100"))
    assert d["direction"] == "down"
    assert d["color"] == "error"
    assert d["percent"] == Decimal("-30.0")


def test_delta_neutral_within_threshold():
    # 2% change → neutral band (threshold is 3%)
    d = calculate_delta(Decimal("102"), Decimal("100"))
    assert d["direction"] == "neutral"
    assert d["color"] == "neutral"


def test_delta_zero_both():
    d = calculate_delta(Decimal("0"), Decimal("0"))
    assert d["direction"] == "neutral"
    assert d["percent"] == Decimal("0")


def test_delta_previous_zero_current_nonzero():
    d = calculate_delta(Decimal("50"), Decimal("0"))
    assert d["direction"] == "up"
    assert d["percent"] == Decimal("100")


def test_delta_accepts_int():
    d = calculate_delta(110, 100)
    assert d["direction"] == "up"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def test_start_of_week_monday():
    # 2026-06-25 is a Thursday
    d = date(2026, 6, 25)
    assert start_of_week(d) == date(2026, 6, 22)  # Monday


def test_start_of_week_on_monday():
    d = date(2026, 6, 22)
    assert start_of_week(d) == date(2026, 6, 22)


def test_start_of_month():
    assert start_of_month(date(2026, 6, 15)) == date(2026, 6, 1)


def test_end_of_month_june():
    assert end_of_month(date(2026, 6, 1)) == date(2026, 6, 30)


def test_end_of_month_february_leap():
    assert end_of_month(date(2024, 2, 1)) == date(2024, 2, 29)


def test_end_of_month_february_non_leap():
    assert end_of_month(date(2025, 2, 1)) == date(2025, 2, 28)


# ---------------------------------------------------------------------------
# calculate_date_range
# ---------------------------------------------------------------------------


def test_date_range_today(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("today")
    assert start == end == date(2026, 6, 25)


def test_date_range_yesterday(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("yesterday")
    assert start == end == date(2026, 6, 24)


def test_date_range_this_week(monkeypatch):
    # 2026-06-25 is Thursday — week starts Monday 2026-06-22
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("this_week")
    assert start == date(2026, 6, 22)
    assert end == date(2026, 6, 25)


def test_date_range_last_week(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("last_week")
    assert start == date(2026, 6, 15)
    assert end == date(2026, 6, 21)


def test_date_range_custom_valid(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("custom", "2026-06-01", "2026-06-20")
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 20)


def test_date_range_custom_future_raises(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    with pytest.raises(ValueError, match="future"):
        calculate_date_range("custom", "2026-06-01", "2026-12-31")


def test_date_range_custom_inverted_raises(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    with pytest.raises(ValueError):
        calculate_date_range("custom", "2026-06-20", "2026-06-01")


def test_date_range_custom_over_365_raises(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    with pytest.raises(ValueError, match="365"):
        calculate_date_range("custom", "2025-01-01", "2026-06-25")


def test_date_range_unknown_defaults_to_today(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    start, end = calculate_date_range("bogus_view")
    assert start == end == date(2026, 6, 25)


# ---------------------------------------------------------------------------
# calculate_previous_period
# ---------------------------------------------------------------------------


def test_previous_period_single_day():
    prev_from, prev_to = calculate_previous_period(date(2026, 6, 25), date(2026, 6, 25))
    assert prev_to == date(2026, 6, 24)
    assert prev_from == date(2026, 6, 24)


def test_previous_period_week():
    prev_from, prev_to = calculate_previous_period(date(2026, 6, 22), date(2026, 6, 28))
    assert prev_to == date(2026, 6, 21)
    assert prev_from == date(2026, 6, 15)


# ---------------------------------------------------------------------------
# calculate_comparison_range
# ---------------------------------------------------------------------------


def test_comparison_range_today(monkeypatch):
    monkeypatch.setattr(
        "cashpilot.services.report_utils.today_local", lambda: date(2026, 6, 25)
    )
    # today: same weekday last week
    prev_from, prev_to = calculate_comparison_range("today", date(2026, 6, 25), date(2026, 6, 25))
    assert prev_from == prev_to == date(2026, 6, 18)


def test_comparison_range_this_week():
    prev_from, prev_to = calculate_comparison_range("this_week", date(2026, 6, 22), date(2026, 6, 25))
    assert prev_from == date(2026, 6, 15)
    assert prev_to == date(2026, 6, 18)


# ---------------------------------------------------------------------------
# format_date_range
# ---------------------------------------------------------------------------


def test_format_date_range_single_day():
    result = format_date_range(date(2026, 6, 25), date(2026, 6, 25))
    assert result == "Jun 25, 2026"


def test_format_date_range_same_year():
    result = format_date_range(date(2026, 6, 1), date(2026, 6, 30))
    assert "Jun 01" in result
    assert "Jun 30, 2026" in result


def test_format_date_range_cross_year():
    result = format_date_range(date(2025, 12, 25), date(2026, 1, 5))
    assert "2025" in result
    assert "2026" in result

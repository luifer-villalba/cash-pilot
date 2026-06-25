"""Unit tests for services/insights.py — no DB required."""

from datetime import date
from decimal import Decimal

import pytest

from cashpilot.services.insights import (
    FLAG_RATE_ALERT_THRESHOLD,
    GROWTH_ALERT_NEGATIVE_THRESHOLD,
    GROWTH_ALERT_POSITIVE_THRESHOLD,
    detect_revenue_anomalies,
    generate_alerts,
    generate_business_stats_summary,
    generate_daily_summary,
    generate_monthly_summary,
    generate_weekly_summary,
)


# ---------------------------------------------------------------------------
# detect_revenue_anomalies
# ---------------------------------------------------------------------------


def _make_series(values: list[float], start: date | None = None) -> list[dict]:
    start = start or date(2026, 6, 1)
    from datetime import timedelta

    return [
        {"date": start + timedelta(days=i), "revenue": Decimal(str(v)), "has_data": v > 0}
        for i, v in enumerate(values)
    ]


def test_anomaly_high_outlier():
    data = _make_series([1000] * 15 + [9000])  # last day is a clear spike
    anomalies = detect_revenue_anomalies(data)
    assert len(anomalies) == 1
    assert anomalies[0]["direction"] == "high"


def test_anomaly_low_outlier():
    data = _make_series([1000] * 15 + [10])
    anomalies = detect_revenue_anomalies(data)
    assert len(anomalies) == 1
    assert anomalies[0]["direction"] == "low"


def test_no_anomalies_flat_series():
    data = _make_series([1000] * 10)
    assert detect_revenue_anomalies(data) == []


def test_anomaly_requires_minimum_points():
    data = _make_series([1000, 9000, 1000])  # only 3 points — not enough
    assert detect_revenue_anomalies(data) == []


def test_anomaly_skips_zero_revenue_days():
    # zero-revenue days have has_data=False and should be excluded
    data = _make_series([1000] * 10 + [0] * 3 + [9000])
    anomalies = detect_revenue_anomalies(data)
    # Only the actual 9000 spike should be detected, not the zeros
    directions = {a["direction"] for a in anomalies}
    assert "high" in directions
    assert all(a["revenue"] > 0 for a in anomalies)


def test_anomaly_returns_date_and_zscore():
    data = _make_series([1000] * 15 + [9000])
    anomaly = detect_revenue_anomalies(data)[0]
    assert "date" in anomaly
    assert "z_score" in anomaly
    assert anomaly["z_score"] > 0


# ---------------------------------------------------------------------------
# generate_alerts
# ---------------------------------------------------------------------------


def test_alert_revenue_drop():
    alerts = generate_alerts(growth_percent=Decimal("-25"))
    assert any(a["level"] == "error" for a in alerts)
    assert any("25" in a["message"] for a in alerts)


def test_alert_revenue_spike():
    alerts = generate_alerts(growth_percent=Decimal("35"))
    assert any(a["level"] == "success" for a in alerts)


def test_alert_no_alert_for_moderate_growth():
    # 10% growth — below the 30% spike threshold and above the -20% drop threshold
    alerts = generate_alerts(growth_percent=Decimal("10"))
    growth_alerts = [a for a in alerts if "%" in a["message"]]
    assert len(growth_alerts) == 0


def test_alert_high_flag_rate():
    alerts = generate_alerts(flag_rate_percent=FLAG_RATE_ALERT_THRESHOLD + 1)
    assert any(a["level"] == "warning" for a in alerts)
    assert any("sesiones" in a["message"].lower() for a in alerts)


def test_alert_flag_rate_below_threshold():
    alerts = generate_alerts(flag_rate_percent=5.0)
    flag_alerts = [a for a in alerts if "sesiones" in a["message"].lower()]
    assert len(flag_alerts) == 0


def test_alert_anomalies():
    anomaly = {
        "date": date(2026, 6, 15),
        "revenue": Decimal("9000"),
        "z_score": 2.5,
        "direction": "high",
    }
    alerts = generate_alerts(anomalies=[anomaly])
    assert any(a["level"] == "warning" for a in alerts)
    assert any("15 jun" in a["message"] for a in alerts)


def test_alert_anomalies_low():
    anomaly = {
        "date": date(2026, 6, 15),
        "revenue": Decimal("10"),
        "z_score": -2.5,
        "direction": "low",
    }
    alerts = generate_alerts(anomalies=[anomaly])
    assert any("bajas" in a["message"] for a in alerts)


def test_alert_zero_revenue_days():
    alerts = generate_alerts(zero_revenue_days=3)
    assert any("3 días" in a["message"] for a in alerts)


def test_alert_zero_revenue_days_singular():
    alerts = generate_alerts(zero_revenue_days=1)
    assert any("1 día" in a["message"] for a in alerts)


def test_alerts_empty_when_no_issues():
    alerts = generate_alerts()
    assert alerts == []


def test_alerts_multiple_issues():
    alerts = generate_alerts(
        growth_percent=Decimal("-30"),
        flag_rate_percent=20.0,
        zero_revenue_days=2,
    )
    assert len(alerts) >= 3


# ---------------------------------------------------------------------------
# generate_weekly_summary
# ---------------------------------------------------------------------------


def test_weekly_summary_with_growth():
    s = generate_weekly_summary(
        current_week_total=Decimal("7000000"),
        previous_week_total=Decimal("5000000"),
        growth_percent=Decimal("40.0"),
        highest_day={"day_name": "Viernes", "revenue": 1500000},
        lowest_day={"day_name": "Lunes", "revenue": 500000},
        days_with_data=6,
    )
    assert "40.0%" in s
    assert "Viernes" in s
    assert "6 días activos" in s


def test_weekly_summary_decline():
    s = generate_weekly_summary(
        current_week_total=Decimal("3000000"),
        previous_week_total=Decimal("5000000"),
        growth_percent=Decimal("-40.0"),
        highest_day={},
        lowest_day={},
        days_with_data=5,
    )
    assert "menos" in s.lower()


def test_weekly_summary_no_data():
    s = generate_weekly_summary(
        current_week_total=Decimal("0"),
        previous_week_total=Decimal("0"),
        growth_percent=None,
        highest_day={},
        lowest_day={},
        days_with_data=0,
    )
    assert "No se registraron" in s


def test_weekly_summary_no_previous_data():
    s = generate_weekly_summary(
        current_week_total=Decimal("1000000"),
        previous_week_total=Decimal("0"),
        growth_percent=None,
        highest_day={},
        lowest_day={},
        days_with_data=3,
    )
    assert "No hay datos" in s


# ---------------------------------------------------------------------------
# generate_monthly_summary
# ---------------------------------------------------------------------------


def test_monthly_summary_positive():
    s = generate_monthly_summary(
        current_month_total=Decimal("30000000"),
        previous_month_total=Decimal("25000000"),
        growth_percent=Decimal("20.0"),
        highest_day={"day_number": 15, "revenue": 2000000},
        lowest_day={},
        days_with_data=22,
        month_name="junio",
    )
    assert "junio" in s
    assert "20.0%" in s


def test_monthly_summary_no_data():
    s = generate_monthly_summary(
        current_month_total=Decimal("0"),
        previous_month_total=Decimal("0"),
        growth_percent=None,
        highest_day={},
        lowest_day={},
        days_with_data=0,
        month_name="junio",
    )
    assert "No se registraron" in s
    assert "junio" in s


# ---------------------------------------------------------------------------
# generate_daily_summary
# ---------------------------------------------------------------------------


def test_daily_summary_all_perfect():
    s = generate_daily_summary(
        total_sales=Decimal("5000000"),
        net_earnings=Decimal("4800000"),
        total_sessions=5,
        perfect_count=5,
        shortage_count=0,
        surplus_count=0,
        date_label="Jun 25, 2026",
    )
    assert "5 sesiones" in s
    assert "perfectamente" in s.lower()
    assert "Jun 25, 2026" in s


def test_daily_summary_mixed_discrepancies():
    s = generate_daily_summary(
        total_sales=Decimal("5000000"),
        net_earnings=Decimal("4500000"),
        total_sessions=5,
        perfect_count=3,
        shortage_count=1,
        surplus_count=1,
        date_label="",
    )
    assert "3 perfectas" in s
    assert "faltante" in s
    assert "sobrante" in s


def test_daily_summary_no_sessions():
    s = generate_daily_summary(
        total_sales=Decimal("0"),
        net_earnings=Decimal("0"),
        total_sessions=0,
        perfect_count=0,
        shortage_count=0,
        surplus_count=0,
        date_label="Jun 25, 2026",
    )
    assert "No se encontraron" in s


# ---------------------------------------------------------------------------
# generate_business_stats_summary
# ---------------------------------------------------------------------------


def test_business_stats_summary_growth():
    s = generate_business_stats_summary(
        total_sales=Decimal("50000000"),
        previous_sales=Decimal("40000000"),
        growth_percent=Decimal("25.0"),
        business_count=3,
        period_label="jun 2026",
        top_business_name="Sucursal Centro",
        bottom_business_name="Sucursal Norte",
        top_business_share=Decimal("45.0"),
        businesses_growing=2,
    )
    assert "3 sucursales" in s
    assert "25.0%" in s
    assert "Sucursal Centro" in s
    assert "45%" in s
    assert "2 de 3" in s
    assert "Sucursal Norte" in s


def test_business_stats_summary_flat():
    s = generate_business_stats_summary(
        total_sales=Decimal("10000000"),
        previous_sales=Decimal("10000000"),
        growth_percent=Decimal("0.0"),
        business_count=1,
        period_label="",
        top_business_name="",
    )
    assert "Sin cambios" in s


def test_business_stats_summary_absolute_diff():
    s = generate_business_stats_summary(
        total_sales=Decimal("110000000"),
        previous_sales=Decimal("100000000"),
        growth_percent=Decimal("10.0"),
        business_count=2,
        period_label="",
        top_business_name="Suc A",
        businesses_growing=2,
    )
    assert "10.0%" in s
    assert "Gs." in s  # absolute diff shown

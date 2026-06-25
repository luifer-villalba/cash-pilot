"""Smart insights engine for report data.

Provides:
- Anomaly detection (statistical outliers in daily revenue series)
- Alert generation (thresholds, flags, unusual patterns)
- Natural language summaries (template-driven, no LLM dependency)
"""

from datetime import date
from decimal import Decimal
from statistics import mean, stdev
from typing import Any

# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALY_ZSCORE_THRESHOLD = 2.0  # days beyond this z-score are flagged


def detect_revenue_anomalies(
    daily_data: list[dict[str, Any]],
    *,
    date_key: str = "date",
    revenue_key: str = "revenue",
    has_data_key: str = "has_data",
) -> list[dict[str, Any]]:
    """Flag days whose revenue is a statistical outlier in the series.

    Requires at least 4 data points to compute a meaningful z-score.
    Returns a list of anomaly dicts: {date, revenue, z_score, direction}.
    """
    points = [
        d for d in daily_data if d.get(has_data_key, True) and d.get(revenue_key, 0) > 0
    ]
    if len(points) < 4:
        return []

    revenues = [float(p[revenue_key]) for p in points]
    mu = mean(revenues)
    sd = stdev(revenues)
    if sd == 0:
        return []

    anomalies = []
    for p in points:
        z = (float(p[revenue_key]) - mu) / sd
        if abs(z) >= ANOMALY_ZSCORE_THRESHOLD:
            anomalies.append(
                {
                    "date": p[date_key],
                    "revenue": p[revenue_key],
                    "z_score": round(z, 2),
                    "direction": "high" if z > 0 else "low",
                }
            )
    return anomalies


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------

FLAG_RATE_ALERT_THRESHOLD = 15.0  # percent
GROWTH_ALERT_NEGATIVE_THRESHOLD = -20.0  # percent
GROWTH_ALERT_POSITIVE_THRESHOLD = 30.0  # percent


def generate_alerts(
    *,
    growth_percent: Decimal | None = None,
    flag_rate_percent: float | None = None,
    anomalies: list[dict] | None = None,
    zero_revenue_days: int = 0,
    period_label: str = "",
) -> list[dict[str, str]]:
    """Return a list of alert dicts for display in report headers.

    Each alert: {level: 'warning'|'error'|'success', message: str}
    """
    alerts: list[dict[str, str]] = []

    if growth_percent is not None:
        g = float(growth_percent)
        if g <= GROWTH_ALERT_NEGATIVE_THRESHOLD:
            alerts.append(
                {
                    "level": "error",
                    "message": f"Revenue dropped {abs(g):.1f}% vs prior period{' (' + period_label + ')' if period_label else ''}.",
                }
            )
        elif g >= GROWTH_ALERT_POSITIVE_THRESHOLD:
            alerts.append(
                {
                    "level": "success",
                    "message": f"Revenue grew {g:.1f}% vs prior period — strong performance.",
                }
            )

    if flag_rate_percent is not None and flag_rate_percent >= FLAG_RATE_ALERT_THRESHOLD:
        alerts.append(
            {
                "level": "warning",
                "message": f"{flag_rate_percent:.1f}% of sessions are flagged — review recommended.",
            }
        )

    if anomalies:
        for a in anomalies:
            day_str = a["date"].strftime("%b %d") if hasattr(a["date"], "strftime") else str(a["date"])
            direction_word = "unusually high" if a["direction"] == "high" else "unusually low"
            alerts.append(
                {
                    "level": "warning",
                    "message": f"{day_str} had {direction_word} revenue (z={a['z_score']:+.1f}).",
                }
            )

    if zero_revenue_days > 0:
        noun = "day" if zero_revenue_days == 1 else "days"
        alerts.append(
            {
                "level": "warning",
                "message": f"{zero_revenue_days} {noun} with no recorded sessions this period.",
            }
        )

    return alerts


# ---------------------------------------------------------------------------
# Natural-language summaries
# ---------------------------------------------------------------------------


def _fmt_currency(amount: Decimal | float) -> str:
    """Format a number as a human-readable Guaraní amount (no decimals, dot thousands)."""
    n = int(round(float(amount)))
    if n >= 1_000_000:
        return f"Gs. {n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"Gs. {n:,}".replace(",", ".")
    return f"Gs. {n}"


def generate_weekly_summary(
    *,
    current_week_total: Decimal,
    previous_week_total: Decimal,
    growth_percent: Decimal | None,
    highest_day: dict,
    lowest_day: dict,
    days_with_data: int,
) -> str:
    """Return a one-paragraph natural language summary for a weekly trend report."""
    lines: list[str] = []

    total_str = _fmt_currency(current_week_total)

    if days_with_data == 0:
        return "No sessions were recorded for this week."

    lines.append(f"This week totaled {total_str} across {days_with_data} active day(s).")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(f"That's {g:.1f}% above last week — an improvement of {_fmt_currency(current_week_total - previous_week_total)}.")
        elif g < 0:
            lines.append(f"That's {abs(g):.1f}% below last week — a decline of {_fmt_currency(previous_week_total - current_week_total)}.")
        else:
            lines.append("Revenue was flat compared to last week.")
    elif previous_week_total == 0:
        lines.append("No comparison data is available for the previous week.")

    if highest_day:
        lines.append(
            f"Best day: {highest_day.get('day_name', '')} ({_fmt_currency(highest_day.get('revenue', 0))})."
        )
    if lowest_day and lowest_day != highest_day:
        lines.append(
            f"Slowest day: {lowest_day.get('day_name', '')} ({_fmt_currency(lowest_day.get('revenue', 0))})."
        )

    return " ".join(lines)


def generate_monthly_summary(
    *,
    current_month_total: Decimal,
    previous_month_total: Decimal,
    growth_percent: Decimal | None,
    highest_day: dict,
    lowest_day: dict,
    days_with_data: int,
    month_name: str = "",
) -> str:
    """Return a one-paragraph natural language summary for a monthly trend report."""
    lines: list[str] = []
    total_str = _fmt_currency(current_month_total)
    period = f" in {month_name}" if month_name else ""

    if days_with_data == 0:
        return f"No sessions were recorded{period}."

    lines.append(f"Revenue{period} totaled {total_str} across {days_with_data} active day(s).")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(f"That's {g:.1f}% above the previous month.")
        elif g < 0:
            lines.append(f"That's {abs(g):.1f}% below the previous month.")
        else:
            lines.append("Revenue was flat compared to the previous month.")

    if highest_day:
        lines.append(
            f"Peak day: {highest_day.get('day_number', '')} ({_fmt_currency(highest_day.get('revenue', 0))})."
        )

    return " ".join(lines)


def generate_daily_summary(
    *,
    total_sales: Decimal,
    net_earnings: Decimal,
    total_sessions: int,
    perfect_count: int,
    shortage_count: int,
    surplus_count: int,
    date_label: str = "",
) -> str:
    """Return a one-paragraph natural language summary for a daily revenue report."""
    lines: list[str] = []
    period = f" on {date_label}" if date_label else ""

    if total_sessions == 0:
        return f"No closed sessions were found{period}."

    lines.append(
        f"{total_sessions} session(s) were closed{period}, generating {_fmt_currency(total_sales)} in total sales."
    )
    lines.append(f"Net earnings: {_fmt_currency(net_earnings)}.")

    if total_sessions > 0:
        pct_perfect = perfect_count / total_sessions * 100
        if pct_perfect == 100:
            lines.append("All sessions balanced perfectly.")
        else:
            parts = []
            if perfect_count:
                parts.append(f"{perfect_count} perfect")
            if shortage_count:
                parts.append(f"{shortage_count} shortage")
            if surplus_count:
                parts.append(f"{surplus_count} surplus")
            lines.append(f"Discrepancy breakdown: {', '.join(parts)}.")

    return " ".join(lines)


def generate_business_stats_summary(
    *,
    total_sales: Decimal,
    previous_sales: Decimal,
    growth_percent: Decimal | None,
    business_count: int,
    period_label: str = "",
    top_business_name: str = "",
) -> str:
    """Return a brief natural language summary for the multi-business stats report."""
    lines: list[str] = []
    period = f" for {period_label}" if period_label else ""

    lines.append(
        f"Combined sales{period} across {business_count} location(s): {_fmt_currency(total_sales)}."
    )

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(f"Up {g:.1f}% vs prior period.")
        elif g < 0:
            lines.append(f"Down {abs(g):.1f}% vs prior period.")
        else:
            lines.append("Flat vs prior period.")

    if top_business_name:
        lines.append(f"Top performer: {top_business_name}.")

    return " ".join(lines)

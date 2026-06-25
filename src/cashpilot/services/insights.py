"""Smart insights engine for report data.

Provides:
- Anomaly detection (statistical outliers in daily revenue series)
- Alert generation (thresholds, flags, unusual patterns)
- Natural language summaries (template-driven, no LLM dependency)
"""

from decimal import Decimal
from statistics import mean, stdev
from typing import Any

# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALY_ZSCORE_THRESHOLD = 2.0  # days beyond this z-score are flagged

_MONTH_NAMES_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def _fmt_date_es(d) -> str:
    """Format a date as '15 jun' in Spanish."""
    if hasattr(d, "day"):
        return f"{d.day} {_MONTH_NAMES_ES[d.month]}"
    return str(d)


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
    points = [d for d in daily_data if d.get(has_data_key, True) and d.get(revenue_key, 0) > 0]
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
            period_str = f" ({period_label})" if period_label else ""
            alerts.append(
                {
                    "level": "error",
                    "message": (
                        f"Caída de {abs(g):.1f}% respecto al período anterior{period_str}."
                    ),
                }
            )
        elif g >= GROWTH_ALERT_POSITIVE_THRESHOLD:
            alerts.append(
                {
                    "level": "success",
                    "message": f"Crecimiento de {g:.1f}% respecto al período anterior.",
                }
            )

    if flag_rate_percent is not None and flag_rate_percent >= FLAG_RATE_ALERT_THRESHOLD:
        alerts.append(
            {
                "level": "warning",
                "message": (
                    f"{flag_rate_percent:.1f}% de las sesiones están marcadas"
                    " — se recomienda revisión."
                ),
            }
        )

    if anomalies:
        # Show at most 2 anomalies (the most extreme ones) to avoid alert spam
        top = sorted(anomalies, key=lambda a: abs(a["z_score"]), reverse=True)[:2]
        for a in top:
            day_str = _fmt_date_es(a["date"])
            if a["direction"] == "high":
                alerts.append(
                    {
                        "level": "warning",
                        "message": f"El {day_str} tuvo ventas inusualmente altas.",
                    }
                )
            else:
                alerts.append(
                    {
                        "level": "warning",
                        "message": f"El {day_str} tuvo ventas inusualmente bajas.",
                    }
                )

    if zero_revenue_days > 0:
        noun = "día" if zero_revenue_days == 1 else "días"
        alerts.append(
            {
                "level": "warning",
                "message": f"{zero_revenue_days} {noun} sin sesiones registradas en este período.",
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
        return "No se registraron sesiones esta semana."

    dia = "día activo" if days_with_data == 1 else "días activos"
    lines.append(f"Esta semana totalizó {total_str} en {days_with_data} {dia}.")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            diff = _fmt_currency(current_week_total - previous_week_total)
            lines.append(f"Eso es {g:.1f}% más que la semana pasada (+{diff}).")
        elif g < 0:
            diff = _fmt_currency(previous_week_total - current_week_total)
            lines.append(f"Eso es {abs(g):.1f}% menos que la semana pasada (-{diff}).")
        else:
            lines.append("Las ventas se mantuvieron iguales respecto a la semana pasada.")
    elif previous_week_total == 0:
        lines.append("No hay datos de la semana anterior para comparar.")

    if highest_day:
        best_rev = _fmt_currency(highest_day.get("revenue", 0))
        lines.append(f"Mejor día: {highest_day.get('day_name', '')} ({best_rev}).")
    if lowest_day and lowest_day != highest_day:
        slow_rev = _fmt_currency(lowest_day.get("revenue", 0))
        lines.append(f"Día más bajo: {lowest_day.get('day_name', '')} ({slow_rev}).")

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
    period = f" en {month_name}" if month_name else ""

    if days_with_data == 0:
        return f"No se registraron sesiones{period}."

    dia = "día activo" if days_with_data == 1 else "días activos"
    lines.append(f"Las ventas{period} totalizaron {total_str} en {days_with_data} {dia}.")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(f"Eso es {g:.1f}% más que el mes anterior.")
        elif g < 0:
            lines.append(f"Eso es {abs(g):.1f}% menos que el mes anterior.")
        else:
            lines.append("Las ventas se mantuvieron iguales respecto al mes anterior.")

    if highest_day:
        peak_rev = _fmt_currency(highest_day.get("revenue", 0))
        lines.append(f"Día pico: {highest_day.get('day_number', '')} ({peak_rev}).")

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
    period = f" del {date_label}" if date_label else ""

    if total_sessions == 0:
        return f"No se encontraron sesiones cerradas{period}."

    sales_str = _fmt_currency(total_sales)
    sesion = "sesión cerrada" if total_sessions == 1 else "sesiones cerradas"
    lines.append(f"{total_sessions} {sesion}{period} con {sales_str} en ventas totales.")
    lines.append(f"Ganancia neta: {_fmt_currency(net_earnings)}.")

    pct_perfect = perfect_count / total_sessions * 100
    if pct_perfect == 100:
        lines.append("Todas las sesiones cuadraron perfectamente.")
    else:
        parts = []
        if perfect_count:
            parts.append(f"{perfect_count} perfecta{'s' if perfect_count > 1 else ''}")
        if shortage_count:
            parts.append(f"{shortage_count} con faltante{'s' if shortage_count > 1 else ''}")
        if surplus_count:
            parts.append(f"{surplus_count} con sobrante{'s' if surplus_count > 1 else ''}")
        lines.append(f"Diferencias: {', '.join(parts)}.")

    return " ".join(lines)


def generate_business_stats_summary(
    *,
    total_sales: Decimal,
    previous_sales: Decimal,
    growth_percent: Decimal | None,
    business_count: int,
    period_label: str = "",
    top_business_name: str = "",
    bottom_business_name: str = "",
    top_business_share: Decimal | float | None = None,
    businesses_growing: int | None = None,
) -> str:
    """Return a natural language summary for the multi-business stats report."""
    lines: list[str] = []
    period = f" en {period_label}" if period_label else ""
    suc = "sucursal" if business_count == 1 else "sucursales"

    lines.append(
        f"Ventas combinadas{period} en {business_count} {suc}: {_fmt_currency(total_sales)}."
    )

    if growth_percent is not None:
        g = float(growth_percent)
        diff = abs(float(total_sales) - float(previous_sales))
        diff_str = _fmt_currency(diff)
        if g > 0:
            lines.append(f"Subió {g:.1f}% vs período anterior (+{diff_str}).")
        elif g < 0:
            lines.append(f"Bajó {abs(g):.1f}% vs período anterior (-{diff_str}).")
        else:
            lines.append("Sin cambios respecto al período anterior.")

    if businesses_growing is not None and business_count > 1:
        lines.append(f"{businesses_growing} de {business_count} sucursales crecieron.")

    if top_business_name:
        share_str = f" ({float(top_business_share):.0f}% del total)" if top_business_share else ""
        lines.append(f"Mejor desempeño: {top_business_name}{share_str}.")

    if bottom_business_name and bottom_business_name != top_business_name:
        lines.append(f"Menor desempeño: {bottom_business_name}.")

    return " ".join(lines)

"""Smart insights engine for report data.

Provides:
- Anomaly detection (statistical outliers in daily revenue series)
- Alert generation (thresholds, flags, unusual patterns)
- Natural language summaries (template-driven, no LLM dependency)

All generated text is bilingual (en/es), matching the app's `get_locale()`
convention (query param `?lang=`, falling back to Accept-Language, default "en").
"""

from decimal import Decimal
from statistics import mean, stdev
from typing import Any

# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

ANOMALY_ZSCORE_THRESHOLD = 2.0  # days beyond this z-score are flagged

_MONTH_ABBR_ES = {
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

_MONTH_NAME_ES = {
    "January": "enero",
    "February": "febrero",
    "March": "marzo",
    "April": "abril",
    "May": "mayo",
    "June": "junio",
    "July": "julio",
    "August": "agosto",
    "September": "septiembre",
    "October": "octubre",
    "November": "noviembre",
    "December": "diciembre",
}

_DAY_NAME_ES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}


def _fmt_day_short(d: Any, locale: str) -> str:
    """Format a date as a short 'day month' label in the given locale."""
    if locale == "es" and hasattr(d, "day") and hasattr(d, "month"):
        return f"{d.day} {_MONTH_ABBR_ES[d.month]}"
    return d.strftime("%b %d") if hasattr(d, "strftime") else str(d)


def _translate_day_name(day_name: str, locale: str) -> str:
    if locale == "es":
        return _DAY_NAME_ES.get(day_name, day_name)
    return day_name


def _translate_month_name(month_name: str, locale: str) -> str:
    if locale == "es":
        return _MONTH_NAME_ES.get(month_name, month_name)
    return month_name


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
    locale: str = "en",
) -> list[dict[str, str]]:
    """Return a list of alert dicts for display in report headers.

    Each alert: {level: 'warning'|'error'|'success', message: str}
    """
    is_es = locale == "es"
    alerts: list[dict[str, str]] = []

    if growth_percent is not None:
        g = float(growth_percent)
        if g <= GROWTH_ALERT_NEGATIVE_THRESHOLD:
            if is_es:
                message = (
                    f"Los ingresos cayeron {abs(g):.1f}% respecto al período anterior"
                    + (f" ({period_label})" if period_label else "")
                    + "."
                )
            else:
                message = (
                    f"Revenue dropped {abs(g):.1f}% vs prior period"
                    + (f" ({period_label})" if period_label else "")
                    + "."
                )
            alerts.append({"level": "error", "message": message})
        elif g >= GROWTH_ALERT_POSITIVE_THRESHOLD:
            if is_es:
                message = (
                    f"Los ingresos crecieron {g:.1f}% respecto al período anterior "
                    "— un desempeño sólido."
                )
            else:
                message = f"Revenue grew {g:.1f}% vs prior period — strong performance."
            alerts.append({"level": "success", "message": message})

    if flag_rate_percent is not None and flag_rate_percent >= FLAG_RATE_ALERT_THRESHOLD:
        if is_es:
            message = (
                f"El {flag_rate_percent:.1f}% de las sesiones están marcadas"
                " — se recomienda revisión."
            )
        else:
            message = f"{flag_rate_percent:.1f}% of sessions are flagged — review recommended."
        alerts.append({"level": "warning", "message": message})

    if anomalies:
        for a in anomalies:
            day_str = _fmt_day_short(a["date"], locale)
            if is_es:
                direction_word = (
                    "inusualmente alto" if a["direction"] == "high" else "inusualmente bajo"
                )
                message = f"El {day_str} tuvo un ingreso {direction_word} (z={a['z_score']:+.1f})."
            else:
                direction_word = "unusually high" if a["direction"] == "high" else "unusually low"
                message = f"{day_str} had {direction_word} revenue (z={a['z_score']:+.1f})."
            alerts.append({"level": "warning", "message": message})

    if zero_revenue_days > 0:
        if is_es:
            noun = "día" if zero_revenue_days == 1 else "días"
            message = f"{zero_revenue_days} {noun} sin sesiones registradas en este período."
        else:
            noun = "day" if zero_revenue_days == 1 else "days"
            message = f"{zero_revenue_days} {noun} with no recorded sessions this period."
        alerts.append({"level": "warning", "message": message})

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
    locale: str = "en",
) -> str:
    """Return a one-paragraph natural language summary for a weekly trend report."""
    is_es = locale == "es"
    lines: list[str] = []

    total_str = _fmt_currency(current_week_total)

    if days_with_data == 0:
        return (
            "No se registraron sesiones esta semana."
            if is_es
            else ("No sessions were recorded for this week.")
        )

    if is_es:
        lines.append(f"Esta semana totalizó {total_str} en {days_with_data} día(s) activo(s).")
    else:
        lines.append(f"This week totaled {total_str} across {days_with_data} active day(s).")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            diff = _fmt_currency(current_week_total - previous_week_total)
            if is_es:
                lines.append(f"Eso es un {g:.1f}% más que la semana pasada — una mejora de {diff}.")
            else:
                lines.append(f"That's {g:.1f}% above last week — an improvement of {diff}.")
        elif g < 0:
            diff = _fmt_currency(previous_week_total - current_week_total)
            if is_es:
                lines.append(
                    f"Eso es un {abs(g):.1f}% menos que la semana pasada — una caída de {diff}."
                )
            else:
                lines.append(f"That's {abs(g):.1f}% below last week — a decline of {diff}.")
        else:
            lines.append(
                "Los ingresos se mantuvieron estables respecto a la semana pasada."
                if is_es
                else "Revenue was flat compared to last week."
            )
    elif previous_week_total == 0:
        lines.append(
            "No hay datos de comparación disponibles para la semana anterior."
            if is_es
            else "No comparison data is available for the previous week."
        )

    if highest_day:
        best_rev = _fmt_currency(highest_day.get("revenue", 0))
        best_day_name = _translate_day_name(highest_day.get("day_name", ""), locale)
        lines.append(
            f"Mejor día: {best_day_name} ({best_rev})."
            if is_es
            else f"Best day: {best_day_name} ({best_rev})."
        )
    if lowest_day and lowest_day != highest_day:
        slow_rev = _fmt_currency(lowest_day.get("revenue", 0))
        slow_day_name = _translate_day_name(lowest_day.get("day_name", ""), locale)
        lines.append(
            f"Día más flojo: {slow_day_name} ({slow_rev})."
            if is_es
            else f"Slowest day: {slow_day_name} ({slow_rev})."
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
    locale: str = "en",
) -> str:
    """Return a one-paragraph natural language summary for a monthly trend report."""
    is_es = locale == "es"
    lines: list[str] = []
    total_str = _fmt_currency(current_month_total)
    translated_month = _translate_month_name(month_name, locale)
    if month_name:
        period = f" en {translated_month}" if is_es else f" in {translated_month}"
    else:
        period = ""

    if days_with_data == 0:
        return (
            f"No se registraron sesiones{period}."
            if is_es
            else f"No sessions were recorded{period}."
        )

    if is_es:
        lines.append(
            f"Los ingresos{period} totalizaron {total_str} en {days_with_data} día(s) activo(s)."
        )
    else:
        lines.append(f"Revenue{period} totaled {total_str} across {days_with_data} active day(s).")

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(
                f"Eso es un {g:.1f}% más que el mes anterior."
                if is_es
                else f"That's {g:.1f}% above the previous month."
            )
        elif g < 0:
            lines.append(
                f"Eso es un {abs(g):.1f}% menos que el mes anterior."
                if is_es
                else f"That's {abs(g):.1f}% below the previous month."
            )
        else:
            lines.append(
                "Los ingresos se mantuvieron estables respecto al mes anterior."
                if is_es
                else "Revenue was flat compared to the previous month."
            )

    if highest_day:
        peak_rev = _fmt_currency(highest_day.get("revenue", 0))
        lines.append(
            f"Día pico: {highest_day.get('day_number', '')} ({peak_rev})."
            if is_es
            else f"Peak day: {highest_day.get('day_number', '')} ({peak_rev})."
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
    locale: str = "en",
) -> str:
    """Return a one-paragraph natural language summary for a daily revenue report."""
    is_es = locale == "es"
    lines: list[str] = []
    period = (f" el {date_label}" if is_es else f" on {date_label}") if date_label else ""

    if total_sessions == 0:
        return (
            f"No se encontraron sesiones cerradas{period}."
            if is_es
            else f"No closed sessions were found{period}."
        )

    sales_str = _fmt_currency(total_sales)
    if is_es:
        lines.append(
            f"Se cerraron {total_sessions} sesión(es){period}, "
            f"generando {sales_str} en ventas totales."
        )
        lines.append(f"Ganancia neta: {_fmt_currency(net_earnings)}.")
    else:
        lines.append(
            f"{total_sessions} session(s) were closed{period}, "
            f"generating {sales_str} in total sales."
        )
        lines.append(f"Net earnings: {_fmt_currency(net_earnings)}.")

    if total_sessions > 0:
        pct_perfect = perfect_count / total_sessions * 100
        if pct_perfect == 100:
            lines.append(
                "Todas las sesiones cuadraron perfectamente."
                if is_es
                else "All sessions balanced perfectly."
            )
        else:
            parts = []
            if is_es:
                if perfect_count:
                    parts.append(f"{perfect_count} perfectas")
                if shortage_count:
                    parts.append(f"{shortage_count} con faltante")
                if surplus_count:
                    parts.append(f"{surplus_count} con sobrante")
                lines.append(f"Desglose de discrepancias: {', '.join(parts)}.")
            else:
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
    locale: str = "en",
) -> str:
    """Return a brief natural language summary for the multi-business stats report."""
    is_es = locale == "es"
    lines: list[str] = []
    period = (f" de {period_label}" if is_es else f" for {period_label}") if period_label else ""

    if is_es:
        lines.append(
            f"Ventas combinadas{period} en {business_count} local(es): "
            f"{_fmt_currency(total_sales)}."
        )
    else:
        lines.append(
            f"Combined sales{period} across {business_count} location(s): "
            f"{_fmt_currency(total_sales)}."
        )

    if growth_percent is not None:
        g = float(growth_percent)
        if g > 0:
            lines.append(
                f"Subió {g:.1f}% respecto al período anterior."
                if is_es
                else f"Up {g:.1f}% vs prior period."
            )
        elif g < 0:
            lines.append(
                f"Bajó {abs(g):.1f}% respecto al período anterior."
                if is_es
                else f"Down {abs(g):.1f}% vs prior period."
            )
        else:
            lines.append(
                "Estable respecto al período anterior." if is_es else "Flat vs prior period."
            )

    if top_business_name:
        lines.append(
            f"Mejor desempeño: {top_business_name}."
            if is_es
            else f"Top performer: {top_business_name}."
        )

    return " ".join(lines)

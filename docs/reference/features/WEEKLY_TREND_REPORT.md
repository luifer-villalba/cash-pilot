# Weekly Trend Report — Feature Documentation

> 📚 Reference Document  
> This document describes the weekly trend report feature implementation and usage.

## Purpose

The weekly trend report provides business owners and managers with week-over-week revenue comparisons to identify trends, growth patterns, and anomalies in their sales data.

---

## Overview

**Feature Status:** ✅ Production Ready  
**Access Level:** Admin only  
**Acceptance Criteria:** AC-06  
**Related Tests:** `test_weekly_trend_report.py`, `test_weekly_trend_pdf.py`

---

## What It Does

The weekly trend report:

1. **Compares current week vs previous 4 weeks** - Shows revenue trends over 5 weeks
2. **Day-by-day breakdown** - Displays daily totals for each day of the week
3. **Growth indicators** - Shows percentage change with visual indicators (↑ ↓ →)
4. **Identifies patterns** - Highlights highest/lowest revenue days
5. **Supports PDF export** - Generate downloadable PDF reports
6. **Multi-business support** - Filter by specific business or view all
7. **Performance optimized** - Cached results for fast loading

---

## User Workflow

### Accessing the Report

1. **Admin logs in** to CashPilot
2. **Navigate to Reports** → Weekly Trend Report
3. **Select filters:**
   - All Businesses (default) or specific business
   - Current week or historical weeks
4. **View results** on screen
5. **Export to PDF** (optional) - Click "Export PDF" button

### Reading the Report

**Week Selector:**
- Current week (default)
- Previous weeks (dropdown: 1 week ago, 2 weeks ago, etc.)

**Daily Breakdown Table:**
| Day | Current Week | 1 Week Ago | 2 Weeks Ago | 3 Weeks Ago | 4 Weeks Ago |
|-----|--------------|------------|-------------|-------------|-------------|
| Mon | ₲ 1.500.000 ↑ | ₲ 1.200.000 | ₲ 1.100.000 | ₲ 1.000.000 | ₲ 1.250.000 |
| Tue | ₲ 1.800.000 ↑ | ₲ 1.500.000 | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

**Week Total:**
- Sum of all days in the week
- Percentage change from previous week
- Trend indicator (↑ ↓ →)

**Insights:**
- Highest revenue day of current week
- Lowest revenue day of current week
- Average daily revenue
- Growth rate calculation

---

## Technical Implementation

### Data Source

**Cash Sessions:**
- Report aggregates totals from all `cash_sessions` with `status = 'closed'`
- Calculates total sales: `cash_sales + card_sales + credit_sales`
- Groups by business and date
- Filters by week boundaries (Monday-Sunday)

**Week Calculation:**
```python
# Week starts Monday (ISO week)
# Week ends Sunday
week_start = current_date - timedelta(days=current_date.weekday())
week_end = week_start + timedelta(days=6)
```

### Caching Strategy

**Cache Keys:**
- Format: `weekly_trend_v4_{business_id}_{week_start}`
- Version: `v4` (increment when calculation logic changes)

**Cache TTL:**
- **Current week:** 5 minutes (frequently updated as sessions close)
- **Historical weeks:** 1 hour (stable data)

**Cache Invalidation:**
- Automatic TTL expiration
- Manual clear when logic changes (increment version)
- No need to flush cache manually on session edits

### PDF Generation

**Technology:** WeasyPrint (HTML to PDF)

**Process:**
1. Render HTML template with report data
2. Apply CSS styling (optimized for print)
3. Generate PDF via WeasyPrint
4. Return as downloadable file

**File Name:** `weekly_trend_{business_name}_{week_start}.pdf`

**Layout:**
- Page size: A4 (portrait)
- Margins: 20mm all sides
- Header: Business name, date range
- Footer: Generated date, page numbers
- Tables: Responsive, proper page breaks

---

## API Endpoints

### Get Weekly Trend Data (JSON)

```
GET /api/reports/weekly-trend
```

**Query Parameters:**
- `business_id` (optional): Filter by business UUID (omit for all businesses)
- `week_offset` (optional): Weeks back from current (0 = current, 1 = last week)

**Response:**
```json
{
  "current_week": {
    "start_date": "2026-02-10",
    "end_date": "2026-02-16",
    "daily_totals": [
      {
        "date": "2026-02-10",
        "day_name": "Lunes",
        "total_sales": "1500000.00",
        "session_count": 3,
        "change_percent": 25.0,
        "trend": "up"
      }
    ],
    "week_total": "9500000.00",
    "week_average": "1357142.86"
  },
  "comparison_weeks": [
    {
      "week_label": "1 semana atrás",
      "week_start": "2026-02-03",
      "week_total": "8700000.00",
      "change_percent": -8.5
    }
  ]
}
```

### Export Weekly Trend PDF

```
GET /api/reports/weekly-trend/pdf
```

**Query Parameters:** Same as JSON endpoint

**Response:** PDF file (Content-Type: application/pdf)

---

## Frontend Template

**File:** `templates/reports/weekly_trend.html`

**Components:**
- Filter form (business selector, week selector)
- Summary cards (week total, average, growth rate)
- Daily breakdown table (5 weeks side-by-side)
- Trend indicators (↑ ↓ → with colors)
- Export PDF button
- Loading states (HTMX)

**Styling:**
- Tailwind CSS + DaisyUI
- Monospace fonts for numbers
- Color-coded trends (green=growth, red=decline, gray=stable)
- Responsive layout (mobile-friendly)

---

## Business Rules

### Week Boundaries

- **Week starts:** Monday 00:00:00
- **Week ends:** Sunday 23:59:59
- **Timezone:** America/Asuncion (Paraguay)

### Data Inclusion

**Included:**
- Closed cash sessions only (`status = 'closed'`)
- Active businesses only (`is_active = true`)
- Non-deleted sessions only (`is_deleted = false`)

**Excluded:**
- Open sessions (not yet reconciled)
- Deleted sessions (soft delete)
- Inactive businesses

### Calculation

**Total Sales:**
```python
total_sales = cash_sales + card_sales + credit_sales
```

**Growth Percentage:**
```python
change_percent = ((current - previous) / previous) * 100 if previous > 0 else 0
```

**Trend Indicator:**
- `↑` Up: change_percent > 5%
- `↓` Down: change_percent < -5%
- `→` Stable: -5% ≤ change_percent ≤ 5%

---

## Testing

### Test Coverage

**File:** `tests/test_weekly_trend_report.py`

**Tests:**
- AC-06: Weekly report data aggregation
- AC-06: Week boundary calculation
- AC-06: Multi-business filtering
- AC-06: Growth percentage calculation
- AC-06: Trend indicator logic
- AC-06: Cache functionality

**File:** `tests/test_weekly_trend_pdf.py`

**Tests:**
- AC-06: PDF generation succeeds
- AC-06: PDF contains correct data
- AC-06: PDF styling applied

### Manual Testing Checklist

- [ ] Report loads for all businesses
- [ ] Report loads for single business
- [ ] Week navigation works (current, -1, -2, etc.)
- [ ] Daily totals match raw session data
- [ ] Growth percentages calculated correctly
- [ ] Trend indicators display properly
- [ ] PDF export generates valid file
- [ ] PDF contains all data from screen
- [ ] Works on Windows 7 / IE11
- [ ] Responsive on mobile

---

## Performance Considerations

### Query Optimization

**Database Index:**
```sql
CREATE INDEX idx_sessions_business_date_status 
ON cash_sessions(business_id, opened_at, status) 
WHERE is_deleted = false;
```

**Query Strategy:**
- Use date range filter (`opened_at BETWEEN start AND end`)
- Filter by `status = 'closed'` and `is_deleted = false`
- Aggregate in database (not Python)
- Use `GROUP BY` for daily totals

### Caching Impact

**Without Cache:**
- Query time: ~200-500ms (depending on data size)
- Database load: 1 query per page load

**With Cache:**
- Response time: ~10-20ms
- Database load: Only on cache miss
- TTL ensures fresh data (5min current, 1hr historical)

### Scalability

**Current Performance:**
- Handles 1000+ sessions per business
- Supports 10+ businesses
- Response time <500ms (cache miss)
- Response time <50ms (cache hit)

**Future Improvements:**
- Materialized views for historical weeks
- Background job to pre-calculate reports
- Redis instead of in-memory cache

---

## Troubleshooting

### Report Shows Wrong Totals

**Causes:**
1. Cache stale (unlikely with 5min TTL)
2. Session not closed (only closed sessions counted)
3. Timezone mismatch (check America/Asuncion)

**Solutions:**
1. Clear cache: Increment `WEEKLY_TREND_CACHE_VERSION`
2. Verify session status: `SELECT * FROM cash_sessions WHERE status = 'open'`
3. Check logs for timezone errors

### PDF Export Fails

**Causes:**
1. WeasyPrint not installed
2. Font missing
3. CSS errors

**Solutions:**
1. `pip install weasyprint`
2. Check logs: `docker compose logs app | grep -i weasyprint`
3. Test HTML render first before PDF

### Missing Days in Report

**Causes:**
1. No sessions on that day (expected)
2. All sessions open (not counted)
3. Week boundary issue

**Solutions:**
1. Verify sessions exist: `SELECT * FROM cash_sessions WHERE opened_at::date = '2026-02-10'`
2. Check status: Count open vs closed
3. Verify week calculation logic

---

## Future Enhancements

**Planned (Not Yet Implemented):**
- Month-over-month comparison
- Year-over-year trends
- Cashier performance breakdown
- Business comparison charts
- Custom date ranges
- Email scheduled reports

**Out of Scope:**
- Predictive analytics (forecasting)
- External data integration (weather, holidays)
- Real-time updates (current implementation is cached)

---

## Related Documentation

- [API.md](API.md) - API endpoint details
- [ACCEPTANCE_CRITERIA.md](../product/ACCEPTANCE_CRITERIA.md) - AC-06
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

---

## Change History

- **2026-01-29:** Initial implementation (CP-REPORTS-01)
- **2026-02-14:** Cache optimization and version strategy added
- **Current Version:** v4 (cache version)

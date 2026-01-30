# Implementation Plan — CP-REPORTS-02: Flagged Cash Sessions Report (by business/cashier)

## Goal

Provide an admin-only report that lists flagged cash sessions by business, cashier, and date, with quick filters (This Week/Last Week/This Month/Last Month) and quick stats comparing the previous period.

---

## Acceptance Criteria

- AC-06 Reporting (Admin Only)
- AC-04 Validation & Error Handling

---

## Scope

**In scope**

- Add a new report entry on the Reports dashboard.
- Create a new report page that supports:
  - Quick date ranges: This Week, Last Week, This Month, Last Month
  - Optional filters: Business, Cashier name (search)
  - Sorting: Business name → Cashier name → Session date
  - Rows show: business, date, cashier, flag reason, and session details
- Quick stats for the selected range with comparison to previous period:
  - Total flagged sessions
  - Flag rate (% flagged vs total sessions)
  - Days with flags
  - Cashiers with flags
  - Total sessions
- No model or database changes.

**Out of scope**

- New export formats
- RBAC changes
- Audit log UI

---

## PR Breakdown (Recommended)

### PR 1 — Report route + data aggregation

**Purpose**

- Add report route with date range logic, filters, and aggregated stats

**Changes**

- `src/cashpilot/api/routes/flagged_sessions.py` (new)
- `src/cashpilot/main.py` (include router)

**Risks**

- Medium (date range edge cases, filters affecting stats consistency)

**Tests**

- Unit tests for date range calculations
- Unit tests for stats/delta calculations on filtered vs unfiltered datasets

---

### PR 2 — Report UI

**Purpose**

- Build report template with filters, stats cards, and flagged session table

**Changes**

- `templates/reports/flagged-sessions.html`
- `templates/reports/dashboard.html`

**Risks**

- Low (template + layout)

**Tests**

- Manual verification of filters and ordering
- Manual verification of screenshot-ready layout

---

### PR 3 — Copy + i18n (Optional)

**Purpose**

- Localize new report title, labels, and helper text

**Changes**

- `translations/es_PY/LC_MESSAGES/messages.po`

**Risks**

- Low

**Tests**

- Manual check of translated labels

---

## Migration Strategy (If Applicable)

- Migration required? No

---

## Test Strategy Summary

- Date range and comparison logic unit tests
- Manual UI verification for filters, sorting, and quick stats

---

## Rollback Plan

- Remove the report entry and route; no data changes to unwind

---

## Completion Checklist

Work is complete when:

- Report appears on the Reports dashboard
- Date range shortcuts work as specified
- Business and cashier filters apply consistently to rows and quick stats
- Quick stats compare to the previous period
- Rows are grouped/sorted by business, cashier, then session date
- No model/database changes were required

---

## Change Control

Any deviation from this plan must:

- Be documented
- Be explicitly approved

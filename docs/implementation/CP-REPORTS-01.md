# Implementation Plan — CP-REPORTS-01: Business stats filter ordering + week-over-week comparisons

## Goal

Improve the business stats report filters so default and quick ranges match expected business workflows, and comparisons are explicit and trustworthy at a glance.

---

## Status

Completed (2026-01-29)

---

## Acceptance Criteria

- AC-06 Reporting (Admin Only)
- AC-04 Validation & Error Handling

---

## Scope

**In scope**

- Reorder filter shortcuts in `templates/reports/business-stats.html`:
  - Today, Yesterday, This Week, Last Week, This Month (default), Last Month, Personalizado
- Replace "Últimos 7 días / Últimos 30 días" with "This Week / Last Week"
- Implement comparison rules:
  - Today → compare to same weekday last week
  - Yesterday → compare to same weekday last week
  - This Week → compare to Last Week (same weekday range, defined week boundary)
  - Last Week → compare to the week prior
  - This Month (MTD) → compare to Last Month MTD
  - Last Month → compare to the month prior (full month)
- Header copy clarifies comparison basis (e.g., "mismo día de la semana pasada")
- Default selection is This Month (MTD) and clearly labeled as MTD in UI copy
- Update translations and labels for new shortcut names and comparison text

**Out of scope**

- Changes to data models or persistence
- Changes to non-reporting pages
- New export formats
- RBAC changes

---

## PR Breakdown (Mandatory)

### PR 1 — Date range + comparison logic

**Purpose**

- Add or refactor date-range helpers to support new comparison rules

**Changes**

- `src/cashpilot/api/routes/business_stats.py`
- Any shared date helper module (if required)

**Risks**

- Medium (date edge cases, week boundary definitions)

**Tests**

- Unit tests for date-range calculations (Today/Yesterday vs same weekday last week)
- Tests for week and month comparisons, including month boundary edge cases

---

### PR 2 — Filter UI ordering + default selection

**Purpose**

- Align shortcuts with new ranges and make default selection explicit

**Changes**

- `templates/reports/business-stats.html`
- Any related report navigation/partials

**Risks**

- Low

**Tests**

- Manual verification of default selection and correct link params
- Snapshot or template render checks if available

---

### PR 3 — Copy + i18n clarity (Optional)

**Purpose**

- Make comparison basis obvious at a glance

**Changes**

- `translations/es_PY/LC_MESSAGES/messages.po`
- Any copy in report headers or tooltips

**Risks**

- Low

**Tests**

- Manual check of translated labels and header text

---

## Migration Strategy (If Applicable)

- Migration required? No

---

## Test Strategy Summary

- Add or update tests for date-range comparison logic in `business_stats` route
- Manual UI check for filter order, default selection, and comparison label clarity

---

## Rollback Plan

- Revert filter ordering and range logic changes by rolling back PRs
- No data changes to unwind

---

## Completion Checklist

Work is complete when:

- Filters are ordered as specified and This Month (MTD) is default
- Today/Yesterday compare to the same weekday last week
- This Week/Last Week behave as defined by a consistent week boundary
- Comparison basis is clearly communicated in the UI
- Tests are green and AC-06/AC-04 are satisfied

---

## Change Control

Any deviation from this plan must:

- Be documented
- Be explicitly approved

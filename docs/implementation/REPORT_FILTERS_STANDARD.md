# Report Filters Standard (Simple Pattern)

## Purpose
Define one **simple, repeatable filter pattern** for all admin reports, so implementation and QA stay consistent over time.

This is the baseline to reuse in future report tickets (transfers, expenses, envelopes, and next reports).

---

## 1) Canonical Filter Contract (URL + state)

All report pages should keep filter state in query params.

### Required date params
- `from_date` (ISO date)
- `to_date` (ISO date)
- `preset` (`today`, `yesterday`, `last_2_days`, `last_3_days`, `last_7_days`, `last_month`, `custom`)

### Optional context params
- `origin` (example: `reconciliation`)
- `page`, `page_size`, `sort_by`, `sort_order`
- report-specific filters (`business_ids`, `cashier_id`, `verified`, etc.)

### Rule: default behavior
- If no origin context is present: default to **Today**.
- If user enters from a context screen (e.g. reconciliation): preserve the deep-link context (date/custom range) and keep it through pagination and form submits.

---

## 2) UI Pattern (must stay compact)

### Primary row (always visible)
Keep a single compact row with:
1. `from_date`
2. `to_date`
3. main selector(s) most used in that report (e.g. business)
4. quick presets (buttons/chips)
5. `Apply` action (if needed by page behavior)

### Secondary row/panel (advanced)
Less-used filters go in a collapsible "Advanced filters" area.

### Simplicity rules
- Do not duplicate date controls in multiple places.
- Do not add decorative controls without behavior.
- Keep quick preset behavior immediate and predictable.

---

## 3) Quick Presets Behavior (required)

When a preset is clicked:
1. Update `from_date` + `to_date`.
2. Set `preset` correctly.
3. Execute search immediately.
4. Preserve other active filters.

Active preset must be visually highlighted using existing design system classes.

---

## 4) Backend Rules

- Apply filtering/sorting/pagination in SQL, not in-memory.
- Compute counts/totals from the same filtered base query.
- Keep pagination stable and deterministic with explicit ordering.
- Validate/normalize query params (invalid values should safely fallback).

---

## 5) QA Checklist (minimum)

For each report implementing this standard:

- [ ] Default entry without context opens in `today`.
- [ ] Context entry (e.g. reconciliation) preserves custom/date context.
- [ ] Presets update range and run immediately.
- [ ] Other filters are preserved when preset changes.
- [ ] Pagination keeps all active filters and context params.
- [ ] Sorting works with active filters and pagination.
- [ ] Totals/count reflect current filtered dataset.
- [ ] Empty-state and validation/error messages are visible and clear.
- [ ] Mobile layout remains usable (filters + results).

---

## 6) Rollout to Other Reports

Apply this document as the default filter pattern for:
- Expenses by date range
- Envelopes by date range
- Any new date-range admin report

Each ticket should include:
1. Link to this standard.
2. Any justified deviation (explicitly documented).
3. Added tests for presets + filter persistence + pagination.

---

## 7) Future Review & Corrections

When a filter bug or UX mismatch appears:
1. Compare against this standard first.
2. Fix the implementation to match the standard (instead of adding one-off behavior).
3. If the standard itself needs improvement, update this file and reference the change in the ticket/PR.

Suggested cadence: quick review whenever a report filter is changed, plus monthly pass for consistency.

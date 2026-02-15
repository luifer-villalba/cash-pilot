# Implementation Plan — CP-REPORTS-02: Auto-refresh reconciliation comparison

## Goal

Reduce manual refresh during end-of-day by auto-updating the reconciliation comparison table for admins.

---

## Acceptance Criteria

- AC-06 Reporting (Admin Only)

---

## Scope

**In scope**

- Add HTMX polling to refresh the comparison results on the reconciliation comparison page.
- Keep current filters (date, business) applied on refresh.
- Optional: show a simple "last updated" timestamp on refresh.

**Out of scope**

- New filters or report logic changes.
- Data model or migration changes.
- RBAC rule changes.

---

## PR Breakdown (Mandatory)

### PR 1 — HTMX polling + partial rendering

**Purpose**

- Enable periodic refresh of comparison results without full page reload.

**Changes**

- templates/admin/reconciliation_compare.html
- Optional: new partial template for comparison results
- src/cashpilot/api/admin.py (add/adjust route for partial render)

**Risks**

- Low (additional DB reads; ensure HTMX refresh does not break legacy browsers)

**Tests**

- Manual: verify polling refreshes data every 30-60s
- Manual: confirm filters (date, business) persist across refresh
- Manual: verify on Windows 7 / legacy browser compatibility

---

## Migration Strategy (If Applicable)

- Migration required? No

---

## Test Strategy Summary

- Manual verification only

---

## Rollback Plan

- Remove HTMX polling attributes and any partial route; no data changes to revert

---

## Completion Checklist

Work is complete when:

- Comparison results auto-refresh on a fixed interval
- Selected filters remain applied
- No regression in legacy compatibility

---

## Change Control

Any deviation from this plan must:

- Be documented
- Be explicitly approved

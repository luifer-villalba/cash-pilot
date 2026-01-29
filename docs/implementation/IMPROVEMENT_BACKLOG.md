# IMPROVEMENT_BACKLOG — CashPilot

## Purpose

This document tracks **all improvement work identified after the external audit**.
It is the **single source of truth** for technical debt, risk mitigation, and hardening tasks.

This backlog is **not executable by itself**.
Each item must be implemented via a dedicated **Implementation Plan** following `docs/sdlc/IMPLEMENTATION_PLAN.md`.

---

## Backlog Governance Rules

* Items are ordered by **risk, not convenience**
* No item enters implementation without DoR approval
* One epic or ticket per implementation plan
* No "drive-by fixes"

---

## 🔴 EPIC 1 — RBAC & Business Isolation (CRITICAL)

**Risk:** Privilege escalation, cross-business data leaks
**Release impact:** Blocks any production release

### CP-RBAC-01 — Enforce RBAC on session edit API

* **Severity:** Critical
* **Problem:** Any authenticated user can edit any session
* **Evidence:** `src/cashpilot/api/cash_session_edit.py`
* **Acceptance impact:** AC-02, AC-05
* **Status:** Completed (2026-01-29)

### CP-RBAC-02 — Restrict audit / flag endpoints to Admin

* **Severity:** High
* **Problem:** Audit data visible and mutable by any user
* **Evidence:** `src/cashpilot/api/cash_session_audit.py`
* **Acceptance impact:** AC-02, AC-07
* **Status:** Not started

### CP-RBAC-03 — Enforce business assignment on all session flows

* **Severity:** High
* **Problem:** Cashiers can act on unassigned businesses
* **Evidence:** `routes/sessions.py` (HTML flow)
* **Acceptance impact:** AC-01, AC-02
* **Status:** Not started

### CP-RBAC-04 — Confirm Superadmin access across all businesses

* **Severity:** Medium
* **Problem:** Docs/tests must reflect superadmin reality; ensure endpoints treat Admin as global.
* **Evidence:** Decision: Admin is superadmin
* **Status:** Approved

---

## 🔴 EPIC 2 — Data Integrity & Transactions (CRITICAL)

**Risk:** Silent financial data corruption

### CP-DATA-01 — Prevent partial persistence on validation errors

* **Severity:** Critical
* **Problem:** Invalid data may be partially saved
* **Evidence:** `core/db.py`, `routes/sessions.py`
* **Acceptance impact:** AC-04
* **Status:** Not started

### CP-DATA-02 — Enforce single open session per cashier/business

* **Severity:** High
* **Problem:** Multiple open sessions possible via UI
* **Evidence:** Missing overlap check in HTML flow
* **Acceptance impact:** AC-03
* **Status:** Not started

---

## 🔴 EPIC 3 — Legacy Compatibility (CRITICAL / NFR)

**Risk:** Application unusable on Windows 7

### CP-LEGACY-01 — Remove ES6 from base template

* **Severity:** High
* **Problem:** ES6 syntax breaks IE11
* **Evidence:** `templates/base.html`
* **Acceptance impact:** AC-08
* **Status:** Not started

### CP-LEGACY-02 — Replace unsupported DOM APIs

* **Severity:** Medium
* **Problem:** `classList.toggle(force)` unsupported
* **Evidence:** `static/js/dashboard.js`
* **Acceptance impact:** AC-08
* **Status:** Not started

---

## 🟠 EPIC 5 — API Robustness & Error Handling (MEDIUM)

**Risk:** Unhandled input can cause 500s and noisy error reporting

### CP-ROBUST-01 — Guard UUID parsing across API routes

* **Severity:** Medium
* **Problem:** Invalid UUIDs can raise uncaught errors and return 500s
* **Evidence:** Multiple API routes with direct UUID parsing
* **Acceptance impact:** Reliability / error hygiene
* **Status:** Completed (2026-01-29)

---

## 🟠 EPIC 6 — Reporting UX & Comparisons (MEDIUM)

**Risk:** Misleading comparisons reduce trust in reporting insights

### CP-REPORTS-01 — Business stats filter ordering + week-over-week comparisons

* **Severity:** Medium
* **Problem:** Filter order and comparison logic do not match expected business workflow
* **Evidence:** `templates/reports/business-stats.html`, `src/cashpilot/api/routes/business_stats.py`
* **Acceptance impact:** AC-06, AC-04
* **Status:** Not started

---

## 🟠 EPIC 4 — Data Model Alignment (DECISION REQUIRED)

**Risk:** Auditability and reporting correctness degradation

### CP-MODEL-01 — Resolve role model mismatch

* **Severity:** High
* **Problem:** Roles are global, docs require per-business
* **Evidence:** `models/user.py` vs `DATA_MODEL.md`
* **Decision:** Roles are global; Admin is superadmin. Docs aligned to code.
* **Status:** Roles are global (docs aligned to code)

### CP-MODEL-02 — Add or document business timezone

* **Severity:** High
* **Problem:** Timezone missing from business entity
* **Evidence:** `models/business.py`
* **Status:** Not started

### CP-MODEL-03 — Link DailyReconciliation to CashSession

* **Severity:** High
* **Problem:** Missing linkage and audit fields
* **Evidence:** `models/daily_reconciliation.py`
* **Status:** Not started

---

## 🟠 EPIC 5 — Testing vs Acceptance Criteria

**Risk:** Cannot demonstrate compliance

### CP-TEST-01 — Map tests to Acceptance Criteria

* **Severity:** High
* **Problem:** Tests lack AC references
* **Evidence:** `tests/`
* **Status:** Not started

### CP-TEST-02 — Add RBAC tests for mutating APIs

* **Severity:** Critical
* **Problem:** API RBAC bypass untested
* **Evidence:** Missing coverage
* **Status:** Not started

---

## 🟡 EPIC 6 — Release & Ops Hardening

**Risk:** Recovery and rollback weakness

### CP-REL-01 — Add backup verification to release checklist

* **Severity:** Medium
* **Problem:** Backup not explicit
* **Evidence:** `RELEASE_CHECKLIST.md`
* **Status:** Not started

### CP-REL-02 — Document Windows 7 verification evidence

* **Severity:** Medium
* **Problem:** No proof of legacy testing
* **Status:** Not started

---

## Backlog Rules Reminder

* Backlog items do NOT equal implementation approval
* Each item requires:

  * Definition of Ready
  * Dedicated Implementation Plan
  * Small, reviewable PRs

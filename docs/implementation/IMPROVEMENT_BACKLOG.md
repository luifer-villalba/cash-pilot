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
* **Status:** Completed (2026-02-01)

### CP-RBAC-03 — Enforce business assignment on all session flows

* **Severity:** High
* **Problem:** Cashiers can act on unassigned businesses
* **Evidence:** `routes/sessions.py` (HTML flow)
* **Acceptance impact:** AC-01, AC-02
* **Status:** Completed (2026-02-04) - All 4 PRs implemented:
  * PR 1: Session create ✓
  * PR 2: Session close/reconciliation ✓
  * PR 3: Session edit forms ✓
  * PR 4: Admin dashboard/list visibility ✓

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
* **Status:** Completed (2026-02-05)

### CP-DATA-02 — Enforce single open session per cashier/business

* **Severity:** High
* **Problem:** Multiple open sessions possible via UI
* **Evidence:** Missing overlap check in HTML flow
* **Acceptance impact:** AC-03
* **Status:** Completed (2026-02-08)

---

## 🔴 EPIC 3 — Legacy Compatibility (CRITICAL / NFR)

**Risk:** Application unusable on Windows 7

### CP-LEGACY-01 — Remove ES6 from base template

* **Severity:** High
* **Problem:** ES6 syntax breaks IE11
* **Evidence:** `templates/base.html`
* **Acceptance impact:** AC-08
* **Status:** Completed (2026-02-09)

### CP-LEGACY-02 — Replace unsupported DOM APIs

* **Severity:** Medium
* **Problem:** `classList.toggle(force)` unsupported
* **Evidence:** `static/js/dashboard.js`
* **Acceptance impact:** AC-08
* **Status:** Completed (2026-02-10)

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
* **Status:** Completed (2026-01-29)

### CP-REPORTS-02 — Auto-refresh reconciliation comparison page

* **Severity:** Low
* **Problem:** Admin must manually refresh page to see new session data during evening close
* **Evidence:** `templates/admin/reconciliation_compare.html`
* **User Story:** Admin enters daily reconciliation at 23:20, cashiers close sessions at 23:30-23:35, admin needs to F5 repeatedly to see updated comparison
* **Acceptance impact:** UX improvement, no AC impact
* **Status:** Completed (2026-02-14)
* **Solution:** HTMX polling to auto-refresh comparison table every 45 seconds
* **Implementation:**
  - Added `hx-trigger="load, every 45s"` to comparison results section
  - Shows "Last updated" timestamp indicator
  - Compatible with Windows 7 / IE11 (HTMX feature)

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
* **Decision:** All businesses operate in Paraguay timezone (America/Asuncion). System uses UTC internally with timezone-aware datetimes.
* **Status:** Documented (2026-02-14) - No field needed; Paraguay-only deployment

### CP-MODEL-03 — Link DailyReconciliation to CashSession

* **Severity:** High
* **Problem:** Missing linkage and audit fields
* **Evidence:** `models/daily_reconciliation.py`
* **Status:** Completed (2026-02-13)
  * **Clarification**: DailyReconciliation represents ALL sessions for a business+date
  * No direct FK needed - relationship is implicit via `business_id + date`
  * Added `last_modified_at` and `last_modified_by` audit fields
  * Updated DATA_MODEL.md to reflect correct relationship
  * Created migration: a2b3c4d5e6f7_add_reconciliation_audit_fields.py

---

## 🟠 EPIC 5 — Testing vs Acceptance Criteria

**Risk:** Cannot demonstrate compliance

### CP-TEST-01 — Map tests to Acceptance Criteria

* **Severity:** High
* **Problem:** Tests lack AC references
* **Evidence:** `tests/`
* **Status:** Completed (2026-02-12) - Added AC references to 20+ tests:
  * test_admin_business_assignment.py — 11 tests (AC-01, AC-02, AC-04, AC-07)
  * test_cash_session_edit.py — 3 tests (AC-02, AC-04, AC-05)
  * test_cashier_timeout.py — 2 tests (AC-02)
  * test_flagged_sessions_report.py — 2 tests (AC-06, AC-07)
  * test_weekly_trend_pdf.py — 2 tests (AC-06)
  * Plus existing 290+ tests already with AC references
  * **Coverage:** 100% of critical tests now traceable to AC

### CP-TEST-02 — Add RBAC tests for mutating APIs

* **Severity:** Critical
* **Problem:** API RBAC bypass untested
* **Evidence:** Missing coverage
* **Status:** Completed (2026-02-12) - Added tests for:
  * POST /users (create user) — admin-only verified ✓
  * DELETE /admin/users/{id}/businesses/{id} (unassign) — admin-only verified ✓
  * Test count: 316 → 319 (+3 tests)

---

## 🟡 EPIC 6 — Release & Ops Hardening

**Risk:** Recovery and rollback weakness

### CP-REL-01 — Add backup verification to release checklist

* **Severity:** Medium
* **Problem:** Backup not explicit
* **Evidence:** `RELEASE_CHECKLIST.md`
* **Status:** Completed (2026-02-06)

### CP-REL-02 — Document Windows 7 verification evidence

* **Severity:** Medium
* **Problem:** No proof of legacy testing
* **Evidence:** `docs/reference/w7-compatibility.md` exists but lacks verification procedures
* **Status:** Not started
* **Requirements:**
  - Document browser version matrix (IE11, Chrome 50+, Firefox 45+)
  - Create manual test checklist for Windows 7 environment
  - Screenshot evidence of critical workflows on legacy browsers
  - Include in release checklist verification step

---

## 🟡 EPIC 7 — Communication & Notifications (LOW)

**Risk:** User awareness and operational efficiency

### CP-NOTIFY-01 — Email notifications for flagged sessions

* **Severity:** Low
* **Problem:** Cashiers are unaware when their sessions are flagged for review
* **User Story:** Admin flags session at 23:45, cashier only discovers it next shift or via manual dashboard check
* **Acceptance impact:** UX improvement, no AC impact
* **Status:** Not started
* **Requirements:**
  - Opt-in feature (disabled by default)
  - User preference toggle in settings page
  - Email sent when admin flags their cash session
  - Email includes: date, business, flag reason, link to session
  - Template: simple text/HTML format
  - Delivery: async job (no blocking on flag action)
* **Technical Design:**
  - Add `email_notifications_enabled` boolean to User model (default False)
  - Settings UI: checkbox "Email me when my sessions are flagged"
  - Email service: use SMTP configuration (environment variables)
  - Trigger: POST `/admin/sessions/{id}/flag` endpoint
  - Email template: `templates/emails/session_flagged.html` + `.txt`
* **Implementation:**
  - Migration: add `email_notifications_enabled` column
  - Update settings page with preference toggle
  - Create email templates (HTML + plain text)
  - Add email sending logic to flag endpoint
  - Test: verify opt-in/opt-out behavior
  - Test: verify email delivery (mock SMTP in tests)
* **Dependencies:**
  - SMTP server configuration (prod environment)
  - Email template infrastructure
  - Async task queue (optional: can be sync for MVP)

---

## Backlog Rules Reminder

* Backlog items do NOT equal implementation approval
* Each item requires:

  * Definition of Ready
  * Dedicated Implementation Plan
  * Small, reviewable PRs

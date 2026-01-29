# REQUIREMENTS — CashPilot

## Purpose

Define **what CashPilot must do** in clear, testable terms. This document is **authoritative** for scope. Architecture, implementation, and tests must conform to these requirements.

---

## User Roles (RBAC)

### Roles

* **Admin**: Full visibility across businesses; manage users, roles, configuration, reporting, and audits.
* **Cashier**: Open/close sessions and enter reconciliations for assigned businesses.

### RBAC Rules (High-Level)

* Users can only access **assigned businesses**.
* Actions are denied by default unless explicitly allowed.
* UI must hide actions the role cannot perform.

---

## Functional Requirements

### FR-01 Authentication & Sessions

* Users authenticate via session-based auth.
* Sessions expire after inactivity.
* Concurrent session rules must prevent conflicts where applicable.

### FR-02 Business & User Assignment

* Admins assign users to businesses with specific roles.
* A user may belong to multiple businesses with different roles.

### FR-03 Cash Session Lifecycle

* Cashiers can open a cash session for a business.
* Only one open session per cashier/business (unless explicitly allowed).
* Sessions record opening/closing timestamps (timezone-aware).

### FR-04 Reconciliation

* Closing a session requires entering reconciliation totals.
* System validates numeric ranges and formats.
* Conflicts are flagged and visible to managers/admins.

### FR-05 Editing & Corrections

* Open sessions may be edited by permitted roles.
* Closed sessions have restricted edit paths with audit logging.

### FR-06 Reporting

* Admins can access daily, weekly, and monthly reports.
* Reports must be filterable by business and date range.
* Weekly trend report must support **PDF export**.

### FR-07 Audit Trail

* All critical changes record: actor, timestamp, and action.
* Soft deletes are used; data is never hard-deleted.

---

## Non-Functional Requirements

### NFR-01 Compatibility

* Must function on Windows 7 and legacy browsers.
* No reliance on modern JS frameworks.

### NFR-02 Performance

* Page loads should be fast on low-end hardware.
* Reports must render reliably for typical SMB data volumes.

### NFR-03 Security

* Enforce RBAC on backend (not UI-only).
* Protect against unauthorized data access across businesses.

### NFR-04 Reliability & Integrity

* Timezone-safe timestamps (Paraguay context).
* Numeric overflow prevention and validation.

---

## Data Requirements

* All monetary values stored with safe precision.
* Sessions, reconciliations, and reports must be reproducible from stored data.

---

## Out of Scope (Explicit)

* Inventory tracking.
* Payroll or HR features.
* Offline usage.
* Third-party accounting integrations.

---

## Acceptance Reference

Detailed acceptance criteria live in:

* `docs/product/ACCEPTANCE_CRITERIA.md`

---

## Change Control

Any new feature or modification must:

* Align with PRODUCT_VISION.md
* Update Acceptance Criteria
* Pass Definition of Ready
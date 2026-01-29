# PRODUCT_VISION — CashPilot

## Purpose

Define why CashPilot exists, who it is for, and what success looks like. This document is the **authoritative source** for product intent. Architecture and implementation must conform to this vision.

## Problem Statement

Small and mid-sized retail businesses struggle to maintain accurate, auditable cash-session records across shifts, staff, and locations. Manual processes and spreadsheets cause reconciliation errors, delayed reporting, weak accountability, and poor visibility for owners.

## Target Users

* **Primary:** Store owners and managers who need reliable, auditable cash-session control.
* **Secondary:** Cashiers and supervisors who open/close sessions and enter reconciliations.
* **Admin:** Business administrators managing users, roles, and permissions across locations.

## Value Proposition

CashPilot provides a **simple, auditable, server-rendered system** to open, close, reconcile, and review cash sessions with clear RBAC, strong audit trails, and reliable reports—without requiring modern hardware or browsers.

## Core Workflows (Must-Have)

1. **Authentication & RBAC**: Users authenticate and access only permitted businesses and actions.
2. **Cash Session Lifecycle**: Open session → record activity → close session with reconciliation.
3. **Reconciliation & Validation**: Validate totals, detect conflicts, flag issues.
4. **Reporting**: Daily/weekly/monthly trends and exports (including PDF).
5. **Auditability**: Immutable history of changes with actor and timestamps.

## Non-Goals

* No offline-first mode.
* No SPA rewrite (no React/Vue client).
* No accounting system replacement.
* No advanced BI or forecasting.

## Constraints

* **Legacy compatibility:** Must work on Windows 7 and older browsers.
* **Server-rendered UI:** HTMX/Jinja; minimal client JS.
* **Security:** Session-based auth, RBAC, audit fields, soft deletes.
* **Data integrity:** Timezone-aware timestamps; Paraguay context.

## Success Metrics

* Reduced reconciliation errors.
* Faster close-of-day processing.
* Clear audit trails for disputes.
* Adoption across multiple locations without retraining.

## Risks & Assumptions

* **Assumption:** Users accept server-rendered UX for reliability.
* **Risk:** Over-scope via reporting features.
* **Mitigation:** Strict adherence to Non-Goals and Acceptance Criteria.

## Out of Scope (Explicit)

* Inventory management.
* Payroll.
* POS replacement.
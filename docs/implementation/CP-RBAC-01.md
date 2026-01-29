# Implementation Plan — CP-RBAC-01: Enforce RBAC on session edit API

## Goal
Prevent privilege escalation by ensuring only:
- Admin (superadmin) OR
- Cashier who owns the session
can edit a cash session through API endpoints.

---

## Acceptance Criteria
- AC-02 RBAC Enforcement
- AC-05 Editing Rules

---

## Scope

### In scope
- `src/cashpilot/api/cash_session_edit.py` RBAC enforcement
- Ownership checks for cashier
- Tests covering allow/deny cases
- Require authentication via Depends(get_current_user)
- Remove changed_by as a request-controlled parameter; set it server-side from current_user
- Enforce existing edit-window policy for Cashier on CLOSED sessions (32h) via require_own_session

### Out of scope
- HTML routes
- Audit/flag endpoints
- Data model changes
- Reporting changes
- No changes to edit-window duration/policy (we will follow existing require_own_session behavior)

---

## PR Breakdown

### PR 1 — Require authentication + prevent `changed_by` spoofing
**Purpose**
Close the immediate security hole by ensuring session edit endpoints:
- cannot be called without authentication
- cannot accept `changed_by` from client input

**Changes**
- Add `current_user: User = Depends(get_current_user)` to all endpoints in `src/cashpilot/api/cash_session_edit.py`
- Remove `changed_by` from the endpoint signature (no client-controlled audit identity)
- Set `changed_by` server-side (e.g., `current_user.email` or `current_user.display_name_email`) when calling audit logging

**Tests**
- Unauthenticated request is rejected (401/403)

---

### PR 2 — Enforce RBAC / ownership rules (Admin superadmin, Cashier owner-only)
**Purpose**
Ensure only authorized users can edit sessions:
- Admin (superadmin): can edit any session
- Cashier: can edit only sessions they own (`session.cashier_id == current_user.id`)

**Changes**
- Reuse `cashpilot.api.auth_helpers.require_own_session` as the single authorization gate:
  - Admin (superadmin): allowed
  - Cashier: owner-only; if CLOSED, enforce 32-hour edit window
- Replace manual session loading in `cash_session_edit.py` with `require_own_session`

**Tests**
- Cashier cannot edit another cashier’s session (403/404)
- Cashier can edit own session (success)
- Admin can edit any session (success)
- Tests must reference AC-02 and AC-05 in docstrings/comments


## Test Strategy
- Add tests near existing session edit tests or create a new focused test:
  - Include AC references in docstring/comments
- Ensure tests cover both roles and at least two sessions across different users

---

## Rollback Plan
- Each PR is independently revertible; no migrations involved.

---

## Completion Checklist
- All edit endpoints protected by guard
- Tests pass
- No unauthorized edits possible
- changed_by is derived from authenticated user, not client input
# Implementation Plan — CP-RBAC-02: Restrict audit/flag endpoints to Admin

## Goal
Ensure audit visibility and session flagging are restricted to Admin users only.

---

## Acceptance Criteria
- AC-02 RBAC Enforcement
- AC-07 Audit Trail

---

## Scope

### In scope
- Enforce admin-only access on audit/flag endpoints in `src/cashpilot/api/cash_session_audit.py`
- Add tests to confirm cashiers are denied and admins are allowed

### Out of scope
- HTML routes
- Data model changes
- Reporting changes
- Business assignment policy changes

---

## PR Breakdown

### PR 1 — Admin-only guardrails
**Purpose**
Lock down audit/flag endpoints to Admin users.

**Changes**
- Add `require_admin` dependency to:
  - `POST /cash-sessions/{session_id}/flag`
  - `GET /cash-sessions/{session_id}/audit-logs`

**Risks**
- Low

**Tests**
- Admin can flag a session
- Cashier is denied flagging a session
- Admin can fetch audit logs
- Cashier is denied audit logs

---

## Migration Strategy
- Migration required? No

---

## Test Strategy Summary
- Add RBAC tests for flag/audit endpoints
- Include AC references in docstrings/comments

---

## Rollback Plan
- Revert the endpoint dependency changes
- Revert RBAC tests

---

## Completion Checklist
- Audit/flag endpoints require Admin
- Tests are green
- AC-02 and AC-07 coverage added

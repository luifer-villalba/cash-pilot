# Implementation Plan — EPIC: RBAC & Business Isolation (CRITICAL)

## Purpose
Eliminate privilege escalation paths and enforce strict access controls so that:
- Mutations are allowed only for **owners** (cashier who owns the session) or **admins**
- All access is constrained to **assigned businesses** (membership-based isolation)

This epic blocks any production release until complete.

---

## Inputs
- External Audit Report (Jan 2026)
- `docs/product/ACCEPTANCE_CRITERIA.md` (AC-01, AC-02, AC-05, AC-07)
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/CODE_MAP.md`
- `docs/architecture/DATA_MODEL.md`
- `docs/sdlc/TEST_PLAN.md`

---

## Acceptance Criteria Impacted
- **AC-01** Authentication & Access
- **AC-02** RBAC Enforcement
- **AC-05** Editing Rules
- **AC-07** Audit Trail

---

## Scope

### In scope
- Enforce RBAC + ownership on all mutating session endpoints (API + HTML flows)
- Enforce **business assignment** filtering in all read/write paths (including admins)
- Add tests to prevent regressions (RBAC/assignment)

### Out of scope
- Data model redesign (handled separately)
- Reporting recalculation changes
- UI redesign

---

## Risks
- Locking legitimate admin workflows if assignment checks are too strict
- Breaking existing tests that assumed global visibility

Mitigation:
- Add targeted tests per endpoint before/after changes
- Make failures explicit with clear error responses

---

## PR Breakdown (Mandatory)

### PR 1 — RBAC guardrails for mutating API endpoints (edit)
**Tickets:** CP-RBAC-01  
**Goal:** No user can edit sessions they don’t own unless admin.

**Changes**
- Add a single, reusable backend dependency/guard:
  - loads the target session
  - checks business assignment
  - checks ownership/admin
- Apply guard to `src/cashpilot/api/cash_session_edit.py`

**Tests**
- Unauthorized user cannot edit someone else’s session
- Cashier can edit own open session (if allowed)
- Admin can edit within assigned business

**Exit criteria**
- API edit endpoints have no bypass path

---

### PR 2 — Restrict audit/flag endpoints
**Tickets:** CP-RBAC-02  
**Goal:** Audit visibility and flagging cannot be used by unauthorized roles.

**Changes**
- Apply admin-only (and assignment-scoped) access to:
  - `src/cashpilot/api/cash_session_audit.py`

**Tests**
- Cashier denied audit/flag access
- Admin allowed within assigned business only

---

### PR 3 — Business assignment enforcement across HTML flows
**Tickets:** CP-RBAC-03  
**Goal:** UI routes cannot be used to act on unassigned businesses.

**Changes**
- Apply assignment filtering/validation inside:
  - `src/cashpilot/api/routes/sessions.py` (create/close flows)
  - any business selector lists (must show assigned businesses only)

**Tests**
- Cashier cannot create session for unassigned business
- Cashier cannot close/edit session from unassigned business

---

### PR 4 — Align access rules with Superadmin model
**Tickets:** CP-RBAC-04 (updated)
**Goal:** Admin has global business access; Cashier remains constrained.

**Changes**
- Ensure business listing and dashboards:
  - Admin sees all businesses
  - Cashier sees only assigned businesses
- Ensure access guards behave as:
  - Admin bypasses assignment checks
  - Cashier requires assignment + ownership checks

**Tests**
- Admin can access any business and sessions
- Cashier cannot access unassigned business
- Cashier cannot mutate sessions they don’t own

---

## Test Strategy (per TEST_PLAN)
- Add/extend tests for RBAC + assignment on:
  - API edit endpoints
  - audit/flag endpoints
  - HTML create/close flows
  - admin dashboards/lists

All new/updated tests must reference AC identifiers (AC-01/02/05/07) in docstring or comment.

---

## Rollback Plan
- PRs are independently revertible
- No data migrations required for this epic

---

## Completion Checklist
- All PRs merged
- No endpoint allows cross-business access
- No endpoint allows mutating sessions without owner/admin checks
- Tests green
- Audit findings for RBAC closed

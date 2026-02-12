# Implementation Plan — CP-TEST-02: Add RBAC tests for mutating APIs

## Goal
Close test coverage gaps for RBAC on mutating (POST, PUT, PATCH, DELETE) API endpoints.  
Ensure cashiers cannot create users or unassign business assignments.

---

## Acceptance Criteria
- AC-02: RBAC Enforcement
- AC-01: Business Isolation

---

## Scope

### In scope
- Add RBAC tests for `POST /users` endpoint (create user)
- Add RBAC tests for `DELETE /admin/users/{id}/businesses/{id}` endpoint (unassign business)  
- Verify endpoints return 403 for cashiers, and allow admins
- Tests must reference acceptance criteria in docstrings

### Out of scope
- API endpoint changes (all already properly protected with `require_admin`)
- Data model changes
- HTML endpoint testing (already covered)

---

## Status
✅ **COMPLETED** — 2026-02-12

---

## Implementation Summary

### PR 1 — Add RBAC tests for mutating API endpoints
**Purpose**  
Add integration tests to verify RBAC is enforced on previously untested mutating endpoints.

**Changes**
- Added `test_cashier_cannot_create_user()` to `tests/test_admin_business_assignment.py`
  - Verifies POST /users returns 403 for cashier
  - Confirms no user is created in database
  
- Added `test_admin_can_create_user()` to `tests/test_admin_business_assignment.py`
  - Verifies POST /users allows admin (not 403)
  - Basic RBAC test (functional validation tested elsewhere)

- Added `test_cashier_cannot_unassign_business()` to `tests/test_admin_business_assignment.py`
  - Verifies DELETE /admin/users/{id}/businesses/{id} returns 403 for cashier
  - Confirms assignment remains in database

**Risks**
- Low (tests only, no code changes)
- Endpoints already protected with `require_admin`

**Tests Added**
- `test_cashier_cannot_create_user` — 1 test
- `test_admin_can_create_user` — 1 test
- `test_cashier_cannot_unassign_business` — 1 test

**Test Results**
```
tests/test_admin_business_assignment.py::test_cashier_cannot_create_user PASSED
tests/test_admin_business_assignment.py::test_admin_can_create_user PASSED
tests/test_admin_business_assignment.py::test_cashier_cannot_unassign_business PASSED

319 passed in 86.17s
```

---

## Migration Strategy
- Migration required? **No**
- All API endpoints already protected
- Tests are additive only

---

## Test Strategy Summary
- Integration tests using async HTTP client (admin_client, client)
- Tests verify:
  - Cashiers get 403 Forbidden on protected endpoints
  - Admins have access (not 403)
  - Database state is unmodified when access is denied
- All tests include AC-02 reference in docstring

---

## Rollback Plan
- Revert commit to `tests/test_admin_business_assignment.py`
- No API changes to revert

---

## Completion Checklist
- ✅ Identified endpoints without RBAC test coverage
- ✅ Added tests to `test_admin_business_assignment.py`
- ✅ All tests pass (319/319)
- ✅ No regressions in existing tests
- ✅ AC-02 coverage documented
- ✅ Tests follow project conventions (async, fixtures, docstrings)

---

## Mapped Acceptance Criteria

| AC | Requirement | Test Coverage |
|----|-----------|----|
| AC-02 | RBAC: Cashiers cannot perform admin actions | `test_cashier_cannot_create_user`, `test_cashier_cannot_unassign_business` |
| AC-02 | RBAC: Admins can perform their actions | `test_admin_can_create_user` |

---

## Files Modified

```
tests/test_admin_business_assignment.py
  +test_cashier_cannot_create_user (verify POST /users is admin-only)
  +test_admin_can_create_user (verify admin has access)
  +test_cashier_cannot_unassign_business (verify DELETE unassign is admin-only)
```

---

## Notes
- **POST /users** was already protected with `require_admin` in code; tests were simply missing
- **DELETE /admin/users/.../businesses/...** was already protected with `require_admin` in code; tests were simply missing
- All endpoints covered by this task were already properly secured; tests add compliance verification only
- Test count increased from 316 to 319 (+3 tests)

---

## Sign-Off
- **Status:** Completed
- **Date:** 2026-02-12
- **Impact:** Zero breaking changes; tests only

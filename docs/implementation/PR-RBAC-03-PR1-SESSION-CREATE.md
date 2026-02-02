# PR 1: Business Assignment Enforcement on Session Create
## Ticket: CP-RBAC-03 (Phase 1 of 4)

**Goal:** No cashier can create cash sessions for businesses they are not assigned to. Admins can create sessions for any business.

---

## Changes Summary

### 1. New Helper: `require_business_assignment()` 
**File:** `src/cashpilot/api/auth_helpers.py`

**Purpose:** Reusable async dependency that validates business assignment (AC-01, AC-02).

**Behavior:**
- **Admin** (superadmin): Bypasses assignment check, returns validated business UUID
- **Cashier:** Checks `UserBusiness` membership; raises `403 Forbidden` if not assigned
- **Invalid UUID:** Raises `NotFoundError` (404)

**Logging:** Logs denied access attempts for audit trail

**Usage:**
```python
business_id = await require_business_assignment(
    business_id="550e8400-e29b-41d4-a716-446655440000",
    current_user=user,
    db=db
)
# Raises 403 if cashier lacks assignment
```

---

### 2. New Helper: `get_assigned_businesses()`
**File:** `src/cashpilot/api/utils.py`

**Purpose:** Filter business lists based on user role (AC-01).

**Behavior:**
- **Admin:** Returns ALL active businesses (superadmin access)
- **Cashier:** Returns only businesses with `UserBusiness` membership
- **Sorted:** By business name
- **Active Only:** Filters out inactive businesses

**Usage:**
```python
businesses = await get_assigned_businesses(current_user, db)
# Returns: List[Business] - filtered per role
```

---

### 3. Session Create Form: Business List Filtering
**File:** `src/cashpilot/api/routes/sessions.py` → `create_session_form()`

**Changes:**
- Replaced `get_active_businesses(db)` with `get_assigned_businesses(current_user, db)`
- Now shows only assigned businesses for cashiers
- Admin sees all businesses

**Acceptance Criteria:** AC-01 ✓

---

### 4. Session Create POST: Business Assignment Validation
**File:** `src/cashpilot/api/routes/sessions.py` → `create_session_post()`

**Changes:**
1. Added `require_business_assignment()` call at the start of request processing
2. Enforces business assignment **before** any session creation logic
3. Returns `403 Forbidden` if cashier lacks assignment
4. Admin allowed (superadmin bypass)
5. Error handling:
   - `HTTPException` (403, NotFoundError) re-raised
   - Validation errors caught separately
   - Business list refreshed on error using `get_assigned_businesses()`

**Acceptance Criteria:** AC-01 ✓, AC-02 ✓

**Flow:**
```
POST /sessions with business_id
  ↓ (1)
require_business_assignment(business_id, current_user, db)
  ├─ Admin? → Return business_uuid (no check)
  ├─ Cashier assigned? → Return business_uuid
  └─ Cashier unassigned? → 403 Forbidden ✓ STOPS HERE
  ↓ (2)
parse/validate currency, date, time
  ↓ (3)
create CashSession
  ↓ (4)
redirect to session detail
```

---

## Tests Added
**File:** `tests/test_rbac.py` → `TestRBACBusinessAssignmentOnSessionCreate`

### Test 1: Cashier Denied for Unassigned Business
```python
def test_cashier_cannot_create_session_for_unassigned_business()
```
- Creates an unassigned business
- POST /sessions with that business_id
- Expects 403 Forbidden ✓

**Criteria:** AC-01, AC-02

### Test 2: Cashier Allowed for Assigned Business
```python
def test_cashier_can_create_session_for_assigned_business()
```
- Creates a business and assigns it to cashier
- POST /sessions with that business_id
- Expects 302/303 redirect to session detail ✓

**Criteria:** AC-01, AC-02

### Test 3: Admin Allowed for Any Business
```python
def test_admin_can_create_session_for_any_business()
```
- Creates an unassigned business
- Admin POSTs /sessions (no explicit assignment)
- Expects 302/303 redirect ✓

**Criteria:** AC-02 (superadmin)

### Test 4: Form Shows Only Assigned Businesses (Cashier)
```python
def test_create_session_form_shows_only_assigned_businesses_for_cashier()
```
- Creates assigned and unassigned businesses
- GET /sessions/create as cashier
- Asserts only assigned business appears in HTML ✓

**Criteria:** AC-01

### Test 5: Form Shows All Businesses (Admin)
```python
def test_create_session_form_shows_all_businesses_for_admin()
```
- Creates multiple businesses
- GET /sessions/create as admin
- Asserts all businesses appear in HTML ✓

**Criteria:** AC-02

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Breaking admin workflows** | Low | Admin checks removed; superadmin logic verified in code |
| **Existing tests fail** | Medium | Updated error handling in create_session_post; tests added |
| **Missing assignment edge case** | Low | Business list filtered on form; validation on POST |
| **Performance (extra DB query)** | Low | Single indexed lookup on UserBusiness(user_id, business_id) |

---

## Files Modified

```
5 files changed, 253 insertions(+), 15 deletions(-)

 docs/implementation/IMPROVEMENT_BACKLOG.md |   4 +-
 src/cashpilot/api/auth_helpers.py          |  51 +++++++++++++++++++++++++
 src/cashpilot/api/routes/sessions.py       |  31 ++++++++-------
 src/cashpilot/api/utils.py                 |  30 ++++++++++++++
 tests/test_rbac.py                         | 152 +++++++++++++++++++++++++
```

---

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **AC-01: Authentication & Access** | ✓ | `require_business_assignment()` + tests + form filtering |
| **AC-02: RBAC Enforcement (Admin/Cashier)** | ✓ | Admin superadmin bypass + cashier assignment check |
| **AC-05: Editing Rules** | N/A | Out of scope (handled in PR 2-3) |
| **AC-07: Audit Trail** | ✓ | Access denial logged |

---

## Rollback Plan

- Revert commits (PRs are independent)
- No data migrations required
- No schema changes
- Rollback is safe ✓

---

## What's Next

**PR 2:** Business assignment checks on session close/reconciliation flows
**PR 3:** Business assignment checks on session edit form endpoints  
**PR 4:** Admin dashboard/list visibility alignment

---

## Reviewer Checklist

- [ ] `require_business_assignment()` handles all roles correctly
- [ ] `get_assigned_businesses()` respects admin superadmin status
- [ ] Session form shows correct business list per role
- [ ] POST /sessions enforces assignment before any DB writes
- [ ] Tests cover AC-01 and AC-02
- [ ] Error messages are clear (403 vs NotFoundError)
- [ ] No regression in existing tests
- [ ] Logging captures denied access

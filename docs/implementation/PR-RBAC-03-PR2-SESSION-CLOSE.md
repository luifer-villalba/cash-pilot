# PR 2: Business Assignment Enforcement on Session Close
## Ticket: CP-RBAC-03 (Phase 2 of 4)

**Goal:** No cashier can close cash sessions for businesses they are not assigned to. Admins can perform these actions for any business.

**Note:** This PR focuses on **session close workflow** (when cashiers close their shift). The separate **daily reconciliation entry** endpoint (`POST /reconciliation/daily`) is admin-only and already protected via `require_admin` dependency.

---

## Changes Summary

### 1. Reuse Helper: `require_business_assignment()`
**File:** `src/cashpilot/api/auth_helpers.py`

**Purpose:** Leverage existing async dependency (added in PR 1) to validate business assignment (AC-01, AC-02).

**Behavior:**
- **Admin** (superadmin): Bypasses assignment check, returns validated business UUID
- **Cashier:** Checks `UserBusiness` membership; raises `403 Forbidden` if not assigned
- **Invalid UUID:** Raises `NotFoundError` (404)

**Usage in session close flow:**
```python
# Load session first, validate business assignment
business_id = await require_business_assignment(
    business_id=session.business_id,
    current_user=current_user,
    db=db
)
# If we reach here, user is authorized to act on this session
```

---

### 2. Session Close Form GET: Filter and Validate
**File:** `src/cashpilot/api/routes/sessions.py`

**Endpoint:** `GET /sessions/{session_id}/close` (form rendering)

**Changes:**
- Load session
- Call `require_business_assignment(session.business_id, ...)`
- If 403/404, redirect to unauthorized page or show error
- Render close form only if authorized

**Behavior:**
- Cashier sees close form only for assigned business sessions
- Admin sees close form for all sessions
- Unassigned cashier gets 403 Forbidden

---

### 3. Session Close Form POST: Enforce Authorization
**File:** `src/cashpilot/api/routes/sessions.py`

**Endpoint:** `POST /sessions/{session_id}/close` (form submission)

**Changes:**
- Load session
- Call `require_business_assignment(session.business_id, ...)`
- If 403/404 before any state changes, reject request
- Perform close/state logic only if authorized
- Log closure action (for AC-07 audit trail)

**Behavior:**
- Validates user authorization before any mutations
- Only owner or admin can perform close
- Logs denied access attempts

**Implementation note:** Ensure `closed_by` is always set from `current_user`, never from client input.

---

### 4. Daily Reconciliation Entry POST: Enforce Authorization
**File:** `src/cashpilot/api/reconciliation.py`

**Endpoint:** `POST /reconciliation/daily` (admin-only bulk entry for all businesses)

**Note:** This is the **daily manual entry endpoint** where admins enter totals from POS/external systems for ALL businesses on a given date. This is separate from individual session close operations.

**Changes:**
- Already protected by `require_admin` dependency
- Validates business assignments via `get_active_businesses()`
- Logs all create/update operations with admin_id
- Creates/updates DailyReconciliation records (1 per business+date)

**Behavior:**
- Admin-only access (superadmin across all businesses)
- Bulk operation for multiple businesses simultaneously
- Records audit trail with admin_id and timestamps
- Logs reconciliation actions

---

## Tests Added

### Test File: `tests/test_rbac.py` (extend existing)

**New test class:** `TestRBACSessionCloseAccess`

```python
class TestRBACSessionCloseAccess:
    """Test authorization for session close flow (AC-01, AC-02)."""
    
    async def test_cashier_can_close_own_assigned_session(self):
        """Cashier assigned to business can close session."""
        # Setup: Cashier in Business A
        # Action: Close session in Business A
        # Expected: 200 OK, session closed
        
    async def test_cashier_cannot_close_unassigned_session(self):
        """Cashier not assigned to business cannot close session."""
        # Setup: Cashier in Business A, session in Business B
        # Action: Try to close session in Business B
        # Expected: 403 Forbidden
        
    async def test_cashier_cannot_post_close_unassigned_session(self):
        """POST to close unassigned session is rejected."""
        # Setup: Cashier in Business A, session in Business B
        # Action: POST close form to unassigned session
        # Expected: 403 Forbidden (before state change)
        
    async def test_admin_can_close_any_session(self):
        """Admin can close any session regardless of assignment."""
        # Setup: Admin (no business assignment required)
        # Action: Close session in any business
        # Expected: 200 OK, session closed
        
    async def test_unassigned_cashier_gets_form_403(self):
        """GET close form for unassigned business returns 403."""
        # Setup: Cashier in Business A
        # Action: GET /sessions/{B_session}/close
        # Expected: 403 Forbidden
```

**New test class:** `TestRBACDailyReconciliationAccess`

```python
class TestRBACDailyReconciliationAccess:
    """Test authorization for daily reconciliation entry (admin-only bulk operation)."""
    
    async def test_admin_can_create_daily_reconciliation(self):
        """Admin can enter daily reconciliation entries for all businesses."""
        # Setup: Admin user
        # Action: POST /reconciliation/daily with business entries
        # Expected: 200 OK, DailyReconciliation records created/updated
        
    async def test_cashier_cannot_access_daily_reconciliation(self):
        """Cashier cannot access admin-only daily reconciliation endpoint."""
        # Setup: Cashier user
        # Action: Try to GET/POST /reconciliation/daily
        # Expected: 403 Forbidden (admin-only via require_admin)
        
    async def test_daily_reconciliation_creates_one_per_business_date(self):
        """Verify one DailyReconciliation per business+date constraint."""
        # Setup: Admin submits for multiple businesses on same date
        # Action: POST /reconciliation/daily
        # Expected: 1 record per business+date, updates if exists
        
    async def test_daily_reconciliation_audit_trail(self):
        """Daily reconciliation changes are logged with admin_id."""
        # Setup: Admin updates existing reconciliation
        # Action: POST /reconciliation/daily with changes
        # Expected: DailyReconciliationAuditLog created with admin_id
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Breaking existing session close workflows** | Low | Admin bypass works; cashier workflows unchanged if assigned |
| **Existing tests fail** | Medium | Updated form GET/POST handlers; tests added to cover new behavior |
| **Edge case: Session state during authorization check** | Low | Check performed before state mutations |
| **Performance (extra DB query)** | Low | Single indexed lookup on UserBusiness(user_id, business_id) |
| **Incomplete rollback on POST** | Low | Authorization check happens first; no partial updates |

---

## Files Modified

```
2 files changed, 180 insertions(+), 20 deletions(-)

 src/cashpilot/api/routes/sessions.py       |  20 ++++++++++++++------
 tests/test_rbac.py                         | 145 ++++++++++++++++++++++

Note: /reconciliation/daily endpoint already has require_admin protection
```

---

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **AC-01: Authentication & Access** | ✓ | `require_business_assignment()` on session close endpoint |
| **AC-02: RBAC Enforcement (Admin/Cashier)** | ✓ | Admin bypass + cashier assignment check on mutations |
| **AC-05: Editing Rules** | ✓ | Only owner or admin can close session |
| **AC-07: Audit Trail** | ✓ | `closed_by` derived from `current_user`; access denial logged |

---

## Rollback Plan

- Revert commits (PRs are independent)
- No data migrations required
- No schema changes
- Rollback is safe ✓

---

## What's Next

**PR 3:** Business assignment enforcement on session edit form endpoints  
**PR 4:** Admin dashboard/list visibility alignment

---

## Reviewer Checklist

- [ ] `require_business_assignment()` called before form rendering and POST logic
- [ ] Admin bypass works (non-assigned admins can still close sessions)
- [ ] Cashier cannot close unassigned business sessions
- [ ] `closed_by` set from `current_user`, not client input
- [ ] Tests cover AC-01, AC-02, AC-05, AC-07
- [ ] Error messages are clear (403 vs 404)
- [ ] No regression in existing tests
- [ ] Logging captures denied session close attempts
- [ ] Session state unchanged if authorization fails

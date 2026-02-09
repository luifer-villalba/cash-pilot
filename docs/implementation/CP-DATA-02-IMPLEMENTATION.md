# IMPLEMENTATION_PLAN — CP-DATA-02

## Enforce Single Open Session per Cashier/Business

---

## Goal

Prevent multiple concurrent open sessions for the same cashier within the same business, ensuring data integrity and reducing reconciliation errors.

---

## Acceptance Criteria

* AC-03 (Cash Session Lifecycle): Single open session per cashier/business
* Must work for cashiers with multiple business assignments
* Clear, actionable UX feedback when conflict occurs

---

## Scope

### In Scope

* **Database constraint** — Add unique constraint to prevent duplicates
* **API validation** — Check for existing open session before allowing creation
* **UI error handling** — Display clear error message with recovery options
* **Tests** — Comprehensive coverage of happy path and conflict scenarios
* **Audit logging** — Log conflict detection attempts

### Out of Scope

* Automatic session closing (manual user action only)
* Session timeout policies (separate feature)
* Historical conflict analysis

---

## Implementation Strategy

### UX Design (Final Approach)

**Prevention at API level:** Prevent the duplicate from being saved  
**UI feedback:** Clear error dialog on form submission:

```
┌─────────────────────────────────┐
│ ⚠ Can't Open New Session        │
├─────────────────────────────────┤
│ You have an open session from    │
│ 2:15 PM                         │
│                                 │
│ [Ver Sesión] [Cerrar]           │
└─────────────────────────────────┘
```

* **Ver Sesión** — Navigate to existing open session
* **Cerrar** — Close existing session manually, then retry

---

## PR Breakdown

### PR 1 — Database & API Foundation

**Purpose:** Add database constraint and validation logic

**Changes**

* Database migration: Add unique constraint on `(cashier_id, business_id)` with `WHERE status='OPEN' AND is_deleted=FALSE`
  * File: `alembic/versions/fce9b0c2d3a4_add_single_open_session_constraint.py`
  * Constraint name: `uq_cash_sessions_one_open_per_cashier_business`
  * Partial index: `WHERE status = 'OPEN' AND is_deleted = FALSE`

* Helper function for checking open sessions
  * File: `src/cashpilot/api/auth_helpers.py`
  * New function: `async def get_open_session_for_cashier_business(cashier_id, business_id, db) -> CashSession | None`
  * Returns existing open (non-deleted) session or None

* API validation in session creation
  * File: `src/cashpilot/api/routes/sessions.py`
  * Pre-check for existing open session before save
  * Catch `IntegrityError` and verify it's due to duplicate session (otherwise re-raise with detailed logging)
  * Convert duplicate session error to user-friendly message with recovery options

**Risks:** Medium  
* Database migration must be tested on staging with existing data
* Partial unique indexes may behave differently across databases

**Tests**

* Unit test: `test_get_open_session_for_cashier_business_returns_session()`
* Unit test: `test_get_open_session_for_cashier_business_returns_none_if_closed()`
* Integration test: `test_prevent_duplicate_open_session_same_business()`
* Integration test: `test_allow_open_session_different_business_same_cashier()`
* Integration test: `test_allow_open_session_if_previous_closed()`
* Integration test: `test_open_session_allows_with_soft_deleted_open()` - verifies soft-deleted OPEN sessions don't block new sessions

---

### PR 2 — UI Error Display & Recovery

**Purpose:** Display error and provide recovery actions

**Changes**

* Form submission error handling
  * File: `src/cashpilot/api/routes/sessions.py`
  * Catch `SessionAlreadyOpenError` specifically
  * Extract session details (ID, opened_time)
  * Return error response with session details

* Error template
  * File: `templates/sessions/create_session.html` (or create `sessions/_error_duplicate_open.html`)
  * Display warning box with:
    - Existing session details
    - "Ver Sesión" button (redirects to session view)
    - "Cerrar" button (redirects to close form)
  * Use Tailwind warning styling (yellow/amber)

* JavaScript helper (if needed for form re-submission)
  * File: `static/js/sessions.js`
  * Optional: Auto-populate after user closes existing session

**Risks:** Low  
* CSS styling must match existing design
* Error message must be localized (es-PY + en)

**Tests**

* E2E test: `test_duplicate_open_session_shows_error_dialog()`
* E2E test: `test_can_view_existing_session_from_error_dialog()`
* E2E test: `test_can_close_existing_session_from_error_dialog()`
* Localization test: `test_error_message_is_localized()`

---

### PR 3 — Audit Logging & Documentation

**Purpose:** Log conflict detection and document the feature

**Changes**

* Audit logging
  * File: `src/cashpilot/core/logging.py`
  * Log duplicate open session attempt with:
    - `cashier_id`, `business_id`
    - existing `session_id`
    - timestamp

* Documentation
  * File: `docs/product/FEATURE_DOCS.md` (new section)
  * Explain single open session rule
  * Recovery steps for users

* README update
  * Update `docs/product/REQUIREMENTS.md` if needed
  * Add note about session lifecycle constraints

**Risks:** Low  
* Documentation must stay in sync with code

**Tests**

* Unit test: `test_duplicate_session_attempt_is_logged()`
* Unit test: `test_log_contains_correct_session_details()`

---

## Migration Strategy

### Database Migration

**Forward migration:**

```sql
-- Create partial unique index (PostgreSQL)
CREATE UNIQUE INDEX uq_cash_sessions_one_open_per_cashier_business
ON cash_sessions(cashier_id, business_id)
WHERE status = 'OPEN';
```

**Backward/Rollback:**

```sql
DROP INDEX uq_cash_sessions_one_open_per_cashier_business;
```

**Data considerations:**

* If existing data has multiple open sessions for same cashier/business:
  * Migration will fail with constraint violation
  * **Pre-flight check:** Run script to identify conflicts
  * **Resolution:** Admin must manually close older sessions before migration
  * **Documentation:** Include conflict detection script in migration file

---

## Test Strategy Summary

### New Tests to Add

**File:** `tests/test_single_open_session.py` (new)

```python
class TestSingleOpenSessionConstraint:
    """Test CP-DATA-02: Single open session per cashier/business."""
    
    # Happy path
    async def test_create_open_session_success()
    async def test_cashier_can_have_open_in_different_businesses()
    async def test_can_open_new_session_after_closing_previous()
    
    # Conflict detection
    async def test_prevent_duplicate_open_session()
    async def test_error_response_includes_existing_session_id()
    async def test_error_response_is_actionable()
    
    # Edge cases
    async def test_closed_session_does_not_block_new_open()
    async def test_admin_cannot_bypass_constraint()
    async def test_concurrent_create_attempts_only_one_succeeds()
```

**File:** `tests/test_sessions.py` (extend existing)

* Add tests for each recovery action in UI

### Existing Tests to Update

* `tests/test_session_conflicts.py` — Update `test_allow_overlap_checkbox()` if overlap checkbox is removed
* `tests/test_cash_session.py` — Add `test_open_session_duplicate()` if not present

### Manual Checks

* Verify constraint works on PostgreSQL (production DB)
* Test on database with pre-existing conflicting sessions
* Manual UX test: Try to open duplicate, verify error, verify recovery actions work

---

## Rollback Plan

### If Problem Detected Before Release

1. Revert PR 1 (remove migration)
2. Revert PR 2 (remove UI changes)
3. Revert PR 3 (remove logging/docs)
4. Run backward migration to drop constraint

### If Problem Detected in Production

1. **Immediate:** Remove unique constraint (pre-staged SQL)
   ```sql
   DROP INDEX IF EXISTS uq_cash_sessions_one_open_per_cashier_business;
   ```
2. **Communication:** Inform users why duplicate sessions possible during rollback
3. **Root cause analysis:** Identify which PR caused the issue
4. **Re-release:** Fix issue and test on staging

---

## Completion Checklist

Work is complete when:

- [ ] All 3 PRs merged to `main`
- [ ] Database migration applies cleanly on staging
- [ ] All new tests pass (unit + integration + E2E)
- [ ] No existing tests regressed
- [ ] Conflict detection logged and auditable
- [ ] Error messages localized (es-PY + en)
- [ ] Documentation updated and reviewed
- [ ] Manual UX testing completed
- [ ] Acceptance criteria AC-03 validated
- [ ] No legacy compatibility regression (Windows 7, IE11 bypass if applicable)
- [ ] Backlog item status updated to "Completed" with date

---

## Change Control

Any deviation from this plan must:

* Be documented in a comment on the PR
* Be explicitly approved in the PR review

**Approved Changes:**
* None yet

---

## Ticket Status Update

When work is completed, update:

**File:** `docs/implementation/IMPROVEMENT_BACKLOG.md`

**Change:**
```markdown
### CP-DATA-02 — Enforce single open session per cashier/business

* **Status:** Completed (YYYY-MM-DD)
```

---

## Implementation Notes

### Why This Approach?

1. **Database constraint first** — Prevents race conditions and accidental duplicates at source
2. **API validation** — Catches constraint violation gracefully with user-friendly error
3. **UX preventive** — Form submission fails fast with actionable recovery options
4. **No auto-close** — User remains in control; they decide to close existing session manually
5. **Multi-business aware** — Constraint scoped to (cashier_id + business_id) tuple

### Known Limitations

* Migration will fail if production has conflicting sessions (manual intervention needed)
* Unique constraint is partial (PostgreSQL syntax); may need adjustment for other databases
* No automatic conflict resolution; users must close manually

### Future Improvements

* Session timeout policy (auto-close after X hours)
* Session handoff (transfer to another cashier)
* Duplicate merge (combine two open sessions into one)


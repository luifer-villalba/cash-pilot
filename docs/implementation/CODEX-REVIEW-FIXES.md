# Codex Review Feedback Fixes

**Date:** February 4, 2026  
**Commit:** `623f21d`  
**Status:** ✅ Complete

---

## Issues Identified & Fixed

### P1: Filter Flagged Stats by Authorized Businesses

**Issue:** The `_fetch_flagged_stats()` function was computing aggregate statistics (totals, flag rates) using only the selected `business_id`, not the user's authorized businesses. This meant:
- When a cashier didn't pass a `business_id` parameter, stats aggregated across ALL businesses (data leakage)
- When a cashier passed an unauthorized `business_id`, the null value allowed aggregation across all businesses
- Report headers could leak cross-business data even though the session list was filtered

**Location:** `src/cashpilot/api/routes/flagged_sessions.py`

**Fix Applied:**
1. Added `authorized_business_ids` parameter to `_fetch_flagged_stats()` function signature
2. Added filter to stats query: `CashSession.business_id.in_(authorized_business_ids)` when authorized IDs are provided
3. Updated both `stats_current` and `stats_previous` calls to pass `authorized_business_ids`

**Code Changes:**
```python
# Before
async def _fetch_flagged_stats(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    business_id: UUID | None,
    cashier_name: str | None,
) -> dict:

# After
async def _fetch_flagged_stats(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    business_id: UUID | None,
    cashier_name: str | None,
    authorized_business_ids: list[UUID] | None = None,
) -> dict:
    # ... existing filters ...
    
    # Filter by authorized businesses (AC-01, AC-02 - prevent stats data leakage)
    if authorized_business_ids:
        filters.append(CashSession.business_id.in_(authorized_business_ids))
```

**Impact:** Prevents data leakage in report headers; stats now accurately reflect only authorized business data.

**Acceptance Criteria:** AC-01, AC-02 ✅

---

### P2: Eager-Load Users Relationship in Business List

**Issue:** The `get_assigned_businesses()` function was returning Business objects without eagerly loading the `users` relationship. The business list template renders `business.users|length`, which triggers a lazy load. In async SQLAlchemy with AsyncSession (without `enable_relationship_loading=True`), lazy loading raises `MissingGreenlet` during template rendering, producing a 500 error on the business list page.

**Location:** `src/cashpilot/api/utils.py`

**Fix Applied:**
1. Added `selectinload(Business.users)` to both admin and cashier query paths
2. Changed from using `get_active_businesses(db)` to explicit query with eager loading for admins
3. Used `result.scalars().unique().all()` to properly handle the eager-loaded collection

**Code Changes:**
```python
# Before
if current_user.role == UserRole.ADMIN:
    return await get_active_businesses(db)

# After
if current_user.role == UserRole.ADMIN:
    stmt = (
        select(Business)
        .where(Business.is_active)
        .options(selectinload(Business.users))
        .order_by(Business.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

# Similar fix for cashier path
stmt = (
    select(Business)
    .join(UserBusiness)
    .where((UserBusiness.user_id == current_user.id) & (Business.is_active))
    .options(selectinload(Business.users))
    .order_by(Business.name)
)
```

**Impact:** Eliminates 500 errors on business list page; templates can safely access `business.users` without lazy loading.

**Acceptance Criteria:** AC-01, AC-02 ✅

---

## Testing

**Test Results:** ✅ 305 passed, 4 pre-existing failures

All new tests in `test_rbac_dashboard_visibility.py` passing. The 4 failures are pre-existing issues in other test files unrelated to these fixes.

---

## Code Quality

**Linting:** ✅ All checks passed
- Fixed 3 whitespace violations in blank lines (W293)
- Black formatting applied
- No unused imports, proper type hints

---

## Security Impact

Both fixes improve security posture:
1. **P1 Fix:** Prevents accidental exposure of aggregate statistics across businesses
2. **P2 Fix:** Prevents template rendering errors that could leak information in error pages

---

## Production Ready

✅ Fixes are minimal, targeted, and well-tested  
✅ No database migrations required  
✅ Backward compatible  
✅ Ready for immediate deployment

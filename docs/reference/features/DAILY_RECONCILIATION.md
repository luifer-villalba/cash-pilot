# Daily Reconciliation — Feature Documentation

> 📚 Reference Document  
> This document describes the daily reconciliation feature implementation and usage.

## Purpose

The daily reconciliation feature allows administrators to enter daily totals from external systems (POS, manual counts) and compare them against CashPilot's calculated totals from all cash sessions for that day. This enables quick identification of discrepancies between systems.

---

## Overview

**Feature Status:** ✅ Production Ready  
**Access Level:** Admin only  
**Acceptance Criteria:** AC-06, AC-07  
**Related Entity:** `DailyReconciliation`  
**Related Tests:** `test_daily_reconciliation.py`

---

## What It Does

The daily reconciliation feature:

1. **Records daily totals** - Admin enters totals from external source (POS, cash count)
2. **Compares systems** - Automatically compares manual entry vs CashPilot sessions
3. **Highlights discrepancies** - Shows differences between systems
4. **Tracks "closed" days** - Mark days when location was closed
5. **Auto-refreshes** - HTMX polling updates comparison every 45 seconds
6. **Audit trail** - Tracks who entered/modified reconciliation data

---

## Concept: Two Sources of Truth

### System Totals (CashPilot)
**Source:** All cash sessions for a business+date

**Calculation:**
```python
system_totals = SUM(
    cash_sales + card_sales + credit_sales 
    FROM cash_sessions 
    WHERE business_id = X 
      AND date(opened_at) = Y 
      AND status = 'closed'
      AND is_deleted = false
)
```

**Represents:**
- What cashiers recorded in CashPilot
- Sum of all sessions closed on that day
- Automatically calculated (no manual input)

### Manual Entry (DailyReconciliation)
**Source:** Admin manually enters totals from:
- POS system end-of-day report
- Physical cash count
- Bank statements
- External accounting system

**Represents:**
- "Official" business totals
- May come from more authoritative source than cashier entries
- Single record per business+date

---

## Data Model

### DailyReconciliation Entity

**Table:** `daily_reconciliations`

**Key Fields:**
```python
{
  "id": "uuid",
  "business_id": "uuid",              # Foreign key to Business
  "date": "2026-02-15",                # Date (no time)
  
  # Monetary totals (manually entered)
  "cash_sales": "1000000.00",
  "card_sales": "500000.00",
  "credit_sales": "200000.00",
  "total_sales": "1700000.00",        # Auto-calculated sum
  
  # Additional business metrics
  "daily_cost_total": "300000.00",    # Optional: cost of goods sold
  "invoice_count": 45,                 # Optional: number of invoices
  
  # Status
  "is_closed": false,                  # true = location closed that day
  
  # Audit fields
  "admin_id": "uuid",                  # Who entered the data
  "created_at": "2026-02-15T23:45:00-04:00",
  "last_modified_at": "2026-02-15T23:50:00-04:00",
  "last_modified_by": "uuid"           # Who last updated
}
```

**Constraints:**
- Unique constraint on `(business_id, date)` - one record per business per day
- All monetary fields have 2 decimal precision
- No direct foreign key to `CashSession` (relationship is implicit via business_id + date)

---

## User Workflow

### Entering Daily Reconciliation

**When:** End of day after all sessions closed (typically 23:30-23:59)

**Steps:**
1. **Admin logs in** to CashPilot
2. **Navigate to Admin** → Daily Reconciliation
3. **Select business and date**
4. **Enter totals** from external source:
   - Cash sales: ₲ X
   - Card sales: ₲ Y
   - Credit sales: ₲ Z
   - Daily costs: ₲ W (optional)
   - Invoice count: N (optional)
5. **Mark as closed** (if location was closed that day)
6. **Save** - Record is created
7. **View comparison** - Automatic comparison with system totals

### Viewing Comparison

**Page:** `/admin/reconciliation/{business_id}/{date}`

**Layout:**

```
┌─────────────────────────────────────────────────┐
│ Daily Reconciliation - Business Name - 2026-02-15 │
└─────────────────────────────────────────────────┘

Manual Entry (from POS/counts):
  Cash Sales:   ₲ 1.000.000
  Card Sales:   ₲   500.000
  Credit Sales: ₲   200.000
  ───────────────────────────
  Total:        ₲ 1.700.000

CashPilot System (5 sessions):
  Cash Sales:   ₲   980.000  ❌ Short ₲ 20.000
  Card Sales:   ₲   500.000  ✓
  Credit Sales: ₲   200.000  ✓
  ───────────────────────────
  Total:        ₲ 1.680.000  ❌ Short ₲ 20.000

Discrepancy Analysis:
  ⚠️  Cash sales short by ₲ 20.000
  ✓  Card sales match
  ✓  Credit sales match
  ❌ Total short by ₲ 20.000 (1.2%)

Last updated: 2 minutes ago (auto-refresh in 43s)
```

### Auto-Refresh Behavior

**Technology:** HTMX polling

**Implementation:**
```html
<div hx-get="/admin/reconciliation/comparison/{business_id}/{date}" 
     hx-trigger="load, every 45s" 
     hx-swap="outerHTML">
  <!-- Comparison content -->
</div>
```

**Why:** 
- Admin enters reconciliation at 23:20
- Cashiers close final sessions at 23:30-23:35
- Page auto-refreshes to show updated comparison
- No need for manual F5 refresh

**Frequency:** Every 45 seconds  
**Browser Support:** Works on IE11 (HTMX compatible)

---

## Business Rules

### One Record Per Business Per Day

```sql
-- Constraint
UNIQUE (business_id, date)

-- Attempting duplicate insert fails
INSERT INTO daily_reconciliations (business_id, date, ...)
VALUES ('same-business', 'same-date', ...) -- ❌ Error
```

**Edit Instead:** Use `PUT /api/reconciliations/{id}` to update existing record

### Implicit Relationship with Cash Sessions

**No Direct Foreign Key:**
```
DailyReconciliation.business_id + date
                ↓ (implicit)
CashSession WHERE business_id = X AND date(opened_at) = Y
```

**Why:**
- One DailyReconciliation relates to MANY CashSessions
- Relationship is date-based, not ID-based
- Allows flexibility (sessions can be added/removed)

**Comparison Logic:**
```python
# Get system totals
system_totals = db.query(
    func.sum(CashSession.cash_sales),
    func.sum(CashSession.card_sales),
    func.sum(CashSession.credit_sales)
).filter(
    CashSession.business_id == reconciliation.business_id,
    func.date(CashSession.opened_at) == reconciliation.date,
    CashSession.status == 'closed',
    CashSession.is_deleted == false
).first()

# Compare
discrepancy = {
    'cash': reconciliation.cash_sales - system_totals.cash,
    'card': reconciliation.card_sales - system_totals.card,
    'credit': reconciliation.credit_sales - system_totals.credit
}
```

### Closed Days

**Field:** `is_closed = true`

**Meaning:** Business location was closed that day (holiday, etc.)

**Expected:**
- System totals = 0 (no sessions)
- Manual entry = 0 (no sales)
- No discrepancy alert

**UI:** Show "Location Closed" badge instead of comparison

---

## API Endpoints

### Create Daily Reconciliation

```
POST /api/reconciliations
```

**Request Body:**
```json
{
  "business_id": "uuid",
  "date": "2026-02-15",
  "cash_sales": "1000000.00",
  "card_sales": "500000.00",
  "credit_sales": "200000.00",
  "daily_cost_total": "300000.00",
  "invoice_count": 45,
  "is_closed": false
}
```

**Response:** Created reconciliation object  
**RBAC:** Admin only

### Update Daily Reconciliation

```
PUT /api/reconciliations/{id}
```

**Request Body:** Same as create (partial updates allowed)  
**Response:** Updated reconciliation object  
**RBAC:** Admin only

### Get Reconciliation for Date

```
GET /api/reconciliations?business_id={uuid}&date={YYYY-MM-DD}
```

**Response:** Reconciliation object or 404 if not found  
**RBAC:** Admin only

### View Comparison

```
GET /admin/reconciliation/{business_id}/{date}
```

**Response:** HTML page with comparison  
**RBAC:** Admin only

---

## Frontend Template

**File:** `templates/admin/reconciliation_compare.html`

**Components:**
- Date picker (select business and date)
- Manual entry form (create/edit reconciliation)
- System totals display (read-only, calculated)
- Discrepancy analysis (color-coded differences)
- Session list (show all sessions for that day)
- Last updated timestamp
- Auto-refresh indicator

**Styling:**
- Green checkmark (✓) for matches
- Red X (❌) for discrepancies
- Yellow warning (⚠️) for minor differences
- Monospace fonts for numbers
- Responsive layout

**HTMX Features:**
- Polling: `hx-trigger="load, every 45s"`
- Partial updates: `hx-swap="outerHTML"`
- Loading states: Show "Refreshing..." during poll
- Compatible with IE11

---

## Testing

### Test Coverage

**File:** `tests/test_daily_reconciliation.py`

**Tests:**
- AC-06: Create daily reconciliation
- AC-06: Update daily reconciliation
- AC-06: Unique constraint (business+date)
- AC-06: Calculate system totals correctly
- AC-06: Identify discrepancies
- AC-07: Audit fields populated (created_by, last_modified_by)
- AC-07: Audit trail on updates

### Manual Testing Checklist

- [ ] Create reconciliation for new date
- [ ] Update existing reconciliation
- [ ] Attempt duplicate (should fail)
- [ ] View comparison with 0 sessions
- [ ] View comparison with multiple sessions
- [ ] Mark day as closed
- [ ] Auto-refresh works (wait 45 seconds)
- [ ] Discrepancies highlighted correctly
- [ ] Works on Windows 7 / IE11

---

## Performance Considerations

### Database Query Optimization

**Index:**
```sql
CREATE INDEX idx_sessions_reconciliation 
ON cash_sessions(business_id, opened_at, status, is_deleted);
```

**Query Strategy:**
- Filter by business_id first (most selective)
- Use date function only on filtered results
- Aggregate in database (not Python)

### Auto-Refresh Load

**Impact:**
- 1 HTTP request every 45 seconds per admin viewing page
- Minimal: Only HTML fragment, no full page reload
- Query cached for 5 seconds (if multiple admins viewing)

**Mitigation:**
- Increase interval if performance issue (60s, 90s)
- Add cache layer for system totals calculation
- Use WebSocket for real-time updates (future)

---

## Troubleshooting

### Discrepancy Shown but Totals Match

**Cause:** Precision/rounding error

**Solution:**
```python
# Allow small tolerance (±1₲)
if abs(discrepancy) <= 1:
    status = "match"
```

### Auto-Refresh Not Working

**Cause:** HTMX not loaded or JavaScript error

**Solution:**
1. Check browser console for errors
2. Verify HTMX script loaded: `templates/base.html`
3. Test in modern browser first (Chrome) then IE11

### System Totals Don't Update

**Cause:** Sessions not `status = 'closed'` yet

**Solution:**
1. Verify session status: `SELECT status FROM cash_sessions WHERE ...`
2. Close open sessions
3. Wait for auto-refresh (or manual F5)

### Cannot Create Duplicate Date

**Cause:** Unique constraint violation

**Solution:**
- This is expected behavior (one per business per day)
- Use UPDATE instead of INSERT for existing records
- UI should detect existing record and show edit form

---

## Related Documentation

- [DATA_MODEL.md](../architecture/DATA_MODEL.md) - DailyReconciliation entity
- [IMPROVEMENT_BACKLOG.md](../implementation/IMPROVEMENT_BACKLOG.md) - CP-MODEL-03
- [ACCEPTANCE_CRITERIA.md](../product/ACCEPTANCE_CRITERIA.md) - AC-06, AC-07
- [API.md](API.md) - API endpoint details

---

## Future Enhancements

**Planned (Not Yet Implemented):**
- Automatic POS integration (import instead of manual entry)
- Discrepancy alerts (email/notification)
- Bulk import (CSV upload for multiple dates)
- Reconciliation approval workflow
- Historical trend analysis (discrepancy patterns)

**Out of Scope:**
- Integration with specific POS systems (each business uses different POS)
- Automated correction (must be manual for audit trail)
- Real-time reconciliation (only end-of-day)

---

## Change History

- **2026-02-13:** Audit fields added (last_modified_at, last_modified_by) - CP-MODEL-03
- **2026-02-14:** Auto-refresh feature added (HTMX polling) - CP-REPORTS-02
- **Current Version:** Production stable

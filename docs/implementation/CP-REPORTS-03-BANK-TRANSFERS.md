# CP-REPORTS-03 — Display Bank Transfers in Reconciliation

**Epic:** EPIC 6 — Reporting UX & Comparisons (MEDIUM)  
**Priority:** HIGH / ASAP  
**Status:** In Progress (Started 2026-02-16)  

---

## Objective

Enable admins to view all bank transfer line items from cash sessions on the daily reconciliation comparison page, allowing them to cross-check transfers against bank statements during evening close.

---

## Problem Statement

**Current State:**  
- Reconciliation page shows only aggregated sales/cash/card totals
- Individual bank transfer line items are only visible in individual session modals
- Admin cannot see all transfers for a date/business in one place during evening close

**Pain Point:**  
Admin must either:
1. Click into each session individually to find transfer details, OR
2. Manually cross-check the aggregated `bank_transfer_total` against bank statement (no detail)

**Impact:**  
- Reconciliation is incomplete and error-prone
- Cannot identify missing or incorrect transfers quickly
- Audit trail incomplete for banking exceptions

---

## Acceptance Criteria

- [ ] **AC-1:** Admin can view all bank transfer line items from cash sessions for a business+date
- [ ] **AC-2:** Each transfer displays: description, amount, session ID (linked), cashier name, timestamp
- [ ] **AC-3:** Transfers are displayed in chronological order (earliest first)
- [ ] **AC-4:** Summary row shows total count and sum of all transfers for the day
- [ ] **AC-5:** Transfer section is read-only (no verification/editing in Phase 1)
- [ ] **AC-6:** Section is admin-only (RBAC enforced on both backend and frontend)
- [ ] **AC-7:** All monetary amounts use monospace font and Paraguay format (Gs X.XXX)
- [ ] **AC-8:** Compatible with Windows 7/IE11 (no modern JS features)
- [ ] **AC-9:** Section integrates seamlessly with existing reconciliation_compare_results.html

---

## Design

### Data Flow

```
GET /admin/reconciliation/compare-results
  └─> Backend query:
       SELECT transfer_items
       FROM transfer_items ti
       JOIN cash_sessions cs ON ti.session_id = cs.id
       WHERE cs.business_id = X
         AND DATE(cs.opened_at) = Y
         AND ti.is_deleted = false
       ORDER BY ti.created_at ASC
```

### UI Component Placement

In `reconciliation_compare_results.html` (after Sales Reconciliation Comparison table):

```
┌─ Sales Reconciliation Comparison ─────────────┐
│ [Table with system/manual totals]             │
└───────────────────────────────────────────────┘

┌─ Bank Transfers Detail (NEW) ─────────────────┐
│ Cash transfers for {{ selected_date }}        │
│ Total: X transfers, Gs Y                      │
│                                               │
│ ┌─ Transfer 1 ─────────────────────────────┐ │
│ │ Description: Customer ABC                 │ │
│ │ Amount:      Gs 50.000                    │ │
│ │ Session:     <link to session>            │ │
│ │ Cashier:     John Perez                   │ │
│ │ Time:        14:32:05                     │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ [More transfer rows...]                      │
│                                               │
│ TOTAL: 15 transfers, Gs 1.500.000           │
└───────────────────────────────────────────────┘
```

### Backend Changes

1. **Reconciliation Route** (`src/cashpilot/api/admin.py`):
   - Add `transfer_items` list to template context  
   - Filter per business_id + date
   - Join with `cash_sessions` + `users` for cashier name

2. **Helper Function** (optional):
   - `_fetch_transfer_items_for_date(db, business_id, date)` → returns list of TransferItem objects with eagerly-loaded relationships

### Template Changes

1. **New partial:** `templates/admin/partials/transfer_items_detail.html`
   - Reusable component: transfer items table
   - Receives: `transfer_items`, `business_name`, `date`
   - Renders: card-based list (mobile) + table (desktop)

2. **Update:** `templates/admin/partials/reconciliation_compare_results.html`
   - Include new transfer_items_detail partial after main comparison table
   - Pass `transfer_items` and `selected_date` to partial

---

## Implementation Steps

### Phase 1: Backend Data Fetching

1. **Update `admin.py::reconciliation_compare_dashboard` route:**
   - Add SQL query to fetch transfer_items for business_id + date
   - Join with cash_sessions + users to get cashier name
   - Filter: `ti.is_deleted = false`
   - Order: `ti.created_at ASC`
   - Load results into context: `"transfer_items": [...]`

2. **Update `admin.py::reconciliation_compare_results_partial` route:**
   - Same query logic as main dashboard view
   - Return transfer_items in partial response for HTMX refresh

3. **No table migrations needed:**
   - `transfer_items` table already exists with all required fields
   - Just need to expose via API

### Phase 2: Template Implementation

1. **Create** `templates/admin/partials/transfer_items_detail.html`:
   - Mobile card layout (collapsible section)
   - Desktop table layout (responsive columns)
   - No edit buttons (read-only)
   - Summary footer: "Total: X transfers, Gs Y.ZZZ"

2. **Update** `templates/admin/partials/reconciliation_compare_results.html`:
   - Add transfer items detail section after comparison table
   - Include HTMX refresh logic (auto-refresh every 45s with polling)
   - Show loading spinner while fetching

### Phase 3: Testing

1. **Unit test:** `test_transfer_items_display.py`
   - Test data fetching query (filtering, ordering, joins)
   - Test calculations (count, sum)
   - Test RBAC: non-admins cannot access

2. **UI test scenarios:**
   - Display with 0 transfers (empty state)
   - Display with multiple transfers
   - Display with transfers across multiple sessions
   - Verify sorting (chronological)
   - Verify formatting (amounts, dates, times)

3. **Integration test:**
   - Full reconciliation page load with transfers
   - HTMX polling trigger
   - Window 7/IE11 compatibility check

---

## Data Dependencies

| Table | Columns Used | Notes |
|-------|------------|-------|
| `transfer_items` | id, session_id, description, amount, created_at, is_deleted | Line item details |
| `cash_sessions` | id, business_id, opened_at | Context + filtering |
| `users` | id, display_name | Cashier names |
| `daily_reconciliation` | — | Not needed for Phase 1 |

---

## RBAC & Security

- **Who can view:**  
  - Admin only (role check: `require_admin`)
  - Non-admins see nothing (no partial rendering)

- **Filtering:**  
  - Backend filters by selected business_id (from dropdown)
  - Admin can see all businesses (no further restriction)

- **Audit Trail:**  
  - No changes to transfer_items in Phase 1 (read-only)
  - View action logged in general access logs (standard pattern)

---

## Compatibility Checklist

- [ ] **Windows 7/IE11:**  
  - No ES6 (arrow functions, template literals, spread operators)
  - No modern DOM APIs (classList.toggle with force param, etc.)
  - No CSS Grid (use Tailwind's row/col system)
  - No CSS Flexbox issues: test on IE11

- [ ] **Smartphone:**  
  - Card layout works on small screens
  - Amounts are visible (no horizontal scroll)
  - Links are tappable (min 44x44px)

- [ ] **Monospace Formatting:**  
  - Use `font-mono` + `tabular-nums` for all amounts
  - Test with long descriptions (truncation)

---

## Success Criteria (DoD)

- [ ] PR: backend data fetching + reconciliation route update
- [ ] PR: transfer items template + styles
- [ ] PR: tests + compatibility verification
- [ ] Code review passed
- [ ] Manual testing on Windows 7/IE11
- [ ] Backlog updated to Completed status
- [ ] Documentation updated (DATA_MODEL.md if needed)

---

## Blockers & Risks

- **None identified** — all dependencies already exist

## Notes for Implementation

1. **Query Complexity:**  
   The SQL join is straightforward; can reuse existing `_build_comparison_data` pattern or add standalone helper

2. **Partial Refresh:**  
   The HTMX polling already works (CP-REPORTS-02 auto-refresh); just extend with transfer_items partial

3. **Styling:**  
   Use existing design patterns from `reconciliation_compare_results.html` (cards, badges, monospace amounts)

---

## Related Issues

- **Blocks:** CP-REPORTS-04 (transfer verification workflow)
- **Supports:** AC-06 (reporting accuracy), AC-07 (audit trail)
- **References:** DATA_MODEL.md (transfer_items table)

---

**Start Date:** 2026-02-16  
**Target Completion:** 2026-02-17  
**Status Tracking:** Update after each PR  

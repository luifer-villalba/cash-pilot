# DATA_MODEL — CashPilot

## Purpose

Describe the **authoritative data model** of CashPilot: entities, relationships, and invariants. This document exists to **protect reporting accuracy, auditability, and RBAC correctness**. Schema changes must align with this model and be implemented via migrations.

---

## Core Principles

* **Auditability first**: changes are traceable; history is preserved.
* **Soft deletes**: critical entities are never hard-deleted.
* **RBAC-aware relations**: access is constrained by user–business assignments.
* **Timezone-safe**: all timestamps are timezone-aware (Paraguay context).
* **Reproducible reports**: reports derive from persisted facts only.

---

## Entities

### User

Represents an authenticated person.

**Key Fields**

* `id`
* `email` (unique)
* `password_hash`
* `is_active`
* `created_at`, `updated_at`
* `role` (Admin | Cashier)  ← global role

**Rules**

* Users have no global permissions by default.
* Access is granted via assignments to businesses.

---

### Business

Represents a business/location.

**Key Fields**

* `id`
* `name`
* `timezone`
* `is_active`
* `created_at`, `updated_at`

**Rules**

* A business owns sessions, reconciliations, and reports.
* Timezone defaults to Paraguay.

---

### UserBusiness (Assignment)
Associative entity linking users to businesses (membership / access boundary).

**Key Fields**
- `id`
- `user_id` → User
- `business_id` → Business
- `created_at`

**Rules**
- Roles are **global** (stored on `User`).
- **Admins are superadmins**: they can access all businesses without assignment.
- **Cashiers require assignment**: UserBusiness defines which businesses a cashier can access.
- Cashiers must also respect **ownership** for session mutation unless explicitly allowed.

---

### CashSession

Represents a cashier work session.

**Key Fields**

* `id`
* `business_id` → Business
* `cashier_id` → User
* `status` (open | closed)
* `opened_at`, `closed_at`
* `created_by`, `updated_by`
* `deleted_at` (soft delete)

**Rules**

* Only one open session per cashier/business (unless explicitly allowed).
* Open/close timestamps must be valid and ordered.

---

### DailyReconciliation

Represents the daily manual entry of sales totals for a business (typically from POS/external system).

**Key Fields**

* `id`
* `business_id` → Business
* `date`
* Monetary totals (cash_sales, card_sales, credit_sales, total_sales)
* `daily_cost_total`, `invoice_count`
* `is_closed` (location closed that day)
* `admin_id` → User (who entered the data)
* `created_at`, `last_modified_at`, `last_modified_by`

**Rules**

* **One DailyReconciliation per business+date**: represents the entire day's totals.
* **Compared against system totals**: Sum of all CashSession records for same business+date.
* **No direct FK to CashSession**: relationship is implicit via `business_id + date`.
* Values are validated for precision and overflow.
* Discrepancies are visible in reconciliation comparison reports.

---

### AuditLog (Implicit / Embedded)

Represents the audit trail captured via audit fields.

**Captured Data**

* Actor (user)
* Action type
* Timestamp

**Rules**

* Audit data is append-only.
* No silent updates to critical entities.

---

## Relationships (Summary)

```
User ──< UserBusiness >── Business
  │                         │
  │                         ├──< CashSession (N per business+date)
  │                         │
  └─────────────────────────└──< DailyReconciliation (1 per business+date)
                                  ↑
                                  └─ compared via business_id + date
```

**Notes:**
* DailyReconciliation aggregates totals for ALL CashSessions of a given business+date.
* No direct FK between DailyReconciliation and CashSession - relationship is implicit.
* Comparison logic: SUM(CashSession WHERE business_id+date) vs DailyReconciliation(business_id+date).

---

## Invariants & Constraints

* No cross-business data access.
* Cashiers cannot modify closed sessions.
* Admins can view all data within assigned businesses.
* Reports must be reproducible from stored entities.

---

## Migrations & Change Control

* All schema changes require Alembic migrations.
* Migrations must preserve existing data.
* DATA_MODEL.md must be updated when entities or rules change.

---

## Explicit Non-Goals

* No event sourcing.
* No CQRS split.
* No denormalized reporting tables without approval.
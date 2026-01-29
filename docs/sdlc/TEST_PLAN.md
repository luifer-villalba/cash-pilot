# TEST_PLAN — CashPilot

## Purpose
Define **how behavior is verified** in CashPilot. Tests exist to prove acceptance criteria,
protect RBAC, preserve auditability, and prevent regressions—especially in reporting and
legacy compatibility.

This plan is **authoritative** for testing scope and expectations.

---

## Testing Principles
- **Behavior over implementation**: test outcomes, not internals
- **RBAC-first**: permissions are validated server-side
- **Data integrity**: reports must be reproducible
- **Legacy-safe**: UI behavior must work on Windows 7

---

## Test Types & Scope

### Unit Tests
**Purpose**: Validate pure logic and helpers  
- Location: `tests/`
- Examples:
  - Validators (numeric ranges, overflow)
  - Formatting/parsing helpers

### Integration Tests
**Purpose**: Validate interactions across layers  
- Database + ORM + business logic
- Examples:
  - Session open/close flows
  - Reconciliation persistence
  - Audit field population

### RBAC Tests (Mandatory)
**Purpose**: Prevent privilege escalation  
- Admin vs Cashier access checks
- Backend enforcement (not UI-only)
- Examples:
  - Cashier cannot access admin reports
  - Admin can view assigned businesses only

### Reporting Tests
**Purpose**: Protect financial correctness  
- Deterministic data setup
- Validate totals and filters
- Examples:
  - Daily/weekly/monthly aggregation
  - Weekly PDF export renders successfully

### UI / Template Tests (Selective)
**Purpose**: Verify server-rendered views  
- Page loads and critical actions
- HTMX interactions for key flows

---

## Mapping to Acceptance Criteria
Each feature test must reference one or more `AC-*`
identifiers from `docs/product/ACCEPTANCE_CRITERIA.md`.

---

## Definition of Done (Testing)
A change is complete when:
- Relevant tests exist or are updated
- All tests pass locally and in CI
- RBAC paths are covered
- No regression in legacy compatibility

---

## Test Data & Fixtures
- Use explicit fixtures/factories
- Avoid shared mutable state
- Prefer clarity over reuse

---

## Change Control
Updates to testing strategy require updating this document.
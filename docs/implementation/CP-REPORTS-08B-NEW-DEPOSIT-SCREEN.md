# CP-REPORTS-08B — New Envelope Deposit Screen (Batch, Multi-Business)

**Issue:** CP-REPORTS-08B  
**Epic:** EPIC 6 — Reporting UX & Comparisons (MEDIUM)  
**Severity:** High  
**Status:** 📝 Planned (2026-03-03)

---

## Context

Previous CP-REPORTS-08B implementation was reverted.
New agreed direction:
- Do not mutate envelopes inline in CP-REPORTS-08 table.
- Add a dedicated screen: `Nuevo depósito` / `New Envelope Deposit`.
- Allow selecting and depositing envelopes from more than one pharmacy in one operation.

---

## Scope (MVP)

1. Keep `GET /admin/envelopes/date-range` as report-first screen.
2. Reuse current row-selection UX from CP-REPORTS-08.
3. Add navigation from selection summary to new screen:
   - `GET /admin/envelopes/deposits/new?session_ids=...`
4. Add batch mutation endpoint:
   - `POST /admin/envelopes/deposits/batch`
5. Persist one deposit event per selected envelope row.
6. Keep envelope lifecycle and note rules.

---

## Out of Scope (MVP)

- No inline deposit forms in CP-REPORTS-08 table/cards.
- No additional dashboard/page besides the dedicated deposit screen.
- No export changes in this ticket.

---

## Functional Requirements

### A) CP-REPORTS-08 Screen

- Admin can select one or many envelope rows.
- Selection can include rows from different businesses.
- CTA `New deposit` opens dedicated screen with selected `session_ids`.

### B) New Deposit Screen

- Shows selected envelopes list with:
  - business
  - session reference
  - cashier
  - pending amount
  - input amount to deposit (per row)
- Includes batch `deposit_date`.
- Optional global note input (applied when needed).
- Supports deselecting rows before submit.

### C) Batch Deposit Submit

- Endpoint accepts selected `session_ids`, per-row amounts, and `deposit_date`.
- Validations:
  - amount > 0
  - amount <= pending for each selected envelope
  - at least one selected envelope
  - note required when resulting pending remains > 0 (existing rule)
- Persists one `EnvelopeDepositEvent` per selected row.
- Redirects back to safe report URL.

### D) RBAC

- Admin-only for both new screen and batch endpoint.
- Cashier access returns forbidden.

---

## Data Model & Persistence

Use/reuse:
- `cash_sessions.envelope_amount` as withdrawn source
- `cash_sessions.envelope_note` for note requirement flow
- `envelope_deposit_events` for partial/full deposit events

Derived values:
- `deposited_total = SUM(events.amount where is_deleted=false)`
- `pending = envelope_amount - deposited_total`
- lifecycle state from withdrawn/deposited totals

---

## API/Routes Plan

1. `GET /admin/envelopes/deposits/new`
   - query: repeated `session_ids`
   - optional `return_to` (safe redirect only)
   - response: dedicated HTML screen

2. `POST /admin/envelopes/deposits/batch`
   - form fields:
     - `session_ids` (repeated)
     - `amount_<session_id>` per selected row
     - `deposit_date`
     - `envelope_note` (optional/global)
     - `return_to` (optional)
   - response: `303` redirect to report

---

## UI Plan

### File(s)
- `templates/admin/envelopes_date_range_report.html` (selection CTA only)
- `templates/admin/envelopes_new_deposit.html` (new page)

### UX Rules
- Keep current visual system/tokens/components.
- Keep mobile + desktop compatible structure.
- Keep interactions simple (no extra modals/animations).

---

## Testing Plan

Primary test file:
- `tests/test_envelope_date_range_report.py`

Add/adjust tests for:
1. Admin can open new deposit screen with selected envelopes.
2. Admin can register a batch with envelopes from multiple businesses.
3. Amount validations (`>0`, `<= pending`).
4. Note-required behavior for pending remainder.
5. Cashier forbidden on both new routes.
6. Existing CP-REPORTS-08 read/report behaviors remain valid.

---

## Risks & Mitigations

- **Risk:** Query/form payload mismatch for dynamic amount fields.  
  **Mitigation:** Parse form data explicitly and validate selected IDs against loaded sessions.

- **Risk:** Cross-business selection introduces accidental filtering assumptions.  
  **Mitigation:** Resolve by selected session IDs only, then enforce active/not-deleted constraints server-side.

- **Risk:** Regression in CP-REPORTS-08 interactions.  
  **Mitigation:** Keep changes minimal: add CTA and redirect only, no inline mutation forms.

---

## Acceptance Criteria (MVP)

- [ ] Dedicated `Nuevo depósito` screen exists and is admin-only.
- [ ] Admin can select envelopes in CP-REPORTS-08 and open new screen.
- [ ] Admin can submit deposits for selected envelopes from multiple pharmacies.
- [ ] System prevents over-deposit per envelope.
- [ ] Note-required rule is enforced when pending remains.
- [ ] CP-REPORTS-08 remains report-first (no inline deposit forms).
- [ ] Existing report filters/sorting/selection remain functional.

---

## Files Expected to Change

- `src/cashpilot/api/admin.py`
- `templates/admin/envelopes_date_range_report.html`
- `templates/admin/envelopes_new_deposit.html` (new)
- `tests/test_envelope_date_range_report.py`
- (if missing in schema) model + migration docs references for envelope deposits

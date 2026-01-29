# CashPilot — Documentation

This directory contains the **authoritative documentation** for CashPilot.
It defines product intent, architecture, execution discipline, and AI usage rules.

If there is any conflict:
**Product > Architecture > SDLC > Reference > Runbooks**

---

## 📌 Documentation Authority

### Product (What & Why)
Authoritative definition of scope and behavior.

- `product/PRODUCT_VISION.md`
- `product/REQUIREMENTS.md`
- `product/ACCEPTANCE_CRITERIA.md`

---

### Architecture (How)
Authoritative technical decisions and system structure.

- `architecture/ARCHITECTURE.md`
- `architecture/CODE_MAP.md`
- `architecture/DATA_MODEL.md`
- `reference/architecture-decisions.md` (historical ADRs)

---

### SDLC & Execution (How We Work)
Mandatory process and governance.

- `sdlc/DEFINITION_OF_READY.md`
- `sdlc/WORKFLOW.md`
- `sdlc/IMPLEMENTATION_PLAN.md`
- `sdlc/TEST_PLAN.md`
- `sdlc/RELEASE_CHECKLIST.md`
- `sdlc/RELEASE_NOTES_TEMPLATE.md`
- `sdlc/AI_PLAYBOOK.md`

---

### Reference (Historical / Explanatory)
Non-authoritative background and guidance.

- `reference/design_readme.md`
- `reference/w7-compatibility.md`

---

### Runbooks (Operational)
Operational procedures and maintenance.

- `runbooks/backup_restore.md`

---

## 🤖 AI Usage Notice

AI tools **must comply** with:
- `sdlc/AI_PLAYBOOK.md`
- `sdlc/DEFINITION_OF_READY.md`

AI-generated output that violates these documents is rejected.

---

## Change Control

Any change to product behavior, architecture, or process must update the relevant documentation.
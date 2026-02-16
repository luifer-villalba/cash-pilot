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
- `reference/architecture-decisions.md` (historical ADRs)
- `reference/API.md` — API endpoint reference
- `reference/GETTING_STARTED.md` — Developer setup guide
- `reference/TROUBLESHOOTING.md` — Common issues and solutions
- `reference/features/WEEKLY_TREND_REPORT.md` — Weekly report feature docs
- `reference/features/DAILY_RECONCILIATION.md` — Reconciliation feature docs

---

### Runbooks (Operational)
Operational procedures and maintenance.

- `runbooks/backup_restore.md`

---

## 📖 Getting Started as a New Developer

**Recommended Reading Path:**

1. **Start Here** → [Getting Started Guide](reference/GETTING_STARTED.md) - Setup your development environment
2. **Understand Product** → [Product Vision](product/PRODUCT_VISION.md) and [Requirements](product/REQUIREMENTS.md)
3. **Learn Architecture** → [Architecture](architecture/ARCHITECTURE.md) and [Code Map](architecture/CODE_MAP.md)
4. **Follow Process** → [Workflow](sdlc/WORKFLOW.md) and [Definition of Ready](sdlc/DEFINITION_OF_READY.md)
5. **Reference as Needed** → [API Docs](reference/API.md), [Troubleshooting](reference/TROUBLESHOOTING.md)

---

## 🛠️ Quick Reference for Common Tasks

- **Setting up locally?** → [Getting Started Guide](reference/GETTING_STARTED.md)
- **API endpoints?** → [API Reference](reference/API.md)
- **Something not working?** → [Troubleshooting Guide](reference/TROUBLESHOOTING.md)
- **Working with Windows 7?** → [W7 Compatibility](reference/w7-compatibility.md)
- **Understanding reports?** → [Weekly Trend](reference/features/WEEKLY_TREND_REPORT.md), [Daily Reconciliation](reference/features/DAILY_RECONCILIATION.md)
- **Database backups?** → [Backup & Restore](runbooks/backup_restore.md)

---

## 🤖 AI Usage Notice

AI tools **must comply** with:
- `sdlc/AI_PLAYBOOK.md`
- `sdlc/DEFINITION_OF_READY.md`

AI-generated output that violates these documents is rejected.

---

## Change Control

Any change to product behavior, architecture, or process must update the relevant documentation.
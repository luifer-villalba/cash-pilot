# WORKFLOW — CashPilot

## Purpose

Define **how work is done** in CashPilot: branching, commits, PRs, reviews, and AI usage. This workflow exists to keep changes **small, auditable, and aligned with the SDLC**.

---

## UI / Design Constraints

- Server-rendered templates only
- No client-side state ownership
- Favor clarity over density
- Avoid animations or transitions that affect usability

## Branching Strategy

### Main Branch

* `main` is always deployable
* No direct commits allowed

### Working Branches

Format:

```
<type>/<short-description>
```

Examples:

* `docs/sdlc-foundation`
* `feat/weekly-report-pdf`
* `fix/session-timezone-bug`

---

## Commit Discipline

### Commit Rules

* One logical change per commit
* No mixed concerns (docs + code + refactor)
* Commit messages must be clear and scoped

Format:

```
<type>: <short description>
```

Examples:

* `docs: add product acceptance criteria`
* `feat: add weekly trend PDF export`
* `fix: prevent numeric overflow in reconciliation`

---

## Pull Request Rules

### PR Size

* PRs must be **small and reviewable**
* Large changes are split into multiple PRs

### PR Requirements

Every PR must:

* Reference acceptance criteria
* Respect Definition of Ready
* Include or update tests (if behavior changes)
* Avoid unrelated refactors

---

## Review Checklist

Before approval, reviewers verify:

* Acceptance criteria satisfied
* RBAC enforced server-side
* No data model violations
* No regression in legacy compatibility
* Tests updated or added

---

## AI Usage Policy

### Allowed

* Use AI to propose code **after** requirements are clear
* Use AI to generate tests based on acceptance criteria
* Use AI to refactor within documented architecture

### Not Allowed

* AI inventing features or roles
* AI bypassing RBAC or validations
* AI introducing new architecture patterns

AI output is treated as **untrusted code** and must pass the same review.

---

## Change Control

* Changes to this workflow require documentation updates
* Deviations must be justified and temporary
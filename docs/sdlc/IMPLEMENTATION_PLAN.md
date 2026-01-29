# IMPLEMENTATION_PLAN — CashPilot

## Purpose

Define **how approved work is executed** in CashPilot. This plan converts a ready idea into **small, deliberate PRs** that can be reviewed, tested, and rolled back safely.

This document is **authoritative** for execution discipline.

---

## When This Plan Is Required

An implementation plan is required when:

* Adding or changing user-facing behavior
* Touching RBAC, reporting, or data model
* Introducing migrations
* Making changes larger than a trivial fix

---

## Inputs (Must Exist)

Before creating an implementation plan:

* Product intent is clear (`PRODUCT_VISION.md`)
* Requirements are defined (`REQUIREMENTS.md`)
* Acceptance criteria exist (`ACCEPTANCE_CRITERIA.md`)
* Definition of Ready is satisfied (`DEFINITION_OF_READY.md`)

---

## Planning Template

### Goal

* Short description of the outcome (not the solution)

### Acceptance Criteria

* List relevant AC-* identifiers

### Scope

**In scope**

* Explicit list

**Out of scope**

* Explicit list

---

## PR Breakdown (Mandatory)

### PR 1 — Foundation / Wiring

**Purpose**

* Prepare structure or plumbing

**Changes**

* Files/modules touched

**Risks**

* Low / Medium / High

**Tests**

* What will be validated

---

### PR 2 — Core Behavior

**Purpose**

* Implement main behavior

**Changes**

* Files/modules touched

**Risks**

* Low / Medium / High

**Tests**

* What will be validated

---

### PR 3 — UI / Reporting / Polish (Optional)

**Purpose**

* User-facing adjustments or exports

**Changes**

* Templates / static assets

**Risks**

* Low / Medium / High

**Tests**

* What will be validated

---

## Migration Strategy (If Applicable)

* Migration required? Yes / No
* Forward migration summary
* Backward/rollback strategy

---

## Test Strategy Summary

* New tests to add
* Existing tests to update
* Manual checks (if any)

---

## Rollback Plan

* How to disable or revert safely
* Data considerations

---

## Completion Checklist

Work is complete when:

* All PRs merged
* Acceptance criteria pass
* Tests are green
* No legacy compatibility regression
* Documentation updated if needed

---

## Change Control

Any deviation from this plan must:

* Be documented
* Be explicitly approved
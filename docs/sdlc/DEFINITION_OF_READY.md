# DEFINITION_OF_READY (DoR) — CashPilot

## Purpose

Define the **minimum conditions** a task, ticket, or PR must satisfy **before implementation begins**. This gate exists to prevent unclear scope, feature creep, and AI-driven overreach.

No work starts unless the DoR is met.

---

## Scope of Application

This DoR applies to:

* Feature work
* Bug fixes that affect behavior
* Refactors touching business logic, RBAC, reporting, or data model

Pure documentation or formatting-only changes may bypass some items.

---

## Required Inputs (All Must Be Present)

### 1. Problem Statement

* What problem is being solved?
* Why does it matter now?
* Which user role is affected (Admin or Cashier)?

### 2. Acceptance Criteria

* One or more acceptance criteria exist in `docs/product/ACCEPTANCE_CRITERIA.md`
* Criteria are observable and testable

### 3. Scope Definition

* What is **in scope** for this change
* What is **explicitly out of scope**
* Expected impact on UI, API, and data

### 4. RBAC Impact

* Which roles can access the new or changed behavior
* Confirmation that backend enforcement is required

### 5. Data Model Impact

* Does this change affect existing entities or relationships?
* If yes:

  * DATA_MODEL.md reviewed
  * Migration strategy identified

### 6. Reporting Impact

* Does this affect any report totals or filters?
* If yes, expected changes are described

### 7. Legacy Compatibility Check

* Confirm no reliance on modern JS APIs
* Confirm Windows 7 compatibility remains intact

---

## Implementation Planning

### 8. PR Breakdown

* Work is broken into **small, reviewable PRs**
* Each PR has a clear goal and deliverables

### 9. Test Strategy

* What tests will prove this works?
* Which existing tests may need updates?

### 10. Risk & Rollback

* Identify potential risks (data integrity, RBAC leakage, reporting accuracy)
* Define rollback or mitigation strategy

---

## Explicit NOT READY Conditions

A task is **NOT READY** if:

* Acceptance criteria are missing or vague
* RBAC rules are implied but not stated
* Data model changes are unclear
* Reporting impact is unknown
* The change requires a large, single PR

---

## Authority & Enforcement

* This DoR is **mandatory** for all implementation work
* Violations block PR approval
* AI-generated code must comply with this checklist

---

## Change Control

Changes to this DoR require:

* Explicit discussion
* Update to this document
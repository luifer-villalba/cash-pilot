# RELEASE_CHECKLIST — CashPilot

## Purpose

Provide a **safe, repeatable release process** for CashPilot. This checklist ensures releases do not compromise data integrity, RBAC, reporting accuracy, or legacy compatibility.

This checklist is **mandatory** for any deployment affecting behavior.

---

## Pre-Release

### Scope & Readiness

* Change satisfies Definition of Ready
* Acceptance criteria validated
* PRs are small and reviewed

### Tests

* All tests passing locally
* Critical paths manually verified if needed

### Data & Migrations

* Migration required? Yes / No
* Migration reviewed and tested locally
* Rollback strategy defined

### Security & RBAC

* RBAC paths reviewed
* No cross-business access introduced

### Legacy Compatibility

* UI verified on Windows 7 (or equivalent constraints)
* No modern JS APIs introduced

---

## Deployment

* Application builds successfully
* Environment variables verified
* Database migrations applied (if any)
* Application starts without errors

---

## Smoke Tests (Post-Deploy)

* Login works
* Admin dashboard loads
* Cashier can open and close a session
* Reports load and totals are correct
* Weekly PDF export renders (if applicable)

---

## Post-Release

* Logs checked for errors
* No unexpected RBAC denials
* Reports validated against known data

---

## Rollback

* Rollback steps documented
* Data impact assessed
* Team notified if rollback executed

---

## Release Sign-off

* Release approved by responsible owner
* Date/time recorded

---

## Change Control

Any modification to this checklist requires documentation updates.
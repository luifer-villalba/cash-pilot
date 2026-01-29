# ACCEPTANCE_CRITERIA — CashPilot

## Purpose

Define **verifiable conditions** that determine when a feature is complete and correct. These criteria are **authoritative** for testing, PR reviews, and release decisions.

Each criterion must be:

* Observable
* Testable
* Role-aware (RBAC)

---

## AC-01 Authentication & Access

**Given** a registered user

* When the user logs in with valid credentials
* Then a session is created and persisted

**Given** a user without assignment to a business

* When they attempt to access business data
* Then access is denied

---

## AC-02 RBAC Enforcement

### Admin

* Can access all businesses
* Can view reports
* Can view audit information
* Can manage users and assignments
* Can flag cash sessions and remove the flag

### Cashier

* Can only access assigned businesses
* Cannot access admin pages or reports
* Can open and close sessions
* Can see flags and comments

---

## AC-03 Cash Session Lifecycle

**Opening a Session**

* Given a Cashier with access to a business
* When they open a session
* Then the session is marked as open with timestamp and cashier identity

**Closing a Session**

* Given an open session
* When the Cashier enters reconciliation values and closes the session
* Then the session is closed, totals are stored, and validations are applied

---

## AC-04 Validation & Error Handling

* Invalid numeric values are rejected with user-friendly errors
* Overflows or unsafe values are prevented
* Validation errors do not persist partial data

---

## AC-05 Editing Rules

* Open sessions can be edited by the Cashier
* Closed sessions cannot be edited by Cashiers
* Any allowed edit is audit-logged

---

## AC-06 Reporting (Admin Only)

* Admin can view daily, weekly, and monthly reports
* Reports respect business and date filters
* Weekly trend report can be exported as PDF

---

## AC-07 Audit Trail

* All critical actions record: user, action, timestamp
* Audit data is immutable
* Soft-deleted records remain visible to Admins

---

## AC-08 Legacy Compatibility

* Core workflows function on Windows 7
* No critical functionality requires modern JS APIs

---

## Definition of Done

A feature is DONE when:

* All applicable acceptance criteria pass
* RBAC is enforced on backend
* Tests cover the criteria
* No regression in legacy compatibility
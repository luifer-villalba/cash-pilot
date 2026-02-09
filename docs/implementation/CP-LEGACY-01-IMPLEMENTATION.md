# IMPLEMENTATION_PLAN — CP-LEGACY-01

## Remove ES6 From Base Template

---

## Goal

Ensure `templates/base.html` contains no ES6 syntax so the app renders and runs on IE11/Windows 7 without script parse failures.

---

## Acceptance Criteria

* AC-08 (Legacy compatibility): base template scripts parse and run on IE11
* No runtime behavior regressions in modern browsers
* No ES6 syntax remains in `templates/base.html` inline scripts

---

## Scope

### In Scope

* Replace ES6 syntax in `templates/base.html` inline scripts
  * `const` -> `var`
  * Arrow functions -> function expressions
* Verify locale detection and theme initialization remain identical
* Manual legacy smoke check steps documented

### Out of Scope

* Rewriting external JS files (tracked by CP-LEGACY-02)
* Adding new polyfills beyond existing set
* Visual design changes

---

## PR Breakdown

### PR 1 — ES6 Removal In Base Template

**Purpose:** Eliminate ES6 syntax in inline scripts without behavior changes

**Changes**

* Update `templates/base.html` inline scripts
  * Replace arrow function in click handler with function expression
  * Replace `const` with `var`
  * Ensure no other ES6 syntax remains
* Keep existing polyfills and logic intact

**Risks:** Low

**Tests**

* Manual: load key pages (dashboard, businesses, reports, login) in a modern browser
* Manual: open app in IE11 (or IE11 emulation) and verify page load without script errors

---

### PR 2 — Legacy Verification Notes

**Purpose:** Document verification steps for AC-08

**Changes**

* Add a short section to legacy test notes (new file if needed under `docs/implementation/`)
  * IE11/Windows 7 verification checklist for base template scripts

**Risks:** Low

**Tests**

* Verify documentation is accurate and matches actual checks

---

## Migration Strategy

* Migration required? No

---

## Test Strategy Summary

* New tests to add: None (manual legacy verification required)
* Existing tests to update: None
* Manual checks:
  * Load `/`, `/businesses`, `/reports`, `/login` and confirm no JS console errors
  * Toggle theme and confirm persistence after reload
  * Use back button link behavior (data-back) in IE11

---

## Rollback Plan

* Revert PR 1 if any legacy regression is found
* Remove documentation changes from PR 2 if incorrect

---

## Completion Checklist

Work is complete when:

* All PRs merged
* AC-08 satisfied for base template scripts
* No legacy compatibility regression
* Documentation updated if needed

---

## Change Control

Any deviation from this plan must:

* Be documented
* Be explicitly approved

---

## Ticket Status Updates

When work is completed, update the corresponding backlog item status
in `docs/implementation/IMPROVEMENT_BACKLOG.md` with the completion date.

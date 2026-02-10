# IMPLEMENTATION_PLAN — CP-LEGACY-02

## Replace Unsupported DOM APIs

---

## Goal

Replace unsupported DOM API calls in JavaScript files to ensure compatibility with IE11/Windows 7.

---

## Acceptance Criteria

* AC-08 (Legacy compatibility): All JavaScript files use only IE11-compatible DOM APIs
* No runtime behavior regressions in modern browsers
* Dashboard filters, session forms, and navigation work in IE11

---

## Scope

### In Scope

* **Add NodeList.forEach polyfill** to `templates/base.html`
* **Replace `classList.toggle(className, force)`** with IE11-compatible conditional logic:
  * `dashboard.js` — 4 instances
* Verify all external JavaScript files use compatible APIs

### Out of Scope

* Polyfills already in base.html (String.padStart, Array.from, etc.) — these are complete
* Visual design changes
* Rewriting base.html inline scripts (covered by CP-LEGACY-01)
* Adding polyfills for APIs not currently used in codebase

---

## Problem Analysis

### Issue 1: classList.toggle(className, force) Not Supported

**Evidence:**
* `static/js/dashboard.js` lines 67-68, 127-128
* IE11 only supports `classList.toggle(className)` (single argument)
* The two-argument form (force parameter) is not supported

**Impact:**
* Dashboard filter badges and clear buttons don't work properly in IE11
* Filter toggle chevron rotation may fail

**Solution:**
Replace `element.classList.toggle('class', condition)` with:
```javascript
if (condition) {
    element.classList.add('class');
} else {
    element.classList.remove('class');
}
```

### Issue 2: NodeList.forEach Not Natively Supported

**Evidence:**
* `static/js/dashboard.js` uses `querySelectorAll().forEach()` (lines 62, 88, 124)
* `static/js/edit-session.js` uses `querySelectorAll().forEach()` (line 84)
* IE11 does not natively support `NodeList.prototype.forEach`

**Impact:**
* Dashboard filter initialization fails
* Session edit form enhancements may not work

**Solution:**
Add `NodeList.prototype.forEach` polyfill to `templates/base.html`

---

## PR Breakdown

### PR 1 — Add NodeList.forEach Polyfill

**Purpose:** Enable `querySelectorAll().forEach()` to work in IE11

**Changes:**

* Update `templates/base.html`
  * Add `NodeList.prototype.forEach` polyfill after existing Array polyfills (around line 165)
  * Add `HTMLCollection.prototype.forEach` polyfill for completeness

**Implementation:**
```javascript
// NodeList.forEach polyfill for IE11
if (window.NodeList && !NodeList.prototype.forEach) {
    NodeList.prototype.forEach = Array.prototype.forEach;
}

// HTMLCollection.forEach polyfill for IE11
if (window.HTMLCollection && !HTMLCollection.prototype.forEach) {
    HTMLCollection.prototype.forEach = Array.prototype.forEach;
}
```

**Risks:** Low (well-established polyfill pattern)

**Tests:**
* Manual: Load dashboard in IE11 and verify filters initialize without console errors
* Manual: Check that filter preset buttons work
* Manual: Verify edit session form loads properly

---

### PR 2 — Replace classList.toggle(force) in dashboard.js

**Purpose:** Replace unsupported two-argument classList.toggle with IE11-compatible code

**Changes:**

* Update `static/js/dashboard.js`
  * Replace lines 67-68 (clear button visibility):
    ```javascript
    // Before:
    btn.classList.toggle('opacity-0', !input.value);
    btn.classList.toggle('pointer-events-none', !input.value);
    
    // After:
    if (!input.value) {
        btn.classList.add('opacity-0', 'pointer-events-none');
    } else {
        btn.classList.remove('opacity-0', 'pointer-events-none');
    }
    ```
  * Replace lines 127-128 (date preset clear button visibility) - same pattern

**Risks:** Low (straightforward replacement, logic unchanged)

**Tests:**
* Manual: Test filter clear buttons show/hide correctly
* Manual: Verify date preset buttons update clear button visibility
* Manual: Confirm no console errors in IE11

---

### PR 3 — Legacy Verification Documentation

**Purpose:** Document IE11 verification steps for CP-LEGACY-02

**Changes:**

* Create or update `docs/implementation/CP-LEGACY-02-VERIFICATION.md`
  * IE11/Windows 7 verification checklist
  * List of all fixed API incompatibilities
  * Expected behavior before and after fixes

**Risks:** Low

**Tests:**
* Documentation review only

---

## Migration Strategy

* Migration required? No
* Database changes? No

---

## Test Strategy Summary

* **New tests to add:** None (IE11 testing requires manual verification)
* **Existing tests to update:** None (behavioral changes are zero)
* **Manual checks:**
  * Dashboard loads without JS errors in IE11
  * Filter form collapse/expand works
  * Clear filter buttons appear/disappear correctly
  * Date preset buttons work (today, yesterday, week, month)
  * Edit session form loads and validation works

---

## Rollback Plan

* Revert PR 1 if polyfill causes issues in any browser
* Revert PR 2 if filter buttons behave incorrectly
* Each PR is independent and can be reverted separately

---

## Implementation Sequence

1. **PR 1** (polyfill) — Foundational, must go first
2. **PR 2** (classList.toggle fixes) — Can proceed after PR 1 merged
3. **PR 3** (documentation) — Can be done in parallel with PR 2

---

## Completion Checklist

Work is complete when:

* ✅ All PRs merged
* ✅ AC-08 satisfied for all external JavaScript files
* ✅ Dashboard filters work in IE11
* ✅ No legacy compatibility regression
* ✅ Verification documentation complete

---

## Change Control

Any deviation from this plan must:

* Be documented in a PR comment
* Be explicitly approved in PR review

**Approved Changes:**
* None yet

---

## Ticket Status Update

When work is completed, update:

**File:** `docs/implementation/IMPROVEMENT_BACKLOG.md`

**Change:**
```markdown
### CP-LEGACY-02 — Replace unsupported DOM APIs

* **Status:** Completed (YYYY-MM-DD)
```

---

## Implementation Notes

### Why This Approach?

1. **Polyfill first** — Ensures forEach works before other code depends on it
2. **Minimal code changes** — Replace only incompatible API calls, preserve all logic
3. **No behavioral changes** — Users should see zero difference in any browser
4. **Progressive enhancement** — Modern browsers continue using native implementations

### Known Limitations

* IE11 will use polyfilled forEach (slightly slower than native)
* Conditional classList operations are more verbose but functionally identical
* Manual testing required for IE11 (automated testing on legacy browsers is complex)

### Future Improvements

* Consider automated IE11 testing via BrowserStack or similar service
* Add linting rules to catch unsupported API usage during development
* Create a legacy compatibility guide for developers

---

## Files Modified

### templates/base.html
* Add NodeList.forEach polyfill
* Add HTMLCollection.forEach polyfill

### static/js/dashboard.js  
* Replace 4×`classList.toggle(className, force)` with conditional logic

### docs/implementation/CP-LEGACY-02-VERIFICATION.md (new)
* Legacy testing checklist and API compatibility notes

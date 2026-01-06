# Windows 7 Compatibility Standards

## Overview

CashPilot maintains compatibility with Windows 7 browsers to support businesses using legacy hardware. This document outlines the compatibility requirements, implementation patterns, and testing procedures.

**Target Browsers:**
- Internet Explorer 11 (IE11)
- Chrome 50+ (last version supporting Windows 7)
- Firefox 45+ (last version supporting Windows 7)
- Edge Legacy (Windows 7 compatible)

**Last Verified:** 2025-01-29  
**Status:** Active maintenance

---

## Why We Support Windows 7

Many small businesses in Paraguay and similar markets still use Windows 7 machines. These systems are:
- Cost-effective for cash register terminals
- Sufficient for basic business operations
- Not easily replaceable due to budget constraints

Supporting Windows 7 ensures CashPilot remains accessible to all potential users.

---

## CSS Guidelines

### Always Use: Fallback Patterns

#### 1. CSS Variables with Fallbacks
**Pattern:** Always provide fallback values when using CSS variables.

```css
/* ✅ CORRECT */
color: var(--color-base-content, #1f2937); /* Fallback to dark gray */

/* ❌ WRONG */
color: var(--color-base-content);
```

**Implementation:** See `static/css/input.css` lines 34-91 for complete fallback patterns.

#### 2. Feature Detection with @supports
**Pattern:** Use `@supports` to provide fallbacks for unsupported features.

```css
/* Fallback for backdrop-blur */
@supports not (backdrop-filter: blur(1px)) {
  .backdrop-blur-sm {
    background-color: rgba(255, 255, 255, 0.95) !important;
    backdrop-filter: none !important;
  }
}

/* Fallback for CSS variables */
@supports not (color: var(--test-var, red)) {
  .btn-primary {
    background-color: #3b82f6 !important; /* Blue-500 fallback */
  }
}
```

**Implementation:** See `static/css/input.css` lines 18-92.

#### 3. Placeholder Styling for IE11
**Pattern:** IE11 requires special placeholder selectors.

```css
/* Modern browsers */
input::placeholder {
  color: var(--color-base-content, #1f2937);
  opacity: 0.5;
}

/* IE11 fallback */
input:-ms-input-placeholder {
  color: rgba(31, 41, 55, 0.5); /* Direct rgba - IE11 doesn't support CSS variables or opacity on placeholder */
}
```

**Implementation:** See `static/css/input.css` lines 94-116.

### Never Use: Incompatible CSS Features

**Forbidden Features:**
- ❌ CSS Grid (use Flexbox with fallbacks)
- ❌ CSS Custom Properties without fallbacks
- ❌ `backdrop-filter` without solid background fallback
- ❌ `color-mix()` function (disabled in PostCSS config)
- ❌ Logical properties (`margin-inline`, etc.) - disabled in PostCSS config
- ❌ `:is()` pseudo-class - disabled in PostCSS config

**Allowed with Fallbacks:**
- ✅ Flexbox (well-supported in IE11 with autoprefixer)
- ✅ CSS Variables (with hardcoded fallbacks)
- ✅ Modern selectors (PostCSS handles transpilation)

---

## JavaScript Best Practices

### Required Polyfills

All polyfills are included inline in `templates/base.html` (lines 31-475) to avoid external dependencies.

#### 1. String.padStart / String.padEnd
**Why:** IE11 doesn't support these methods.

**Implementation:**
```javascript
if (!String.prototype.padStart) {
    String.prototype.padStart = function(targetLength, padString) {
        // Custom implementation that doesn't use String.repeat()
        // (String.repeat() is also not supported in IE11)
    };
}
```

**Location:** `templates/base.html` lines 36-83

#### 2. Array.includes
**Why:** IE11 doesn't support `Array.prototype.includes()`.

**Implementation:**
```javascript
if (!Array.prototype.includes) {
    Array.prototype.includes = function(searchElement, fromIndex) {
        // Custom implementation with sameValueZero comparison
    };
}
```

**Location:** `templates/base.html` lines 84-107

#### 3. Array.from
**Why:** IE11 doesn't support `Array.from()` for converting array-like objects.

**Implementation:**
```javascript
if (!Array.from) {
    Array.from = function(arrayLike, mapFn, thisArg) {
        // Custom implementation with map function support
    };
}
```

**Location:** `templates/base.html` lines 109-143

#### 4. Set
**Why:** IE11 doesn't support the `Set` data structure.

**Implementation:**
```javascript
if (typeof Set === 'undefined') {
    window.Set = function(iterable) {
        this._values = [];
        // Basic implementation with add, has, delete, clear, forEach
    };
}
```

**Location:** `templates/base.html` lines 145-184

#### 5. URLSearchParams
**Why:** IE11 doesn't support `URLSearchParams` for parsing query strings.

**Implementation:**
```javascript
if (typeof URLSearchParams === 'undefined') {
    window.URLSearchParams = function(search) {
        this._params = {};
        // Full implementation with append, get, getAll, has, set, delete, toString
    };
}
```

**Location:** `templates/base.html` lines 186-264

#### 6. Promise
**Why:** IE11 doesn't support native Promises.

**Implementation:**
```javascript
if (typeof Promise === 'undefined') {
    window.Promise = function(executor) {
        // Basic Promise implementation with then, catch, resolve, reject
    };
}
```

**Location:** `templates/base.html` lines 266-348

#### 7. fetch
**Why:** IE11 doesn't support the Fetch API.

**Implementation:**
```javascript
if (typeof fetch === 'undefined') {
    window.fetch = function(url, options) {
        // XMLHttpRequest-based implementation
        // Returns Promise with response object (ok, status, text(), json())
    };
}
```

**Location:** `templates/base.html` lines 350-414

#### 8. Intl.NumberFormat
**Why:** IE11 has limited `Intl.NumberFormat` support.

**Implementation:**
```javascript
if (typeof Intl === 'undefined' || !Intl.NumberFormat) {
    window.Intl.NumberFormat = function(locale, options) {
        // Basic implementation with locale-aware number formatting
        // Supports Spanish (es) locale for Guaraníes formatting
    };
}
```

**Location:** `templates/base.html` lines 416-455

#### 9. CSS Variables Detection
**Why:** IE11 doesn't support CSS custom properties.

**Implementation:**
```javascript
var supportsCSSVars = window.CSS && CSS.supports && CSS.supports('color', 'var(--test-var, red)');
if (!supportsCSSVars) {
    // Inject inline styles for critical elements
    var style = document.createElement('style');
    style.textContent = [
        '.input-bordered:focus { border-color: #3b82f6 !important; }',
        '.btn-primary { background-color: #3b82f6 !important; }',
        // ... more fallback styles
    ].join('\n');
    document.head.appendChild(style);
}
```

**Location:** `templates/base.html` lines 457-473

### Feature Detection Pattern

**Always check for feature support before using:**

```javascript
// ✅ CORRECT - Feature detection
if (!String.prototype.padStart) {
    // Polyfill
}

// ❌ WRONG - Assumes feature exists
'abc'.padStart(5, '0');
```

### Forbidden JavaScript Features

**Never use without polyfills:**
- ❌ `async/await` (use Promise chains or transpile with Babel)
- ❌ Arrow functions in polyfills (use `function` declarations)
- ❌ `const`/`let` in polyfills (use `var` for IE11)
- ❌ Template literals in polyfills (use string concatenation)
- ❌ `String.repeat()` (not supported in IE11)
- ❌ `Array.find()`, `Array.findIndex()` (use `Array.filter()` or polyfill)
- ❌ `Object.assign()` (use manual property copying or polyfill)

**Allowed:**
- ✅ `var`, `function` declarations
- ✅ ES5 array methods (`forEach`, `map`, `filter`, `reduce`)
- ✅ `XMLHttpRequest` (for fetch polyfill)

---

## Build Configuration

### PostCSS Configuration

**File:** `postcss.config.js`

**Key Settings:**
```javascript
'postcss-preset-env': {
    browsers: [
        'IE >= 11',        // Windows 7 support
        'Chrome >= 50',     // Windows 7 support
        'Firefox >= 45',    // Windows 7 support
    ],
    features: {
        'color-mix': false,              // Disabled - not supported
        'logical-properties-and-values': false,  // Disabled
        'is-pseudo-class': false,        // Disabled
        'cascade-layers': false,         // Disabled
    },
},
autoprefixer: {
    overrideBrowserslist: [
        'IE >= 11',
        'Chrome >= 50',
        'Firefox >= 45',
    ],
},
```

**What This Does:**
- Autoprefixer adds vendor prefixes (`-webkit-`, `-moz-`, `-ms-`)
- PostCSS Preset Env transpiles modern CSS to compatible syntax
- Disables features that can't be polyfilled

---

## Testing Checklist

### Pre-Deployment Testing

- [ ] **Test on actual Windows 7 machine or VM**
  - IE11: Full functionality test
  - Chrome 109 (last Windows 7 version): Full functionality test
  - Firefox 115 (last Windows 7 version): Full functionality test

- [ ] **BrowserStack/CrossBrowserTesting verification**
  - Test key user flows:
    - Login/logout
    - Create cash session
    - Add expense/transfer items
    - Close session
    - View dashboard with filters
    - Edit session (within 12hr window)

- [ ] **Visual regression check**
  - Compare screenshots: Windows 11 (Chrome latest) vs Windows 7 (IE11/Chrome 109)
  - Verify colors, spacing, layout match (within acceptable differences)

- [ ] **JavaScript console check**
  - Open browser console on Windows 7
  - Verify no errors on page load
  - Test all interactive features
  - Check for polyfill warnings

### Automated Testing

**Current Status:** Manual testing only. Consider adding:
- BrowserStack automation
- Visual regression testing (Percy, Chromatic)
- JavaScript feature detection tests

---

## Common Issues & Fixes

### Issue 1: CSS Variables Not Working in IE11

**Symptom:** Buttons, inputs, and text appear unstyled or with wrong colors.

**Solution:**
1. Ensure all CSS variables have fallback values: `var(--color-primary, #3b82f6)`
2. Add `@supports not (color: var(--test-var, red))` blocks with hardcoded colors
3. JavaScript detection injects inline styles (see `templates/base.html` lines 457-473)

**Reference:** `static/css/input.css` lines 34-91

---

### Issue 2: String.padStart() Throws Error

**Symptom:** JavaScript error: "padStart is not a function"

**Solution:**
- Polyfill included in `templates/base.html` lines 36-58
- Polyfill doesn't use `String.repeat()` (also not supported in IE11)

**Reference:** `templates/base.html` lines 34-83

---

### Issue 3: fetch() Not Available

**Symptom:** JavaScript error: "fetch is not defined"

**Solution:**
- Polyfill included in `templates/base.html` lines 350-414
- Uses `XMLHttpRequest` under the hood
- Returns Promise-compatible response object

**Reference:** `templates/base.html` lines 350-414

---

### Issue 4: Placeholder Text Not Visible

**Symptom:** Input placeholders are invisible or wrong color in IE11.

**Solution:**
- Use `:-ms-input-placeholder` selector with direct `rgba()` color
- IE11 doesn't support CSS variables or `opacity` on placeholder pseudo-element

**Reference:** `static/css/input.css` lines 111-116

---

### Issue 5: Backdrop Blur Not Working

**Symptom:** Modal/overlay backgrounds are transparent instead of blurred.

**Solution:**
- Use `@supports not (backdrop-filter: blur(1px))` to provide solid background fallback
- Fallback: `background-color: rgba(255, 255, 255, 0.95)`

**Reference:** `static/css/input.css` lines 19-25

---

## References

### Code Locations

- **Polyfills:** `templates/base.html` lines 31-475
- **CSS Fallbacks:** `static/css/input.css` lines 14-116
- **Build Config:** `postcss.config.js`
- **Package Config:** `package.json`

### External Resources

- [Can I Use - IE11 Support](https://caniuse.com/?feats=flexbox,css-variables,es6-class&browsers=ie%3E%3D11)
- [MDN - Browser Compatibility](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference)
- [PostCSS Preset Env](https://github.com/csstools/postcss-preset-env)
- [Autoprefixer](https://github.com/postcss/autoprefixer)

### Related Documentation

- [Design System Guide](design_readme.md) - UI patterns and component guidelines
- [Main README](../README.md) - Project overview and setup

---

## Maintenance Notes

**When to Update This Guide:**
- After adding new CSS features (check IE11 compatibility)
- After adding new JavaScript features (check if polyfill needed)
- After dependency updates (verify browser support)
- After visual design changes (test on Windows 7)

**Last Updated:** 2025-01-29  
**Maintained By:** Development Team  
**Review Frequency:** Quarterly or when compatibility issues reported


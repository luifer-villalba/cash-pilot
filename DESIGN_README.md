# 🎨 CashPilot Design System

Design standards for CashPilot templates. If you're building new pages or adapting old ones, follow this playbook.

---

## Core Principle

**Clarity over beauty.** Pharmacy managers need to scan data instantly, spot discrepancies at a glance, and take action. No cute animations. No hidden information.

---

## Color System

We use 6 semantic colors + DaisyUI defaults:

| Color | Usage | Example |
|-------|-------|---------|
| **Primary (Blue)** | CTAs, active states, highlights | "Open Caja" button, selected filters |
| **Success (Green)** | Balanced reconciliation, completed | ✓ Closed sessions, matched cash |
| **Warning (Amber)** | Flagged sessions, needs review | ⚠️ Discrepancy detected, pending |
| **Error (Red)** | Missing funds, shortages, failures | ❌ Short 50,000₲, session unbalanced |
| **Info (Teal)** | Neutral info, reference data | 🔵 Session opened 08:00, cashier changed |
| **Neutral (Gray)** | Disabled, muted, metadata | Inactive accounts, past dates |

**Key rule:** Color means action. If it's red, something needs fixing.

---

## Typography

```
Headings:
  h1 → text-3xl font-bold               (Page titles)
  h2 → text-sm font-bold uppercase      (Section headers)
       tracking-widest text-base-content/70
  h3 → text-sm font-semibold            (Subsection labels)

Body:
  Regular text → text-sm text-base-content/70
  Labels → text-xs font-semibold uppercase tracking-wider
  Metadata → text-xs text-base-content/60
  Amounts → font-mono text-base font-bold
```

**Why monospace for numbers?** Merchants scan columns of digits. Fixed-width keeps alignment tight.

---

## Metric Cards (stats_row.html)

Metric cards show key numbers at a glance. Used on dashboard + session detail.

```html
<div class="bg-base-100 rounded-lg border border-primary/30 shadow-sm p-3 md:p-4">
  <p class="text-xs text-primary/70 uppercase tracking-wider font-semibold">
    {{ _('TOTAL SALES') }}
  </p>
  <p class="text-xl md:text-2xl font-bold mt-2 text-primary">
    {{ 2_500_000 | format_currency_py }}
  </p>
  <p class="text-xs text-base-content/60 mt-2">
    {{ _('Cash + Cards + Transfers') }}
  </p>
</div>
```

**Structure:**
1. **Colored border** — Indicates metric type (primary, success, warning, error)
2. **Label** — UPPERCASE, tiny, muted (tracking-wider = letter-spacing)
3. **big number** — Font size grows on desktop (text-xl → text-2xl)
4. **Helper text** — Small, gray, explains what the number includes

**Responsive:** 
- Mobile: `text-xl` (fits screen width)
- Desktop: `text-2xl` (more breathing room)

---

## Data Tables (sessions_table.html)

Tables display session lists. Keep them scannable.

```html
<table class="table table-sm w-full">
  <thead>
    <tr class="border-b border-base-300">
      <th class="text-left px-4 py-3 text-xs font-bold 
                  text-base-content/70 uppercase tracking-wider">
        Date
      </th>
    </tr>
  </thead>
  <tbody>
    <tr class="session-row hover:bg-primary/10 border-b">
      <td class="px-4 py-3 text-sm">01/02/2025</td>
    </tr>
  </tbody>
</table>
```

**Rules:**
- Hover tint: `hover:bg-primary/10` on normal rows, `hover:bg-error/14` on flagged
- Column headers: UPPERCASE, `tracking-wider`, muted gray
- Borders between columns: `border-right: 1px solid hsl(var(--bc) / 0.1)` (subtle)
- Row height: Comfortable tap targets (min 40px on mobile)
- Status badges as inline pills (success/warning/error)

**On flagged rows:**
```html
<tr class="session-row flagged border-l-4 border-error ...">
  <!-- Shows error color stripe on left -->
</tr>
```

---

## Session Detail Layout (session_detail.html)

Session detail pages have multiple sections. Organize with clear hierarchy:

```html
<!-- Hero Section (basic info) -->
<header class="bg-base-100 rounded-lg border shadow p-6 mb-6">
  <div class="flex justify-between items-start gap-4">
    <div>
      <h1 class="text-2xl font-bold">{{ session.session_date }}</h1>
      <p class="text-sm text-base-content/70 mt-2">{{ session.business.name }}</p>
    </div>
    <span class="badge badge-{{ status_class }}">{{ session.status }}</span>
  </div>
</header>

<!-- Content Sections -->
<section class="mb-8">
  <h2 class="text-sm font-bold uppercase tracking-widest text-base-content/70 mb-4 flex items-center gap-2">
    <svg>...</svg> {{ _('Payment Methods') }}
  </h2>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <!-- Metric cards go here -->
  </div>
</section>
```

**Section header pattern:**
```html
<h2 class="text-sm font-bold uppercase tracking-widest 
           text-base-content/70 mb-4 flex items-center gap-2">
  <svg class="w-4 h-4">...</svg>
  {{ _('Section Title') }}
</h2>
```

**Why the icon?** Breaks up walls of text. Icon + title = scannability.

---

## Filter Bar (index.html)

Dashboard filters live in a collapsible bar. Design for quick scanning + powerful filters.

```html
<!-- Quick Actions Row -->
<div class="flex justify-between items-center mb-4">
  <div class="flex gap-2">
    <button class="btn btn-sm btn-ghost">📅 Today</button>
    <button class="btn btn-sm btn-ghost">📅 This Week</button>
    <button class="btn btn-sm btn-ghost">📅 This Month</button>
  </div>
  <button id="filter-toggle" class="btn btn-sm btn-outline">
    ⚙️ More Options
  </button>
</div>

<!-- Collapsible Advanced Filters -->
<form id="filter-form" class="hidden grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 items-end pt-2">
  <input type="date" name="from_date" />
  <input type="date" name="to_date" />
  <input type="text" placeholder="Search..." />
  <select name="business_id">
    <option>All Businesses</option>
  </select>
  <button type="submit" class="btn btn-primary btn-sm">Apply</button>
</form>
```

**UX pattern:**
1. **Quick buttons** — 80% of users want "Today" or "This Month"
2. **Collapsible advanced** — Power users dig deeper, but don't clutter
3. **Live updates** — As user types/selects, update results (HTMX)
4. **Clear button** — Reset all filters at once

---

## Status Badges

Use DaisyUI badge utilities for consistency:

```html
<!-- Open Session -->
<span class="badge badge-warning gap-2">
  <svg class="w-4 h-4">...</svg> {{ _('Open') }}
</span>

<!-- Closed Session -->
<span class="badge badge-success gap-2">
  <svg class="w-4 h-4">...</svg> {{ _('Closed') }}
</span>

<!-- Flagged (Needs Review) -->
<span class="badge badge-error gap-2">
  <svg class="w-4 h-4">...</svg> {{ _('Review') }}
</span>
```

**Colors match intent:**
- `badge-warning` (amber) → Still open, action possible
- `badge-success` (green) → Complete, nothing to do
- `badge-error` (red) → Problem detected, needs attention

---

## Form Patterns

Forms should be simple and focused. One column on mobile, 2-3 on desktop.

```html
<form method="post">
  <div class="form-control mb-4">
    <label class="label">
      <span class="label-text font-semibold">{{ _('Business') }}</span>
    </label>
    <select name="business_id" class="select select-bordered" required>
      {% for biz in businesses %}
        <option value="{{ biz.id }}">{{ biz.name }}</option>
      {% endfor %}
    </select>
  </div>

  <div class="form-control mb-4">
    <label class="label">
      <span class="label-text font-semibold">{{ _('Initial Cash') }}</span>
      <span class="label-text-alt text-xs text-base-content/60">Gs</span>
    </label>
    <input type="number" name="initial_cash" class="input input-bordered" required />
  </div>

  <div class="flex gap-2">
    <button type="submit" class="btn btn-primary flex-1">{{ _('Create') }}</button>
    <a href="/" class="btn btn-ghost flex-1">{{ _('Cancel') }}</a>
  </div>
</form>
```

**Rules:**
- Label always above input
- Alt text (units, hints) in `label-text-alt`
- Full-width on mobile (100% → flex-1)
- Submit button is primary, cancel is ghost

---

## Empty States

When there's no data, don't leave the page blank. Show a helpful message.

```html
<div class="flex flex-col items-center justify-center py-12 px-4">
  <div class="text-6xl mb-4">📋</div>
  <h2 class="text-2xl font-bold mb-2">{{ _('No sessions found') }}</h2>
  <p class="text-gray-500 text-center mb-6 max-w-sm">
    {{ _('Adjust your filters or create a new session to get started.') }}
  </p>
  <a href="/sessions/create" class="btn btn-primary">
    {{ _('+ New Session') }}
  </a>
</div>
```

**Pattern:**
1. Large emoji (sets tone instantly)
2. Friendly headline (not "Error 404")
3. Explanation (what can they do?)
4. CTA button (next action)

---

## Loading States

Use skeleton loaders (not spinners). Spinners feel broken.

```html
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
  {% for i in range(5) %}
    <div class="bg-base-200 rounded-lg h-28 animate-pulse"></div>
  {% endfor %}
</div>
```

**Why?** Skeleton shows the layout filling in, not "something is loading."

---

## Icons

Use inline SVGs, not icon libraries. Keep them simple.

```html
<!-- Calendar -->
<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
</svg>

<!-- Checkmark -->
<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
  <path fill-rule="evenodd" 
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
</svg>
```

**Rules:**
- Size: `w-4 h-4` (16px) for inline, `w-6 h-6` (24px) for standalone
- Color: `text-current` (inherits parent text color) or explicit `text-primary`
- Stroke icons for outlines, filled for solid (consistency matters)

---

## Responsive Design

DaisyUI + Tailwind do most of the work. Stick to this pattern:

```html
<!-- Mobile-first -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
  <!-- 1 column mobile, 2 tablet, 3 desktop -->
</div>

<p class="text-sm md:text-base">
  <!-- Smaller font on mobile, grows on desktop -->
</p>

<div class="flex flex-col md:flex-row gap-4">
  <!-- Stack vertical on mobile, horizontal on desktop -->
</div>
```

**Breakpoints:**
- `sm:` ≥ 640px (tablet)
- `md:` ≥ 768px (landscape tablet)
- `lg:` ≥ 1024px (desktop)

**Never hardcode widths.** Use `flex-1`, `w-full`, grid columns.

---

## HTMX Integration

Use HTMX for dynamic updates without page reloads.

```html
<!-- Load stats on page load + filter change -->
<div id="stats-row"
     hx-get="/stats"
     hx-include="#filter-form"
     hx-trigger="load, #filter-form input changed delay:500ms"
     hx-swap="outerHTML">
  <!-- Skeleton loader here -->
</div>

<!-- Paginated table -->
<div id="sessions-table"
     hx-get="/sessions/table?page=1"
     hx-trigger="load"
     hx-swap="innerHTML">
  {% include "partials/sessions_table.html" %}
</div>
```

**Rules:**
- `hx-get` = URL to fetch
- `hx-include` = extra form data to send
- `hx-trigger` = what activates the request (load, click, changed)
- `hx-swap` = how to swap (innerHTML, outerHTML, beforeend)
- `delay:500ms` = debounce rapid input changes

---

## Accessibility (a11y)

These matter. No exceptions.

```html
<!-- Buttons have aria labels -->
<button aria-label="Open filter menu" class="btn">⚙️</button>

<!-- Form labels linked to inputs -->
<label for="email">Email</label>
<input id="email" type="email" />

<!-- Color + another indicator (not color alone) -->
<span class="badge badge-error">❌ Short</span>  <!-- ✓ Icon + color -->
<span style="color: red;">Short</span>          <!-- ✗ Color alone -->

<!-- Headings in semantic order (no skipping h1 → h3) -->
<h1>Session Detail</h1>
<h2>Payment Methods</h2>  <!-- ✓ h2, not h3 -->

<!-- Tables have headers -->
<table>
  <thead>
    <tr>
      <th scope="col">Date</th>
    </tr>
  </thead>
</table>
```

---

## Dark Mode

DaisyUI handles dark mode automatically. Use semantic colors, not hardcoded colors.

```html
<!-- ✓ Good (adapts to dark mode) -->
<div class="bg-base-100 text-base-content">

<!-- ✗ Bad (always white background) -->
<div class="bg-white text-black">
```

---

## Common Patterns

### Session Status Flow
```
OPEN (warning/amber) → CLOSED (success/green) → FLAGGED (error/red)
```

### Money Formatting
```jinja2
{{ amount | format_currency_py }}  <!-- ₲ 2.500.000 -->
```

### Date/Time Display
```jinja2
{{ session.session_date.strftime('%d/%m/%Y') }}  <!-- 01/02/2025 -->
{{ session.opened_time.strftime('%H:%M') }}      <!-- 08:30 -->
```

### Permission-Based UI
```html
{% if current_user.role == 'ADMIN' %}
  <a href="/businesses/new" class="btn btn-primary">{{ _('+ New Business') }}</a>
{% else %}
  <button disabled class="btn btn-primary opacity-40">{{ _('+ New Business') }}</button>
{% endif %}
```

---

## Checklist for New Templates

- [ ] Mobile-first responsive (test on 375px viewport)
- [ ] Color has semantic meaning (not just pretty)
- [ ] Heading hierarchy is correct (h1 → h2 → h3, no jumps)
- [ ] Forms have labels linked to inputs
- [ ] Empty state shown when no data
- [ ] Loading skeleton (not spinner)
- [ ] Status indicators use color + icon/text
- [ ] Numbers use monospace font
- [ ] ARIA labels on icon buttons
- [ ] Translation keys used (not hardcoded text)
- [ ] Works without JavaScript (HTMX is progressive enhancement)
- [ ] Tested on dark mode (if supported)

---

## Files to Reference

When building new pages, copy the structure from:
- **stats_row.html** — Metric cards (financial summary)
- **sessions_table.html** — Data tables + pagination
- **session_detail.html** — Multi-section detail page
- **index.html** — Dashboard layout with filters

These four files set the standard. Make new pages look like them.
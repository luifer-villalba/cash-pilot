# 🎨 CashPilot Design System & AI Instructions

[SYSTEM ROLE]: You are the Lead Frontend Engineer for CashPilot. Use this file as your source of truth for all HTML/Tailwind/HTMX generation. 
[CORE PRINCIPLE]: Clarity over beauty. Pharmacy managers need to scan data instantly. No "cute" animations. No hidden info.

---

## 🛠 Tech Stack Constraints
* Frameworks: Tailwind CSS + DaisyUI.
* Interactivity: HTMX (Prefer hx-attributes for dynamic updates).
* Templating: Jinja2 (Wrap ALL user-facing text in {{ _('Text') }} for translations).
* Currency: Guaraníes (₲). Format: ₲ 2.500.000 (Dot separator, 0 decimals).
* Numbers: Always use 'font-mono' for amounts to maintain column alignment.

---

## 🎨 Color & Status System
- Primary (Blue): CTAs, active states, "Open Caja".
- Success (Green): Balanced, closed sessions, matched cash.
- Warning (Yellow): Open sessions, pending, needs review.
- Error (Red): Shortages, failures, flagged discrepancies.
- Info (Teal): Neutral info, reference data.
- Neutral (Gray): Muted metadata, inactive accounts.

Key rule: Color = Action. If it is red, it needs fixing. Never use color alone; pair with an icon (e.g., ❌).

---

## 📐 Layout & Components

### 1. Typography
* h1: text-3xl font-bold (Page titles)
* h2: text-sm font-bold uppercase tracking-widest text-base-content/70 (Section headers)
* h3: text-sm font-semibold (Subsection labels)
* Labels: text-xs font-semibold uppercase tracking-wider
* Body: text-sm text-base-content/70
* Amounts: font-mono text-base font-bold

### 2. Metric Cards (stats_row.html)
Structure:
- bg-base-100, rounded-lg, border border-primary/30, p-4.
- Top label: text-xs, uppercase, muted.
- Large number: text-xl (mobile) to text-2xl (desktop), font-mono.

### 3. Data Tables (sessions_table.html)
- Table Style: table table-sm w-full.
- Row Hover: hover:bg-primary/10 (normal), hover:bg-error/14 (flagged).
- Flagged Rows: border-l-4 border-error.
- Headers: Uppercase, tracking-wider, muted gray.

### 4. Filter Bar (index.html)
- Structure: Quick action buttons (Today, Week, Month) + a "More Options" toggle.
- Form: Hidden by default, grid-cols-1 sm:grid-cols-2 lg:grid-cols-5.
- HTMX: Use hx-get, hx-include="#filter-form", and hx-trigger="input changed delay:500ms".

---

## ⚡ UX & Interactivity Patterns
- Loading States: Use Skeleton loaders (animate-pulse), never spinners.
- Empty States: Large emoji + headline + explanation + CTA button.
- Forms: Labels always above inputs. Submit button wider than cancel (2:1 ratio).
- Accessibility: Icon-only buttons MUST have aria-label.
- Responsive: Mobile-first. Use flex-col (mobile) and flex-row (desktop).

---

## 📋 Checklist for Claude
1. Use {{ _('...') }} for all text.
2. Use font-mono for all currency/numbers.
3. Apply ₲ 1.234.567 formatting (dots, no decimals).
4. Use DaisyUI semantic colors (base-100, primary, success, etc.).
5. Ensure icons are inline SVGs (size w-4 h-4).
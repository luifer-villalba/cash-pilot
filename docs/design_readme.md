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

## 📝 Modern Form Patterns

### Currency Input Fields
**Pattern:** All currency inputs must clearly indicate they're for currency and format automatically.

```html
<div class="relative">
    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-lg font-bold text-primary pointer-events-none z-10" aria-hidden="true">₲</span>
    <input
        type="text"
        name="amount"
        id="amount"
        class="input input-lg input-bordered w-full font-mono pl-10 text-lg focus:input-primary focus:ring-2 focus:ring-primary/20 transition-all"
        placeholder="1.250.000"
        inputmode="decimal"
        required
        data-currency-input
        autocomplete="off"
        aria-describedby="amount-help"
    />
</div>
<label class="label pt-2" id="amount-help">
    <span class="label-text-alt text-xs text-base-content/60">{{ _('Helper text') }}</span>
</label>
```

**Key Requirements:**
- Visible ₲ prefix (absolute positioned, `pointer-events-none`, `z-10`)
- `font-mono` class for number alignment
- `data-currency-input` attribute for JavaScript formatting
- `inputmode="decimal"` for mobile keyboards
- `autocomplete="off"` to prevent browser interference
- `aria-describedby` linking to helper text
- Focus ring: `focus:ring-2 focus:ring-primary/20`
- Smooth transitions: `transition-all`

### Form Section Structure
**Pattern:** Use numbered sections with visual hierarchy for complex forms.

```html
<!-- STEP 1: Primary Section (Most Important) -->
<div class="bg-gradient-to-br from-primary/5 to-base-100 border-2 border-primary/30 rounded-xl shadow-lg p-6 space-y-6 transition-all duration-200">
    <div class="flex items-center gap-3 pb-2 border-b border-primary/20">
        <div class="w-8 h-8 rounded-full bg-primary text-primary-content flex items-center justify-center font-bold text-sm shadow-sm" aria-hidden="true">1</div>
        <h2 class="text-lg font-bold text-base-content">{{ _('Section Title') }}</h2>
    </div>
    <!-- Form fields here -->
</div>

<!-- STEP 2: Secondary Section -->
<div class="bg-base-100 border-2 border-base-300 rounded-xl shadow-lg p-6 space-y-6 transition-all duration-200">
    <div class="flex items-center gap-3 pb-2 border-b border-base-300">
        <div class="w-8 h-8 rounded-full bg-info text-info-content flex items-center justify-center font-bold text-sm shadow-sm" aria-hidden="true">2</div>
        <h2 class="text-lg font-bold text-base-content">{{ _('Section Title') }}</h2>
    </div>
    <!-- Form fields here -->
</div>

<!-- STEP 3: Optional Section -->
<div class="bg-base-100 border border-base-300 rounded-xl shadow p-6 space-y-6 transition-all duration-200">
    <div class="flex items-center gap-3 pb-2 border-b border-base-300">
        <div class="w-8 h-8 rounded-full bg-base-300 text-base-content flex items-center justify-center font-bold text-sm shadow-sm" aria-hidden="true">3</div>
        <h2 class="text-lg font-bold text-base-content/70">{{ _('Optional Section') }}</h2>
    </div>
    <!-- Form fields here -->
</div>
```

**Visual Hierarchy:**
- Primary section: Gradient background (`from-primary/5 to-base-100`), thicker border (`border-2 border-primary/30`)
- Secondary section: Solid background, standard border (`border-2 border-base-300`)
- Optional section: Lighter styling (`border` not `border-2`), muted text (`text-base-content/70`)

### Action Buttons
**Pattern:** Submit button 2:1 ratio vs cancel, with loading states.

```html
<div class="flex gap-3 pt-4">
    <button 
        type="submit" 
        class="btn btn-error btn-lg flex-[2] gap-2 shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-error/50"
        aria-label="{{ _('Action description') }}"
    >
        <span class="loading loading-spinner loading-sm hidden" id="submit-loading"></span>
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <!-- Icon path -->
        </svg>
        <span>{{ _('Submit') }}</span>
    </button>
    <a 
        href="/cancel-url" 
        class="btn btn-outline btn-lg flex-1 transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-base-content/20"
        aria-label="{{ _('Cancel action') }}"
    >
        {{ _('Cancel') }}
    </a>
</div>
```

**JavaScript for loading state:**
```javascript
<form onsubmit="document.getElementById('submit-loading').classList.remove('hidden');">
```

---

## 🎯 Line Item Tables (Transfer Items, Expense Items, etc.)

### Add Form Pattern
**Pattern:** Card-based add form with gradient background and currency input.

```html
<div class="bg-gradient-to-br from-info/10 to-base-100 border border-info/30 rounded-lg p-4 space-y-3 transition-all duration-200">
    <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <!-- Icon -->
        </svg>
        <span class="text-xs font-bold uppercase tracking-wider text-info">{{ _('Add Item') }}</span>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <!-- Description -->
        <div class="md:col-span-2">
            <label for="item-description" class="sr-only">{{ _('Item description') }}</label>
            <input
                type="text"
                id="item-description"
                class="input input-bordered w-full focus:input-info focus:ring-2 focus:ring-info/20 transition-all"
                placeholder="{{ _('Description placeholder') }}"
                maxlength="100"
                autocomplete="off"
            />
        </div>
        <!-- Amount -->
        <div class="flex gap-2">
            <div class="relative flex-1">
                <label for="item-amount" class="sr-only">{{ _('Item amount') }}</label>
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-bold text-primary pointer-events-none z-10" aria-hidden="true">₲</span>
                <input
                    type="text"
                    id="item-amount"
                    class="input input-bordered w-full font-mono pl-8 focus:input-info focus:ring-2 focus:ring-info/20 transition-all"
                    placeholder="10.000"
                    inputmode="decimal"
                    data-currency-input
                    autocomplete="off"
                />
            </div>
            <button
                type="button"
                class="btn btn-primary gap-2 transition-all hover:scale-105 active:scale-95"
                hx-post="/endpoint"
                hx-target="#items-container"
                hx-swap="outerHTML"
                hx-indicator="#item-loading"
                hx-on::after-swap="document.getElementById('item-description')?.focus(); document.getElementById('item-description').value=''; document.getElementById('item-amount').value='';"
                aria-label="{{ _('Add item') }}"
            >
                <span class="loading loading-spinner loading-xs hidden" id="item-loading"></span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <!-- Icon -->
                </svg>
                <span>{{ _('Add') }}</span>
            </button>
        </div>
    </div>
    <p class="text-xs text-base-content/60 flex items-center gap-1">
        <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <!-- Info icon -->
        </svg>
        <span>{{ _('Helper text') }}</span>
    </p>
</div>
```

### Item List Pattern
**Pattern:** Card-based list with hover effects and delete buttons.

```html
<div class="space-y-2" role="list" aria-label="{{ _('Items list') }}">
    {% for item in items %}
    <div class="bg-base-100 border border-base-300 rounded-lg p-3 flex items-center justify-between hover:shadow-md hover:border-info/40 transition-all duration-200 group" role="listitem">
        <div class="flex-1 min-w-0 pr-3">
            <p class="text-sm font-medium text-base-content truncate" title="{{ item.description }}">{{ item.description }}</p>
            <p class="text-xs text-base-content/60 mt-0.5 flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <!-- Time icon -->
                </svg>
                <time datetime="{{ item.created_at.isoformat() if item.created_at else '' }}">{{ item.created_at.strftime('%H:%M') if item.created_at else '' }}</time>
            </p>
        </div>
        <div class="flex items-center gap-3 flex-shrink-0">
            <p class="text-base font-bold font-mono text-base-content tabular-nums">Gs {{ "{:,.0f}".format(item.amount) }}</p>
            {% if editable %}
            <button
                type="button"
                class="btn btn-ghost btn-sm btn-circle text-error hover:bg-error/20 focus:bg-error/20 focus:outline-none focus:ring-2 focus:ring-error/50 transition-all opacity-0 group-hover:opacity-100"
                aria-label="{{ _('Delete item') }}: {{ item.description }}"
                hx-delete="/endpoint/{{ item.id }}"
                hx-target="#items-container"
                hx-swap="outerHTML"
                hx-confirm="{{ _('Delete this item?') }}"
                hx-indicator="#item-delete-{{ item.id }}"
            >
                <span class="loading loading-spinner loading-xs hidden" id="item-delete-{{ item.id }}"></span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <!-- Delete icon -->
                </svg>
            </button>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
```

**Key Features:**
- `role="list"` and `role="listitem"` for accessibility
- `group` class for hover effects on child elements
- Delete buttons appear on hover (`opacity-0 group-hover:opacity-100`)
- Individual loading indicators per delete button
- `tabular-nums` for consistent number alignment
- Semantic `<time>` element with `datetime` attribute

### Total Card Pattern
**Pattern:** Summary card with gradient background and data attribute for JavaScript.

```html
<div class="bg-gradient-to-br from-info/5 to-base-100 border border-info/20 rounded-lg p-4 transition-all duration-200">
    <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-info flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <!-- Icon -->
            </svg>
            <span class="text-xs font-bold uppercase tracking-wider text-base-content/70">{{ _('Total Label') }}</span>
        </div>
        <p class="text-2xl font-bold font-mono text-base-content tabular-nums" data-total="{{ '{:.0f}'.format(total) if total else '0' }}" aria-label="{{ _('Total label') }}: Gs {{ '{:,.0f}'.format(total) if total else '0' }}">
            Gs {{ "{:,.0f}".format(total) if total else "0" }}
        </p>
    </div>
</div>
```

**Key Features:**
- `data-total` attribute for JavaScript access (numeric string, no formatting)
- `aria-label` with full description (use string concatenation, NOT keyword arguments)
- `tabular-nums` for consistent alignment
- Gradient background matching section theme

### Empty State Pattern
**Pattern:** Centered empty state with icon and message.

```html
<div class="bg-base-200/50 border border-dashed border-base-300 rounded-lg p-6 text-center transition-all duration-200">
    <svg class="w-8 h-8 mx-auto text-base-content/30 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <!-- Icon -->
    </svg>
    <p class="text-sm text-base-content/60 italic">{{ _('No items recorded') }}</p>
</div>
```

---

## ⚡ UX & Interactivity Patterns

### Loading States
**Pattern:** Use loading spinners for HTMX operations, not skeleton loaders.

```html
<!-- In button -->
<span class="loading loading-spinner loading-xs hidden" id="action-loading"></span>

<!-- HTMX attribute -->
hx-indicator="#action-loading"
```

**JavaScript to show on form submit:**
```javascript
<form onsubmit="document.getElementById('submit-loading').classList.remove('hidden');">
```

### HTMX Patterns
**Pattern:** Always include loading indicators and auto-focus after swap.

```html
<button
    hx-post="/endpoint"
    hx-target="#container"
    hx-swap="outerHTML"
    hx-indicator="#loading-id"
    hx-on::after-swap="document.getElementById('input-id')?.focus(); document.getElementById('input-id').value='';"
>
```

### Currency Formatting JavaScript
**Pattern:** Auto-format currency inputs on blur, allow only digits during input.

```javascript
document.querySelectorAll('[data-currency-input]').forEach(input => {
    input.addEventListener('blur', function() {
        if (this.value) {
            const digits = this.value.replace(/\D/g, '');
            if (digits) {
                const num = parseInt(digits);
                this.value = num.toLocaleString('es-PY').replace(/,/g, '.');
            }
        }
        updateReconciliationPreview(); // If applicable
    });

    input.addEventListener('input', function() {
        this.value = this.value.replace(/[^\d.,]/g, '');
        updateReconciliationPreview(); // If applicable
    });
});
```

### Live Reconciliation Sidebar
**Pattern:** Real-time calculation preview that updates as user types.

```html
<div class="bg-gradient-to-br from-success/10 to-base-100 border-2 border-success/30 rounded-xl p-5 space-y-4">
    <div class="flex items-center gap-2 pb-2 border-b border-success/20">
        <svg class="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <!-- Icon -->
        </svg>
        <h3 class="font-bold text-sm uppercase tracking-wider text-success">{{ _('Live Reconciliation') }}</h3>
    </div>
    <div class="space-y-4" id="preview">
        <!-- JavaScript populates this -->
    </div>
</div>
```

**JavaScript Pattern:**
```javascript
function updateReconciliationPreview() {
    // Parse values from form inputs
    // Calculate totals
    // Update preview HTML with formatted results
    // Show empty state if no data entered
}

// Watch for input changes
document.querySelectorAll('[name="field"]').forEach(input => {
    input.addEventListener('input', updateReconciliationPreview);
    input.addEventListener('blur', updateReconciliationPreview);
});

// Watch for HTMX updates
document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'items-container') {
        updateReconciliationPreview();
    }
});
```

---

## ♿ Accessibility Requirements

### Required Attributes
- **All inputs:** `id`, `name`, `aria-describedby` (if helper text exists)
- **All buttons:** `aria-label` (especially icon-only buttons)
- **Currency symbols:** `aria-hidden="true"` and `pointer-events-none`
- **Icons:** `aria-hidden="true"` when decorative
- **Lists:** `role="list"` and `role="listitem"`
- **Time elements:** `<time datetime="ISO8601">` with proper format

### Focus States
- All interactive elements must have visible focus rings
- Use `focus:ring-2 focus:ring-{color}/20` pattern
- Buttons: `focus:outline-none focus:ring-2 focus:ring-{color}/50`

### Screen Reader Support
- Use `sr-only` class for visually hidden labels
- Connect helper text with `aria-describedby`
- Use semantic HTML (`<time>`, `<nav>`, etc.)
- Never use keyword arguments in `_()` - use string concatenation:
  ```jinja
  {# ❌ WRONG #}
  {{ _('Label: %(value)s', value=amount) }}
  
  {# ✅ CORRECT #}
  {{ _('Label') }}: {{ amount }}
  ```

---

## 🎨 Visual Polish

### Transitions
- All interactive elements: `transition-all duration-200`
- Buttons: `hover:scale-[1.02] active:scale-[0.98]` for feedback
- Cards: `hover:shadow-md` and `hover:border-{color}/40`

### Spacing
- Form sections: `space-y-6` for vertical rhythm
- Item lists: `space-y-2` for tight grouping
- Cards: `p-4` to `p-6` depending on importance

### Typography
- Use `tabular-nums` on all numeric displays for alignment
- Currency amounts: `font-mono font-bold`
- Helper text: `text-xs text-base-content/60`

---

## 📋 Checklist for Implementation

### Form Structure
- [ ] Labels above inputs (`label` with `label-text`)
- [ ] Currency inputs have visible ₲ prefix
- [ ] All inputs have `id`, `name`, and `aria-describedby` if needed
- [ ] `data-currency-input` on all currency fields
- [ ] `autocomplete="off"` on currency inputs
- [ ] Submit button 2:1 ratio (`flex-[2]` vs `flex-1`)
- [ ] Loading spinner in submit button

### HTMX Operations
- [ ] `hx-indicator` pointing to loading spinner
- [ ] `hx-on::after-swap` for auto-focus and field clearing
- [ ] Individual loading indicators for delete buttons
- [ ] Proper `hx-target` and `hx-swap` attributes

### Accessibility
- [ ] All icon-only buttons have `aria-label`
- [ ] Currency symbols have `aria-hidden="true"`
- [ ] Decorative icons have `aria-hidden="true"`
- [ ] Lists use `role="list"` and `role="listitem"`
- [ ] Time elements use `<time datetime="">`
- [ ] No keyword arguments in `_()` translations

### Visual Polish
- [ ] Smooth transitions on interactive elements
- [ ] Hover effects on cards and buttons
- [ ] Focus rings on all inputs and buttons
- [ ] `tabular-nums` on numeric displays
- [ ] Proper z-index for currency symbols

### JavaScript
- [ ] Currency formatting on blur
- [ ] Input validation (digits only during typing)
- [ ] Live updates for reconciliation (if applicable)
- [ ] HTMX event listeners for dynamic updates

---

## 🚫 Common Mistakes to Avoid

1. **Translation errors:** Never use `_('Text: %(var)s', var=value)` - use concatenation
2. **Missing aria-labels:** All icon-only buttons MUST have `aria-label`
3. **No focus states:** All inputs and buttons need visible focus rings
4. **Hardcoded text:** All user-facing text must use `{{ _('...') }}`
5. **Missing currency prefix:** Currency inputs must show ₲ symbol
6. **No loading states:** HTMX operations must show loading indicators
7. **Poor mobile UX:** Use `inputmode="decimal"` for numeric inputs
8. **Accessibility gaps:** Use semantic HTML and proper ARIA attributes

---

## 📚 Reference Examples

See these files for complete implementations:
- `templates/sessions/close_session.html` - Complete form with sections
- `templates/partials/transfer_items_table.html` - Line item table pattern
- `templates/partials/expense_items_table.html` - Line item table pattern

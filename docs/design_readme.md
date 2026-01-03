# 🎨 CashPilot Design System & AI Instructions

[SYSTEM ROLE]: You are the Lead Frontend Engineer for CashPilot. Use this file as your source of truth for all HTML/Tailwind/HTMX generation. 
[CORE PRINCIPLE]: Clarity over beauty. Business managers need to scan data instantly. No "cute" animations. No hidden info.

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

## 📊 Report Pages & Data Visualization

Reports are a critical feature for business analytics. They follow specific UX/UI patterns to ensure clarity, ease of use, and actionability.

### Report Page Structure

**Pattern:** Consistent header + controls + content layout with clear visual hierarchy.

#### Header Section
All report pages start with a consistent header:

```html
<div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6">
    <div class="flex-1">
        <div class="flex items-center gap-3">
            <div class="p-2 bg-primary/10 rounded-lg">
                <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <!-- Report icon -->
                </svg>
            </div>
            <div>
                <h1 class="text-2xl md:text-3xl font-bold text-base-content">{{ _('Report Title') }}</h1>
                <p class="text-xs md:text-sm text-base-content/60 mt-0.5">{{ _('Brief description of report purpose') }}</p>
            </div>
        </div>
    </div>
    <a href="/reports" class="btn btn-outline btn-sm gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <!-- Back arrow icon -->
        </svg>
        {{ _('Back') }}
    </a>
</div>
```

**Key Features:**
- Icon in colored circle (`bg-primary/10`)
- Title + subtitle for context
- Back button for navigation
- Responsive flex layout

#### Controls Section
Filter and selection controls in a bordered card:

```html
<div class="bg-base-100 border border-base-300 rounded-lg shadow-sm p-4">
    <!-- Business Selector (Most Important - Full Width) -->
    <div class="mb-4">
        <label for="businessId" class="label py-1">
            <span class="label-text text-xs font-bold uppercase tracking-wider text-base-content/70">{{ _('Business') }}</span>
        </label>
        <select id="businessId" class="select select-bordered w-full focus:select-primary focus:ring-2 focus:ring-primary/20 transition-all" aria-label="{{ _('Select business to analyze') }}">
            <option value="">{{ _('Select Business') }}</option>
            {% for business in businesses %}
            <option value="{{ business.id }}">{{ business.name }}</option>
            {% endfor %}
        </select>
    </div>

    <div class="divider my-3 text-xs text-base-content/50">{{ _('Select time period') }}</div>

    <!-- Selected Period Banner (Hidden by default, shown when report loaded) -->
    <div id="selectedPeriodBanner" class="hidden mb-3 p-3 bg-info/10 border border-info/30 rounded-lg">
        <div class="flex items-center gap-2 text-sm">
            <svg class="w-4 h-4 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
            <span class="font-medium text-info">{{ _('Viewing') }}:</span>
            <span id="selectedPeriodText" class="text-base-content font-semibold"></span>
        </div>
    </div>

    <!-- Quick Action Buttons (First button with icon, starts as btn-outline) -->
    <div class="flex flex-wrap gap-2 mb-4">
        <button class="btn btn-sm btn-outline quick-week-btn transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary/20" data-offset="0" aria-label="{{ _('Show current week') }}">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
            {{ _('This Week') }}
        </button>
        <button class="btn btn-sm btn-outline quick-week-btn transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary/20" data-offset="1" aria-label="{{ _('Show last week') }}">
            {{ _('Last Week') }}
        </button>
        <button class="btn btn-sm btn-outline quick-week-btn transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary/20" data-offset="2" aria-label="{{ _('Show 2 weeks ago') }}">
            {{ _('2 Weeks Ago') }}
        </button>
        <button class="btn btn-sm btn-outline quick-week-btn transition-all hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary/20" data-offset="4" aria-label="{{ _('Show 4 weeks ago') }}">
            {{ _('Last Month') }}
        </button>
    </div>

    <!-- Custom Date Selector (Collapsed by Default) -->
    <details class="collapse collapse-arrow bg-base-200/50 rounded-lg border border-base-300">
        <summary class="collapse-title text-sm font-medium cursor-pointer hover:bg-base-200 transition-all">
            <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <span>{{ _('Pick Custom Date') }}</span>
            </div>
        </summary>
        <div class="collapse-content pt-3">
            <div class="form-control">
                <label for="reportDate" class="label py-1">
                    <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/70">{{ _('Any date in the week') }}</span>
                </label>
                <input type="date" id="reportDate" class="input input-bordered w-full focus:input-primary focus:ring-2 focus:ring-primary/20 transition-all" aria-describedby="weekDisplay" />
                <label class="label pt-2" id="week-display-container">
                    <span class="label-text-alt text-info font-medium flex items-center gap-1" id="weekDisplay">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        {{ _('Select a date to see its week') }}
                    </span>
                </label>
            </div>
        </div>
    </details>
</div>
```

**Key Features:**
- **Business selector at top:** Full width, most prominent position (no grid layout)
- **Visual hierarchy:** Business selection is clearly the first step
- **Selected period banner:** Info-styled banner shows what data is being viewed (hidden until report loads)
- **Quick action buttons:** First button includes icon, all have proper aria-labels
- **Collapsed custom picker:** Advanced date selection hidden by default to reduce visual clutter
- **Auto-generate pattern:** No explicit "Generate Report" button - report updates on selection changes
- **Focus states:** All interactive elements have visible focus rings for accessibility
- **Transitions:** Smooth hover/active effects on all buttons

**Adaptive Patterns:**
- For daily reports: Use quick buttons for "Today", "Yesterday", "7 Days Ago", "30 Days Ago"
- For weekly reports: Use quick buttons for "This Week", "Last Week", "2 Weeks Ago", "Last Month"
- For monthly reports: Use quick buttons for "This Month", "Last Month", "3 Months Ago", "Last Year"

### Report States

#### Loading State
Show loading spinner with message:

```html
<div id="loadingState" class="hidden">
    <div class="flex items-center justify-center py-12">
        <div class="text-center">
            <span class="loading loading-spinner loading-lg text-primary"></span>
            <p class="text-base-content/60 mt-4">{{ _('Loading report data...') }}</p>
        </div>
    </div>
</div>
```

#### Error State
Clear error display with icon:

```html
<div id="errorState" class="hidden">
    <div class="alert alert-error shadow-lg">
        <div class="flex items-start gap-3">
            <svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <div>
                <h3 class="font-bold">{{ _('Error Loading Report') }}</h3>
                <div class="text-sm" id="errorMessage"></div>
            </div>
        </div>
    </div>
</div>
```

#### Selected Period Banner
Show what data is being displayed (placed within the controls card, after divider and before quick action buttons):

```html
<!-- Placed inside the controls card, after the divider -->
<div id="selectedPeriodBanner" class="hidden mb-3 p-3 bg-info/10 border border-info/30 rounded-lg">
    <div class="flex items-center gap-2 text-sm">
        <svg class="w-4 h-4 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
        <span class="font-medium text-info">{{ _('Viewing') }}:</span>
        <span id="selectedPeriodText" class="text-base-content font-semibold"></span>
    </div>
</div>
```

**Usage Pattern:**
- Hidden by default (`hidden` class)
- Shown when report is successfully loaded
- Updated via JavaScript: `selectedPeriodText.textContent = "Week of Dec 29 - Jan 4"`
- Provides visual confirmation of what data the user is viewing
- Uses info color scheme to stand out without alarming
- Positioned within the controls card for context

### Summary Cards Pattern

Display key metrics in a grid:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Metric Card: Highest Revenue Day -->
    <div class="bg-base-100 border border-base-300 rounded-lg p-4 shadow-sm">
        <div class="flex items-center gap-2 mb-2">
            <svg class="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
            </svg>
            <h3 class="font-semibold text-sm text-base-content/70">{{ _('Highest Revenue Day') }}</h3>
        </div>
        <p class="text-2xl font-bold text-base-content" id="highestDay">-</p>
        <p class="text-sm text-base-content/60 mt-1" id="highestDayRevenue">-</p>
        <p class="text-xs text-base-content/50 mt-1" id="highestDayDate">-</p>
    </div>

    <!-- Metric Card: Growth (with dynamic color) -->
    <div class="bg-base-100 border border-base-300 rounded-lg p-4 shadow-sm">
        <div class="flex items-center gap-2 mb-2">
            <svg class="w-5 h-5 text-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
            </svg>
            <h3 class="font-semibold text-sm text-base-content/70">{{ _('Growth vs Previous') }}</h3>
        </div>
        <p class="text-2xl font-bold font-mono tabular-nums" id="weekGrowthPercent">-</p>
        <p class="text-sm font-mono tabular-nums text-base-content/60 mt-1" id="weekGrowthDifference">-</p>
    </div>
</div>
```

**Key Features:**
- Icon with semantic color (success/error/info)
- Clear label with uppercase
- Large primary value
- Supporting secondary and tertiary values
- Placeholder `-` while loading
- `tabular-nums` for numeric values

**JavaScript Pattern for Dynamic Colors:**
```javascript
// Update growth with dynamic color based on value
const growth = parseFloat(data.week_over_week_growth);
const isPositive = growth > 0;
const isNegative = growth < 0;

const colorClass = isPositive ? 'text-success' : isNegative ? 'text-error' : 'text-base-content/60';
const arrow = isPositive ? '↑' : isNegative ? '↓' : '→';

growthPercentEl.className = `text-2xl font-bold font-mono tabular-nums ${colorClass}`;
growthPercentEl.textContent = `${arrow} ${growth > 0 ? '+' : ''}${growth}%`;
```

### Chart Integration

Use Chart.js with consistent styling:

```html
<!-- Chart Container -->
<div class="bg-base-100 border border-base-300 rounded-lg p-6 shadow-sm">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold">{{ _('Chart Title') }}</h2>
        <div class="text-xs text-base-content/60">{{ _('Subtitle or context') }}</div>
    </div>
    <div class="relative" style="height: 350px;">
        <canvas id="chartId"></canvas>
    </div>
</div>
```

**Chart.js Configuration Pattern:**
```javascript
// Line chart configuration
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
            {
                label: 'Last Week',
                data: previousWeekData,
                borderColor: 'rgb(156, 163, 175)', // Gray
                backgroundColor: 'rgba(156, 163, 175, 0.1)',
                borderWidth: 2,
                borderDash: [5, 5], // Dashed for historical
                tension: 0.4,
                pointRadius: 4,
                spanGaps: false, // Don't connect missing data
            },
            {
                label: 'This Week',
                data: currentWeekData,
                borderColor: 'rgb(99, 102, 241)', // Primary blue
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3, // Thicker for emphasis
                tension: 0.4,
                pointRadius: 5,
                fill: true,
                spanGaps: false,
            },
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: function(context) {
                        if (context.parsed.y === null) {
                            return 'No data';
                        }
                        return formatCurrency(context.parsed.y);
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: function(value) {
                        return formatCurrency(value);
                    }
                }
            }
        }
    }
});
```

**Chart Styling Rules:**
- Current/active data: Primary color (`rgb(99, 102, 241)`), thicker lines (3px), filled area
- Historical data: Gray (`rgb(156, 163, 175)`), thinner lines (2px), dashed
- Always format currency in tooltips and axes
- Use `spanGaps: false` to show data gaps clearly
- Set fixed height (350px) for consistency
- `responsive: true, maintainAspectRatio: false` for proper sizing

### Data Tables in Reports

Show detailed day-by-day breakdowns:

```html
<div class="bg-base-100 border border-base-300 rounded-lg p-6 shadow-sm">
    <h2 class="text-lg font-semibold mb-4">{{ _('Detailed Breakdown') }}</h2>
    <div class="overflow-x-auto">
        <table class="table table-sm table-zebra w-full">
            <thead>
                <tr>
                    <th>{{ _('Day') }}</th>
                    <th>{{ _('Date') }}</th>
                    <th class="text-right">{{ _('Revenue') }}</th>
                    <th class="text-right">{{ _('WoW Growth') }}</th>
                    <th class="text-center">{{ _('Trend') }}</th>
                </tr>
            </thead>
            <tbody id="dataTable">
                <!-- Populated by JavaScript -->
            </tbody>
        </table>
    </div>
</div>
```

**JavaScript Pattern for Table Rows:**
```javascript
data.current_week.forEach(day => {
    const row = document.createElement('tr');
    
    // Dynamic color based on growth
    const growthClass = day.growth_percent > 0 ? 'text-success' : 
                       day.growth_percent < 0 ? 'text-error' : 
                       'text-base-content/60';
    
    const growthText = day.growth_percent !== null ? 
        `${day.growth_percent > 0 ? '+' : ''}${day.growth_percent}%` : 
        '-';
    
    // Show dash if no data, currency if we have data
    const revenueDisplay = day.has_data ? formatCurrency(day.revenue) : '-';
    const revenueClass = day.has_data ? 'font-mono' : 'text-base-content/40';
    
    row.innerHTML = `
        <td class="font-medium">${translateDayName(day.day_name)}</td>
        <td>${day.date}</td>
        <td class="text-right ${revenueClass}">${revenueDisplay}</td>
        <td class="text-right font-mono ${growthClass}">${growthText}</td>
        <td class="text-center text-lg">${day.trend_arrow}</td>
    `;
    
    tableBody.appendChild(row);
});
```

**Key Features:**
- Use `-` for missing/null data (not `0` or empty)
- Right-align numeric columns
- Center-align icon columns
- Dynamic color for growth indicators
- `font-mono` for all numeric values
- Muted style (`text-base-content/40`) for missing data

### Interactive Report Controls

**Modern Pattern:** Reports auto-generate when filters change. No separate "Generate Report" button needed.

#### Complete Auto-Generate Pattern
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Read URL parameters for deep linking
    const urlParams = new URLSearchParams(window.location.search);
    const urlDate = urlParams.get('date');
    const urlBusinessId = urlParams.get('business_id');
    
    // Set default date (today for daily reports, this week for weekly reports)
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('reportDate').value = urlDate || today;
    
    // Set business from URL param if exists
    if (urlBusinessId) {
        document.getElementById('businessId').value = urlBusinessId;
    }
    
    // Auto-generate report if URL has params (deep linking support)
    if (urlDate && urlBusinessId) {
        generateReport();
        // Highlight the appropriate quick button if applicable
        highlightMatchingQuickButton();
    }

    // Auto-generate when business changes
    document.getElementById('businessId').addEventListener('change', function() {
        const date = document.getElementById('reportDate').value;
        if (this.value && date) {
            generateReport();
        }
    });

    // Auto-generate when date changes (from custom date picker)
    document.getElementById('reportDate').addEventListener('change', function() {
        const businessId = document.getElementById('businessId').value;
        if (this.value && businessId) {
            // Clear quick button highlights when custom date is used
            document.querySelectorAll('.quick-week-btn').forEach(b => {
                b.classList.remove('btn-primary');
                b.classList.add('btn-outline');
            });
            generateReport();
        }
    });

    // Quick action buttons with active state
    document.querySelectorAll('.quick-week-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const offset = parseInt(this.getAttribute('data-offset'));
            const date = new Date();
            date.setDate(date.getDate() - (offset * 7)); // For weekly reports
            // For daily reports: date.setDate(date.getDate() - offset);
            
            document.getElementById('reportDate').value = date.toISOString().split('T')[0];
            
            // Highlight active button
            document.querySelectorAll('.quick-week-btn').forEach(b => {
                b.classList.remove('btn-primary');
                b.classList.add('btn-outline');
            });
            this.classList.remove('btn-outline');
            this.classList.add('btn-primary');

            // Auto-generate if business is selected
            const businessId = document.getElementById('businessId').value;
            if (businessId) {
                generateReport();
            }
        });
    });

    // Highlight default button if today/this week is selected
    if (document.getElementById('reportDate').value === today && !urlDate) {
        const defaultBtn = document.querySelector('.quick-week-btn[data-offset="0"]');
        if (defaultBtn) {
            defaultBtn.classList.remove('btn-outline');
            defaultBtn.classList.add('btn-primary');
        }
    }
});
```

#### Update URL for Deep Linking
```javascript
async function generateReport() {
    const date = document.getElementById('reportDate').value;
    const businessId = document.getElementById('businessId').value;

    if (!businessId) {
        showError('{{ _("Please select a business") }}');
        return;
    }

    // Update URL with parameters for deep linking and sharing
    const newUrl = `${window.location.pathname}?date=${date}&business_id=${businessId}`;
    window.history.pushState({date, businessId}, '', newUrl);

    try {
        showLoading(true);
        hideError();

        const response = await fetch(`/reports/endpoint/data?date=${date}&business_id=${businessId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '{{ _("Failed to generate report") }}');
        }

        const data = await response.json();
        displayReport(data);
        
        // Show selected period banner
        updateSelectedPeriodBanner(data.period_display);
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}
```

#### Update Selected Period Banner
```javascript
function updateSelectedPeriodBanner(periodText) {
    const banner = document.getElementById('selectedPeriodBanner');
    const textEl = document.getElementById('selectedPeriodText');
    
    if (periodText) {
        textEl.textContent = periodText;
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}
```

**Key Principles:**
1. **No manual trigger:** Reports generate automatically when filters change
2. **Deep linking:** Support URL parameters for sharing specific report views
3. **Active state management:** Visual feedback on which quick action is selected
4. **Clear custom selection:** When custom date is picked, clear quick button highlights
5. **Default highlighting:** Pre-select the most common option (Today/This Week)
6. **Graceful degradation:** Show helpful error if business not selected

### Currency Formatting in Reports

**JavaScript Utility:**
```javascript
// Format for Guaraníes (₲ 2.500.000 - dot separator, no decimals)
const formatCurrency = (value) => {
    const num = Math.round(parseFloat(value));
    return 'Gs ' + num.toLocaleString('es-PY').replace(/,/g, '.');
};
```

**Use consistently:**
- Chart tooltips
- Chart axes
- Summary cards
- Table cells
- All numeric displays

### Report Dashboard (List of Reports)

Grid of available reports:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {% for report in reports %}
    <div class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-lg transition-all duration-200 {% if not report.enabled %}opacity-60{% else %}hover:scale-[1.02]{% endif %}">
        <div class="card-body p-4 md:p-5">
            <div class="flex items-start gap-3 mb-3">
                <div class="p-2 bg-primary/10 rounded-lg flex-shrink-0">
                    <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{{ report.icon }}"/>
                    </svg>
                </div>
                <div class="flex-1">
                    <h3 class="card-title text-lg font-bold">{{ report.title }}</h3>
                </div>
                {% if not report.enabled %}
                <span class="badge badge-sm badge-ghost">{{ _('Coming Soon') }}</span>
                {% endif %}
            </div>
            <p class="text-sm text-base-content/70 mb-4">{{ report.description }}</p>
            <div class="card-actions">
                {% if report.enabled %}
                <a href="/reports/{{ report.id }}" class="btn btn-sm btn-primary w-full gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <!-- Icon -->
                    </svg>
                    {{ _('View Report') }}
                </a>
                {% else %}
                <button disabled class="btn btn-sm btn-primary w-full opacity-50 cursor-not-allowed">
                    {{ _('Coming Soon') }}
                </button>
                {% endif %}
            </div>
        </div>
    </div>
    {% endfor %}
</div>
```

### Report Best Practices

#### Data Handling
1. **Always show placeholders:** Use `-` while loading or for null values
2. **Handle missing data gracefully:** Don't show `0` when there's no data
3. **Show context:** Display date ranges, business names, and time periods prominently
4. **Cache strategically:** Current period = 5 min TTL, past periods = 1 hour TTL

#### Visual Feedback
1. **Loading states:** Show spinner + message during data fetch
2. **Error states:** Clear error messages with retry options
3. **Empty states:** Explain why no data is shown
4. **Success indicators:** Highlight selected period/filters

#### Interaction Patterns
1. **Auto-generate:** Trigger report generation on control changes (don't require "Generate" button)
2. **Quick actions first:** Most common periods as buttons (This Week, Last Week)
3. **Advanced options collapsed:** Keep interface clean, show advanced options on demand
4. **Active state indication:** Show which quick action is active

#### Performance
1. **Lazy load charts:** Only initialize Chart.js when data is available
2. **Destroy and recreate:** Always destroy existing chart before creating new one
3. **Cache results:** Use cache key based on all parameters
4. **Async data loading:** Use `async/await` with proper error handling

#### Accessibility
1. **ARIA labels:** All interactive controls
2. **Screen reader announcements:** For loading/error states
3. **Keyboard navigation:** All controls keyboard accessible
4. **Focus management:** Maintain logical focus order

---

## 📚 Reference Examples

See these files for complete implementations:
- `templates/sessions/close_session.html` - Complete form with sections
- `templates/partials/transfer_items_table.html` - Line item table pattern
- `templates/partials/expense_items_table.html` - Line item table pattern
- `templates/reports/weekly-trend.html` - Complete report with charts, tables, and modern filter pattern
- `templates/reports/daily-revenue.html` - Complete report with modern filter pattern and auto-generate behavior
- `templates/reports/dashboard.html` - Report dashboard/listing page
- `src/cashpilot/api/weekly_trend.py` - Report API endpoint pattern
- `src/cashpilot/api/daily_revenue.py` - Report API endpoint pattern

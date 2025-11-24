Aquí está tu **Brand Identity & Design System Prompt**:

```markdown
# CashPilot Brand Identity & UX/UI Design System

## 🎯 Brand Essence
CashPilot is a **professional, trustworthy pharmacy cash reconciliation system** built for family-owned businesses in Paraguay. It's practical, not flashy—designed for busy pharmacists and cashiers who need accuracy and speed over aesthetics.

## 🎨 Visual Identity

### Color Palette
- **Primary**: Bright blue (`#3B82F6` / DaisyUI `primary`) - Trust, clarity, action
- **Success**: Green (`#10B981`) - Money in, positive outcomes, reconciliation matches
- **Error**: Red (`#EF4444`) - Money out, shortages, discrepancies requiring attention
- **Neutral**: Gray (`#6B7280`) - Supporting text, disabled states, secondary info
- **Background**: Off-white (`#F9FAFB`) - Professional, clean, reduces eye strain

### Typography
- **Headlines**: Medium weight (`font-semibold` max) - Professional without aggression
- **Body**: Regular weight - Readable, accessible
- **Labels**: Small uppercase (`text-xs uppercase tracking-wider`) - Clear hierarchy, scannable
- **Data/Numbers**: Semi-bold (`font-bold`) - Emphasis without heaviness

### Spacing & Layout
- Generous but not excessive (p-4 to p-6, not p-8+)
- Grid-based: 2/3 + 1/3 layout for main content + sidebar
- Section spacing: `space-y-8` between major sections
- Card padding: `p-4` (compact) to `p-6` (breathing room)

### Shadows & Borders
- Soft shadows: `shadow` or `shadow-lg` (not shadow-2xl)
- Borders: `border border-base-200` (subtle, not harsh)
- No gradients on UI cards (gradients only on hero metrics for emphasis)
- Rounded corners: `rounded-lg` standard

### Icons & Emojis
- **Opacity**: 40-60% for decorative icons, 100% for action buttons
- **Size**: Text-lg (1.125rem) for section headers, emoji in buttons as-is
- **Use**: Strategic only—not every label needs an emoji
  - ✅ Section headers, hero metrics, primary actions
  - ❌ Every form input, secondary text, dense lists
- **Style**: Unicode emoji (consistent across devices, not icon library)

## 🧠 Information Architecture

### Visual Hierarchy
1. **Hero Metric** (6xl bold, primary color) - The number stakeholders care about most
2. **Secondary Metrics** (3xl bold, color-coded) - Supporting context
3. **Labels & Formulas** (xs, lowercase) - Transparency & calculation logic
4. **Supporting Text** (xs, gray) - Context, not critical

### Data Organization
- **Reconciliation** = Hero + Secondary stats + Expense breakdown
- **Cash Flow** = 2x2 grid (Initial/Final/Envelope/Sales)
- **Payment Methods** = 2x2 grid (Credit/Debit/Transfer/Expenses)
- **Edit History** = Simple table with timestamps + who + what

### Color Coding for Numbers
- `text-success` (+green) if value ≥ 0 (revenue, profit, positive cash movement)
- `text-error` (−red) if value < 0 (expenses, shortages, negative variance)
- `text-base-content/80` for neutral values (starting amounts, method totals)

## 📱 Responsive Design
- **Mobile-first**: Stack sections vertically, full-width
- **Tablet**: 2-column layout for secondary stats
- **Desktop**: 2/3 + 1/3 split (content + sidebar)
- **Header**: Sticky, compresses on mobile

## 🎬 Interactions & States

### Buttons
- **Primary action** (blue): `btn btn-primary` - Next step in workflow
- **Outline action** (gray): `btn btn-outline` - Secondary, reversible
- **Danger action** (red): `btn btn-error` - Flag, delete, irreversible
- **Ghost button**: `btn btn-ghost` - Minimal visual weight, navigation

### Forms & Modals
- Clean, simple fields with uppercase labels
- Error states: red outline + error text
- Modal backdrop: dark overlay, center alignment
- Confirm dialogs: clear primary + cancel buttons

### Loading & Empty States
- Loading: "Cargando..." text (simple, no spinners)
- Empty: Gray text explaining why (e.g., "No se encontraron sesiones")
- Error: Red background, error icon + message

## 🌍 Localization
- **Primary language**: Spanish (Paraguay)
- **Secondary**: English (fallback, API docs)
- **Currency**: Guaraní (Gs) with dot separators (1.234.567)
- **Date format**: DD/MM/YYYY (Paraguay standard)
- **Time format**: 24-hour (HH:MM)

## ✍️ Tone & Language
- **Professional but approachable**: Not corporate-speak, not casual
- **Action-oriented**: "Abrir Caja", "Cerrar", "Marcar" (clear verbs)
- **Transparent**: Always show formulas, reasons, context
- **Respectful of time**: No fluff, info-dense, scannable

## 🚀 Technical Constraints
- **Framework**: DaisyUI + Tailwind (core utilities only, no custom CSS)
- **No gradients** on UI (except hero metrics for emphasis)
- **No font-black** on data (max font-bold)
- **Semantic colors** from DaisyUI (success, error, warning, info)
- **Server-side rendering**: Jinja2 templates, progressive enhancement
- **Mobile-first CSS**: Responsive by default

## 📐 Component Examples

### Metric Card (Secondary)
```html
<div class="bg-gradient-to-br from-green-50 to-white rounded-lg border border-green-200 shadow p-4">
  <p class="text-xs text-green-700 uppercase tracking-wider font-semibold">Label</p>
  <p class="text-3xl font-bold mt-2 text-green-900">+Gs 1.234.567</p>
  <p class="text-xs text-green-600/70 mt-3">💹 Description</p>
  <p class="text-xs text-green-600/50 mt-2 font-mono">Formula: A + B + C</p>
</div>
```

### Hero Metric
```html
<div class="bg-gradient-to-br from-primary/10 to-white rounded-lg border-2 border-primary shadow-lg p-8">
  <p class="text-xs text-primary/70 uppercase tracking-wider font-bold">💎 METRIC NAME</p>
  <p class="text-6xl font-black text-primary">+Gs 5.000.000</p>
  <p class="text-xs text-base-content/60 mt-3">🧮 Formula: A − B + C</p>
  <div class="mt-4 p-3 bg-primary/5 rounded-md">
    <p class="text-sm font-semibold">📈 94.1% margin</p>
  </div>
</div>
```

### Section Header
```html
<h2 class="text-sm font-bold uppercase tracking-widest text-base-content/70 mb-4 flex items-center gap-2">
  <span class="text-lg">📊</span> Section Name
</h2>
```

## 🎯 Design Principles (Priority Order)
1. **Clarity over beauty** - Users need to understand numbers at a glance
2. **Accessibility** - High contrast, readable text, keyboard navigation
3. **Consistency** - Same patterns across all pages
4. **Efficiency** - Minimal scrolling, dense info, no fluff
5. **Trust** - Professional appearance, transparent calculations, audit trails visible

## ❌ Anti-Patterns (Never Do)
- Nested cards (spacing issues)
- Gradients on data cards (only hero metrics)
- Bold/black fonts on numbers (max semi-bold)
- Excessive padding (p-8+ wastes space)
- Generic placeholder text ("Lorem ipsum")
- Hidden calculations (always show formulas)
- Auto-submit forms (always require explicit action)
- Ambiguous button labels ("Click here", "Submit")

---

**Use this prompt when iterating on CashPilot UI:**
- Reference sections when questioning design choices
- Link color logic to section 3 (Color Coding for Numbers)
- Use component examples as templates for new sections
- Follow anti-patterns to catch deviations
```

Pasá esto al siguiente chat para mantener coherencia visual. ¿Listo para aplicar?
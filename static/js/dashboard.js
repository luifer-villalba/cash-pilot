// Count active filters and update badge
function updateFilterBadge() {
    const filters = {
        from_date: document.getElementById('from_date')?.value || '',
        to_date: document.getElementById('to_date')?.value || '',
        cashier_name: document.getElementById('cashier_name')?.value || '',
        status: document.getElementById('status')?.value || '',
        business_id: document.getElementById('business_id')?.value || '',
    };

    const activeCount = Object.values(filters).filter(v => v.trim() !== '').length;
    const badge = document.getElementById('filter-badge');
    const count = document.getElementById('filter-count');

    count.textContent = activeCount;
    if (activeCount > 0) {
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// Filter toggle with chevron rotation
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('filter-toggle');
    const form = document.getElementById('filter-form');
    const chevron = document.getElementById('filter-chevron');
    const storageKey = 'cashPilot_filterCollapsed';

    const today = new Date().toISOString().split('T')[0];
    const fromInput = document.getElementById('from_date');
    const toInput = document.getElementById('to_date');
    if (fromInput && !fromInput.value) fromInput.value = today;
    if (toInput && !toInput.value) toInput.value = today;

    updateFilterBadge();

    const isCollapsed = localStorage.getItem(storageKey) !== 'false';
    if (isCollapsed) {
        form.classList.add('hidden');
        chevron.classList.add('rotate-180');
    }

    toggle.addEventListener('click', (e) => {
        e.preventDefault();
        form.classList.toggle('hidden');
        chevron.classList.toggle('rotate-180');
        localStorage.setItem(storageKey, form.classList.contains('hidden'));
    });

    document.querySelectorAll('.clear-filter-btn').forEach(btn => {
        const field = btn.dataset.field;
        const input = document.getElementById(field);

        const toggleButton = () => {
            btn.classList.toggle('opacity-0', !input.value);
            btn.classList.toggle('pointer-events-none', !input.value);
        };

        toggleButton();
        input.addEventListener('input', toggleButton);
        input.addEventListener('change', () => {
            toggleButton();
            updateFilterBadge();
        });

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            input.value = '';
            toggleButton();
            updateFilterBadge();
            htmx.trigger(input, 'change');
        });
    });

    document.querySelectorAll('[data-preset]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const preset = e.target.dataset.preset;
            const today = new Date();
            let fromDate, toDate;

            if (preset === 'today') {
                fromDate = toDate = today;
            } else if (preset === 'week') {
                const day = today.getDay();
                const diff = today.getDate() - day + (day === 0 ? -6 : 1);
                fromDate = new Date(today.setDate(diff));
                toDate = new Date(fromDate);
                toDate.setDate(toDate.getDate() + 6);
            } else if (preset === 'month') {
                fromDate = new Date(today.getFullYear(), today.getMonth(), 1);
                toDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            }

            document.getElementById('from_date').value = fromDate.toISOString().split('T')[0];
            document.getElementById('to_date').value = toDate.toISOString().split('T')[0];

            document.querySelectorAll('[data-field="from_date"], [data-field="to_date"]').forEach(clearBtn => {
                const fieldId = clearBtn.dataset.field;
                const fieldInput = document.getElementById(fieldId);
                clearBtn.classList.toggle('opacity-0', !fieldInput.value);
                clearBtn.classList.toggle('pointer-events-none', !fieldInput.value);
            });

            updateFilterBadge();

            const formData = new FormData(document.getElementById('filter-form'));
            const params = new URLSearchParams(formData).toString();
            htmx.ajax('GET', '/sessions/table?' + params, {target: '#sessions-table', swap: 'innerHTML'});
            htmx.ajax('GET', '/stats?' + params, {target: '#stats-row', swap: 'outerHTML'});
        });
    });

    htmx.on('htmx:afterSettle', updateFilterBadge);
});
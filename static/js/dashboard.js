// Count active filters and update badge
function updateFilterBadge() {
    var fromDateEl = document.getElementById('from_date');
    var toDateEl = document.getElementById('to_date');
    var cashierNameEl = document.getElementById('cashier_name');
    var statusEl = document.getElementById('status');
    var businessIdEl = document.getElementById('business_id');
    
    var filters = {
        from_date: (fromDateEl && fromDateEl.value) ? fromDateEl.value : '',
        to_date: (toDateEl && toDateEl.value) ? toDateEl.value : '',
        cashier_name: (cashierNameEl && cashierNameEl.value) ? cashierNameEl.value : '',
        status: (statusEl && statusEl.value) ? statusEl.value : '',
        business_id: (businessIdEl && businessIdEl.value) ? businessIdEl.value : '',
    };

    var activeCount = 0;
    for (var key in filters) {
        if (filters.hasOwnProperty(key) && filters[key].trim() !== '') {
            activeCount++;
        }
    }
    var badge = document.getElementById('filter-badge');
    var count = document.getElementById('filter-count');

    count.textContent = activeCount;
    if (activeCount > 0) {
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// Filter toggle with chevron rotation
document.addEventListener('DOMContentLoaded', function() {
    var toggle = document.getElementById('filter-toggle');
    var form = document.getElementById('filter-form');
    var chevron = document.getElementById('filter-chevron');
    var storageKey = 'cashPilot_filterCollapsed';

    var today = new Date().toISOString().split('T')[0];
    var fromInput = document.getElementById('from_date');
    var toInput = document.getElementById('to_date');
    if (fromInput && !fromInput.value) fromInput.value = today;
    if (toInput && !toInput.value) toInput.value = today;

    updateFilterBadge();

    var isCollapsed = localStorage.getItem(storageKey) !== 'false';
    if (isCollapsed) {
        form.classList.add('hidden');
        chevron.classList.add('rotate-180');
    }

    toggle.addEventListener('click', function(e) {
        e.preventDefault();
        form.classList.toggle('hidden');
        chevron.classList.toggle('rotate-180');
        localStorage.setItem(storageKey, form.classList.contains('hidden'));
    });

    document.querySelectorAll('.clear-filter-btn').forEach(function(btn) {
        var field = btn.dataset.field;
        var input = document.getElementById(field);

        var toggleButton = function() {
            btn.classList.toggle('opacity-0', !input.value);
            btn.classList.toggle('pointer-events-none', !input.value);
        };

        toggleButton();
        input.addEventListener('input', toggleButton);
        input.addEventListener('change', function() {
            toggleButton();
            updateFilterBadge();
        });

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            input.value = '';
            toggleButton();
            updateFilterBadge();
            htmx.trigger(input, 'change');
        });
    });

    document.querySelectorAll('[data-preset]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            var preset = e.target.dataset.preset;
            var today = new Date();
            var fromDate, toDate;

            if (preset === 'today') {
                fromDate = toDate = today;
            } else if (preset === 'yesterday') {
                fromDate = new Date(today);
                fromDate.setDate(fromDate.getDate() - 1);
                toDate = fromDate;
            } else if (preset === 'week') {
                // Last 7 days: today - 6 days to today (7 days total)
                fromDate = new Date(today);
                fromDate.setDate(fromDate.getDate() - 6);
                toDate = new Date(today);
            } else if (preset === 'month') {
                // Last 30 days: today - 29 days to today (30 days total)
                fromDate = new Date(today);
                fromDate.setDate(fromDate.getDate() - 29);
                toDate = new Date(today);
            }

            // Format dates as YYYY-MM-DD using local date to avoid timezone issues
            function formatLocalDate(d) {
                var year = d.getFullYear();
                var month = String(d.getMonth() + 1).padStart(2, '0');
                var day = String(d.getDate()).padStart(2, '0');
                return year + '-' + month + '-' + day;
            }
            
            document.getElementById('from_date').value = formatLocalDate(fromDate);
            document.getElementById('to_date').value = formatLocalDate(toDate);

            document.querySelectorAll('[data-field="from_date"], [data-field="to_date"]').forEach(function(clearBtn) {
                var fieldId = clearBtn.dataset.field;
                var fieldInput = document.getElementById(fieldId);
                clearBtn.classList.toggle('opacity-0', !fieldInput.value);
                clearBtn.classList.toggle('pointer-events-none', !fieldInput.value);
            });

            updateFilterBadge();

            var formData = new FormData(document.getElementById('filter-form'));
            var params = new URLSearchParams(formData).toString();
            htmx.ajax('GET', '/sessions/table?' + params, {target: '#sessions-table', swap: 'innerHTML'});
            htmx.ajax('GET', '/stats?' + params, {target: '#stats-row', swap: 'outerHTML'});
        });
    });

    htmx.on('htmx:afterSettle', updateFilterBadge);
});

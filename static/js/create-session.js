document.addEventListener('DOMContentLoaded', function() {
    var now = new Date();

    // Set date to today (ISO format)
    var dateInput = document.getElementById('session-date');
    if (dateInput && !dateInput.value) {
        dateInput.value = now.toISOString().split('T')[0];
    }

    // Set time to current time (HH:MM format)
    var timeInput = document.getElementById('opened-time');
    if (timeInput && !timeInput.value) {
        var hours = String(now.getHours()).padStart(2, '0');
        var minutes = String(now.getMinutes()).padStart(2, '0');
        timeInput.value = hours + ':' + minutes;
    }

    // Cashier dropdown fetch on business select change
    var businessSelect = document.getElementById('business-select');
    if (businessSelect) {
        businessSelect.addEventListener('change', function(e) {
            var businessId = e.target.value;
            if (!businessId) return;

            fetch('/businesses/' + businessId + '/cashiers')
                .then(function(res) {
                    return res.json();
                })
                .then(function(data) {
                    var select = document.getElementById('cashier-select');
                    select.innerHTML = '<option value="">Select cashier</option>';
                    data.cashiers.forEach(function(name) {
                        var opt = document.createElement('option');
                        opt.value = name;
                        opt.textContent = name;
                        select.appendChild(opt);
                    });
                })
                .catch(function(error) {
                    console.error('Error loading cashiers:', error);
                });
        });
    }
});

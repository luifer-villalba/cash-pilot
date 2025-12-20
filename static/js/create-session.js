document.addEventListener('DOMContentLoaded', function() {
    const now = new Date();

    // Set date to today (ISO format)
    const dateInput = document.getElementById('session-date');
    if (dateInput && !dateInput.value) {
        dateInput.value = now.toISOString().split('T')[0];
    }

    // Set time to current time (HH:MM format)
    const timeInput = document.getElementById('opened-time');
    if (timeInput && !timeInput.value) {
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        timeInput.value = `${hours}:${minutes}`;
    }

    // Cashier dropdown fetch on business select change
    document.getElementById('business-select').addEventListener('change', async (e) => {
        const businessId = e.target.value;
        if (!businessId) return;

        const res = await fetch(`/businesses/${businessId}/cashiers`);
        const data = await res.json();

        const select = document.getElementById('cashier-select');
        select.innerHTML = '<option value="">Select cashier</option>';
        data.cashiers.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        });
    });
});
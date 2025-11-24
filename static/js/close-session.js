// File: static/js/close-session.js

function parseCalculator(value) {
    if (!value) return 0;

    if (value.includes('+')) {
        return value.split('+')
            .map(v => parseInt(v.trim().replace(/\D/g, '')) || 0)
            .reduce((sum, num) => sum + num, 0);
    }

    return parseInt(value.replace(/\D/g, '')) || 0;
}

document.addEventListener('DOMContentLoaded', function () {
    // Calculator-enabled fields
    const calculatorFields = [
        'credit_card_total',
        'debit_card_total',
        'bank_transfer_total',
        'expenses'
    ];

    calculatorFields.forEach(fieldName => {
        const input = document.querySelector(`[name="${fieldName}"]`);
        if (input) {
            input.addEventListener('blur', function () {
                const result = parseCalculator(this.value);
                this.value = currencyFormatter.formatForLocale(result);
            });
        }
    });
});
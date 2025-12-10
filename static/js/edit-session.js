// File: static/js/edit-session.js

function parseCalculator(value) {
    if (!value) return 0;

    if (value.includes('+')) {
        return value.split('+')
            .map(v => parseInt(v.trim().replace(/\D/g, '')) || 0)
            .reduce((sum, num) => sum + num, 0);
    }

    return parseInt(value.replace(/\D/g, '')) || 0;
}

function updatePreview() {
    const finalCash = parseInt(document.querySelector('[name="final_cash"]')?.value?.replace(/\D/g, '')) || 0;
    const form = document.querySelector('form[data-initial-cash]');
    const initialCash = parseInt(form?.dataset.initialCash) || 0;
    const envelope = parseInt(document.querySelector('[name="envelope_amount"]')?.value?.replace(/\D/g, '')) || 0;
    const creditCard = parseCalculator(document.querySelector('[name="credit_card_total"]')?.value);
    const debitCard = parseCalculator(document.querySelector('[name="debit_card_total"]')?.value);
    const bankTransfer = parseCalculator(document.querySelector('[name="bank_transfer_total"]')?.value);
    const expenses = parseCalculator(document.querySelector('[name="expenses"]')?.value);

    const cashSales = (finalCash - initialCash) + envelope;
    const totalSales = cashSales + creditCard + debitCard + bankTransfer;
    const netEarnings = totalSales - expenses;

    const preview = document.getElementById('preview');
    if (preview) {
        preview.innerHTML = `
            <div><span>Cash Sales:</span> <p class="font-bold">${currencyFormatter.format(cashSales)}</p></div>
            <div><span>Total Sales:</span> <p class="font-bold">${currencyFormatter.format(totalSales)}</p></div>
            <div><span>Net Earnings:</span> <p class="font-bold">${currencyFormatter.format(netEarnings)}</p></div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Calculator-enabled fields
    const calculatorFields = [
        'credit_card_total',
        'debit_card_total',
        'bank_transfer_total',
        'expenses',
        'credit_sales_total',
        'credit_payments_collected'
    ];

    calculatorFields.forEach(fieldName => {
        const input = document.querySelector(`[name="${fieldName}"]`);
        if (input) {
            input.addEventListener('blur', function() {
                const result = parseCalculator(this.value);
                this.value = currencyFormatter.formatForLocale(result);
                updatePreview();
            });
            input.addEventListener('input', updatePreview);
        }
    });

    // Regular fields (no calculator)
    document.querySelectorAll('input[name="final_cash"], input[name="envelope_amount"]').forEach(input => {
        input.addEventListener('input', updatePreview);
    });

    updatePreview();
});
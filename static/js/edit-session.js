// File: static/js/edit-session.js

function parseCalculator(value) {
    if (!value) return 0;

    if (value.includes('+')) {
        return value.split('+')
            .map(function(v) {
                return parseInt(v.trim().replace(/\D/g, '')) || 0;
            })
            .reduce(function(sum, num) {
                return sum + num;
            }, 0);
    }

    return parseInt(value.replace(/\D/g, '')) || 0;
}

function updatePreview() {
    var finalCashEl = document.querySelector('[name="final_cash"]');
    var finalCash = 0;
    if (finalCashEl && finalCashEl.value) {
        finalCash = parseInt(finalCashEl.value.replace(/\D/g, '')) || 0;
    }
    
    var form = document.querySelector('form[data-initial-cash]');
    var initialCash = 0;
    if (form && form.dataset && form.dataset.initialCash) {
        initialCash = parseInt(form.dataset.initialCash) || 0;
    }
    
    var envelopeEl = document.querySelector('[name="envelope_amount"]');
    var envelope = 0;
    if (envelopeEl && envelopeEl.value) {
        envelope = parseInt(envelopeEl.value.replace(/\D/g, '')) || 0;
    }
    
    var creditCardEl = document.querySelector('[name="credit_card_total"]');
    var creditCard = 0;
    if (creditCardEl && creditCardEl.value) {
        creditCard = parseCalculator(creditCardEl.value);
    }
    
    var debitCardEl = document.querySelector('[name="debit_card_total"]');
    var debitCard = 0;
    if (debitCardEl && debitCardEl.value) {
        debitCard = parseCalculator(debitCardEl.value);
    }

    // Get bank_transfer and expenses from session totals (read-only display)
    var bankTransferEl = document.querySelector('[data-bank-transfer-total]');
    var bankTransfer = 0;
    if (bankTransferEl && bankTransferEl.dataset && bankTransferEl.dataset.bankTransferTotal) {
        bankTransfer = parseInt(bankTransferEl.dataset.bankTransferTotal) || 0;
    }
    
    var expensesEl = document.querySelector('[data-expenses-total]');
    var expenses = 0;
    if (expensesEl && expensesEl.dataset && expensesEl.dataset.expensesTotal) {
        expenses = parseInt(expensesEl.dataset.expensesTotal) || 0;
    }

    var cashSales = (finalCash - initialCash) + envelope;
    var totalSales = cashSales + creditCard + debitCard + bankTransfer;
    var netEarnings = totalSales - expenses;

    var preview = document.getElementById('preview');
    if (preview) {
        preview.innerHTML = 
            '<div><span>Cash Sales:</span> <p class="font-bold">' + currencyFormatter.format(cashSales) + '</p></div>' +
            '<div><span>Total Sales:</span> <p class="font-bold">' + currencyFormatter.format(totalSales) + '</p></div>' +
            '<div><span>Net Earnings:</span> <p class="font-bold">' + currencyFormatter.format(netEarnings) + '</p></div>';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Calculator-enabled fields (credit only now)
    var calculatorFields = [
        'credit_card_total',
        'debit_card_total',
        'credit_sales_total',
        'credit_payments_collected'
        // Removed: 'bank_transfer_total', 'expenses'
    ];

    calculatorFields.forEach(function(fieldName) {
        var selector = '[name="' + fieldName + '"]';
        var input = document.querySelector(selector);
        if (input) {
            input.addEventListener('blur', function() {
                var result = parseCalculator(this.value);
                this.value = currencyFormatter.formatForLocale(result);
                updatePreview();
            });
            input.addEventListener('input', updatePreview);
        }
    });

    // Regular fields (no calculator)
    document.querySelectorAll('input[name="final_cash"], input[name="envelope_amount"]').forEach(function(input) {
        input.addEventListener('input', updatePreview);
    });

    updatePreview();
});

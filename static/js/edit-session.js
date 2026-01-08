// File: static/js/edit-session.js

// parseCalculator is now defined in currency-formatter.js (global)
// This file uses the global function

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
        envelope = typeof parseCalculator !== 'undefined'
            ? parseCalculator(envelopeEl.value)
            : parseInt(envelopeEl.value.replace(/\D/g, '')) || 0;
    }
    
    var cardTotalEl = document.querySelector('[name="card_total"]');
    var cardTotal = 0;
    if (cardTotalEl && cardTotalEl.value) {
        cardTotal = typeof parseCalculator !== 'undefined' 
            ? parseCalculator(cardTotalEl.value) 
            : parseInt(cardTotalEl.value.replace(/\D/g, '')) || 0;
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
    var totalSales = cashSales + cardTotal + bankTransfer;
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
    // Calculator-enabled fields are identified by data-calculator-field attribute
    // set by currency-formatter.js. We just need to update preview on changes.
    var calculatorFieldSelectors = [
        '[name="card_total"]',
        '[name="credit_sales_total"]',
        '[name="credit_payments_collected"]',
        '[name="envelope_amount"]'
    ];

    calculatorFieldSelectors.forEach(function(selector) {
        var input = document.querySelector(selector);
        if (input) {
            // Calculator fields are handled by currency-formatter.js
            // Just update preview on input/blur
            input.addEventListener('blur', function() {
                updatePreview();
            });
            input.addEventListener('input', updatePreview);
        }
    });

    // Regular fields (no calculator) - envelope_amount is now a calculator field
    document.querySelectorAll('input[name="final_cash"]').forEach(function(input) {
        input.addEventListener('input', updatePreview);
    });

    updatePreview();
});

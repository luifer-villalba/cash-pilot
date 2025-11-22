function updatePreview() {
    const finalCash = parseInt(document.querySelector('[name="final_cash"]')?.value?.replace(/\D/g, '')) || 0;
    const initialCash = parseInt(document.querySelector('[data-initial-cash]')?.dataset.initialCash) || 0;
    const envelope = parseInt(document.querySelector('[name="envelope_amount"]')?.value?.replace(/\D/g, '')) || 0;
    const creditCard = parseInt(document.querySelector('[name="credit_card_total"]')?.value?.replace(/\D/g, '')) || 0;
    const debitCard = parseInt(document.querySelector('[name="debit_card_total"]')?.value?.replace(/\D/g, '')) || 0;
    const bankTransfer = parseInt(document.querySelector('[name="bank_transfer_total"]')?.value?.replace(/\D/g, '')) || 0;
    const expenses = parseInt(document.querySelector('[name="expenses"]')?.value?.replace(/\D/g, '')) || 0;

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
    const now = new Date();

    const timeInput = document.getElementById('closed-time');
    if (timeInput && !timeInput.value) {
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        timeInput.value = `${hours}:${minutes}`;
    }

    document.querySelectorAll('input[name="final_cash"], input[name="envelope_amount"], input[name="credit_card_total"], input[name="debit_card_total"], input[name="bank_transfer_total"], input[name="expenses"]').forEach(input => {
        input.addEventListener('input', updatePreview);
    });

    updatePreview();
});
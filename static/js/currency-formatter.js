// File: static/js/currency-formatter.js

/**
 * Locale-aware currency formatter for CashPilot
 * Supports multiple locales but maintains es-PY currency always
 */

class CurrencyFormatter {
    constructor() {
        this.locale = window.LOCALE || 'es';
        this.currencyLocale = window.CURRENCY_LOCALE || 'es-PY';

        // Locale-specific number formatter (for input display)
        this.numberFormatter = new Intl.NumberFormat(this.locale === 'es' ? 'es-PY' : 'en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    /**
     * Format number for display (e.g., preview cards)
     * es-PY: 1234567 → "Gs 1.234.567"
     * en-US: 1234567 → "Gs 1,234,567"
     */
    format(value) {
        if (!value && value !== 0) return 'Gs 0';
        return `Gs ${this.numberFormatter.format(Math.abs(value))}`;
    }

    /**
     * Format for locale-specific input display
     * Used in real-time preview updates
     */
    formatForLocale(value) {
        if (!value && value !== 0) return '0';
        return this.numberFormatter.format(Math.abs(value));
    }

    /**
     * Get locale-specific decimal separator
     * es-PY → ","
     * en-US → "."
     */
    getDecimalSeparator() {
        return (1.1).toLocaleString(this.locale === 'es' ? 'es-PY' : 'en-US').substring(1, 2);
    }
}

// Initialize global formatter instance
const currencyFormatter = new CurrencyFormatter();

// Debug: Log locale detection
console.log('🌍 Locale Detection:', {
    locale: window.LOCALE,
    currencyLocale: window.CURRENCY_LOCALE,
    browserLanguage: navigator.language,
    formatter: currencyFormatter.numberFormatter
});

/**
 * Initialize currency input handlers on DOM ready
 * Handles formatting for: initial_cash, final_cash, envelope_amount, etc.
 */
function initializeCurrencyInputs() {
    // Fields that support calculator (exclude from auto-formatting)
    // Line 70
    const calculatorFields = new Set([
        'credit_card_total',
        'debit_card_total',
        'bank_transfer_total',
        'expenses',
        'credit_sales_total',
        'credit_payments_collected'
    ]);

    const currencyFieldNames = [
        'initial_cash',
        'final_cash',
        'envelope_amount',
        'credit_card_total',
        'debit_card_total',
        'bank_transfer_total',
        'expenses',
        'credit_sales_total',
        'credit_payments_collected'
    ];

    currencyFieldNames.forEach(fieldName => {
        // Skip calculator-enabled fields completely
        if (calculatorFields.has(fieldName)) {
            console.log(`⚠️ Skipping currency formatter for calculator field: ${fieldName}`);
            return;
        }

        const inputs = document.querySelectorAll(`input[type="text"][name="${fieldName}"], input[type="number"][name="${fieldName}"]`);
        inputs.forEach(input => {
            // On input: keep digits + single decimal point
            input.addEventListener('input', function () {
                let value = this.value;
                const parts = value.split('.');
                const digits = parts[0].replace(/\D/g, '');
                if (parts.length > 1) {
                    const decimals = parts.slice(1).join('').replace(/\D/g, '');
                    this.value = decimals ? digits + '.' + decimals : digits;
                } else {
                    this.value = digits;
                }
            });

            // On blur: format without decimals (Paraguay standard)
            input.addEventListener('blur', function () {
                if (this.value) {
                    const num = parseInt(this.value.replace(/\D/g, '')) || 0;
                    this.value = currencyFormatter.formatForLocale(num);
                }
            });
        });
    });
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeCurrencyInputs);
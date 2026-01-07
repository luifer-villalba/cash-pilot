// File: static/js/currency-formatter.js

/**
 * Locale-aware currency formatter for CashPilot
 * Supports multiple locales but maintains es-PY currency always
 */

function CurrencyFormatter() {
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
CurrencyFormatter.prototype.format = function(value) {
    if (!value && value !== 0) return 'Gs 0';
    return 'Gs ' + this.numberFormatter.format(Math.abs(value));
};

/**
 * Format for locale-specific input display
 * Used in real-time preview updates
 */
CurrencyFormatter.prototype.formatForLocale = function(value) {
    if (!value && value !== 0) return '0';
    return this.numberFormatter.format(Math.abs(value));
};

/**
 * Get locale-specific decimal separator
 * es-PY → ","
 * en-US → "."
 */
CurrencyFormatter.prototype.getDecimalSeparator = function() {
    return (1.1).toLocaleString(this.locale === 'es' ? 'es-PY' : 'en-US').substring(1, 2);
};

// Initialize global formatter instance
var currencyFormatter = new CurrencyFormatter();

/**
 * Safely evaluate basic math expressions (+, -, *, /)
 * Compatible with ES5 and Windows 7
 * Only allows numbers and basic operators for security
 * Examples: "50000+100000" → 150000, "100*3" → 300, "1000-200" → 800, "2+3*4" → 14
 */
function parseCalculator(value) {
    if (!value) return 0;
    
    // Remove all whitespace
    var expr = value.toString().replace(/\s/g, '');
    if (!expr) return 0;
    
    // Validate: only allow digits, decimal point, and operators +, -, *, /
    // This prevents code injection
    if (!/^[\d+\-*/.]+$/.test(expr)) {
        // If invalid characters, just parse as number
        return parseInt(value.replace(/\D/g, '')) || 0;
    }
    
    // Check if it's a simple number (no operators)
    if (!/[\+\-\*\/]/.test(expr)) {
        return parseInt(expr.replace(/[^\d]/g, '')) || 0;
    }
    
    // Parse and evaluate expression safely
    try {
        // Tokenize: split into numbers and operators
        // Use regex to match numbers (including decimals) and operators
        var tokens = expr.match(/(\d+\.?\d*|[\+\-\*\/])/g);
        if (!tokens || tokens.length < 3) {
            // Need at least: number, operator, number
            return parseInt(value.replace(/\D/g, '')) || 0;
        }
        
        // First pass: handle multiplication and division (left to right)
        var i = 0;
        while (i < tokens.length) {
            if (tokens[i] === '*' || tokens[i] === '/') {
                if (i === 0 || i === tokens.length - 1) {
                    // Invalid: operator at start or end
                    return parseInt(value.replace(/\D/g, '')) || 0;
                }
                
                var left = parseFloat(tokens[i - 1]) || 0;
                var operator = tokens[i];
                var right = parseFloat(tokens[i + 1]) || 0;
                var result;
                
                if (operator === '*') {
                    result = left * right;
                } else {
                    result = right !== 0 ? left / right : 0;
                }
                
                // Replace the three tokens with the result
                tokens.splice(i - 1, 3, result.toString());
                i = i - 1; // Stay at same position to check next
            } else {
                i++;
            }
        }
        
        // Second pass: handle addition and subtraction (left to right)
        i = 0;
        while (i < tokens.length) {
            if (tokens[i] === '+' || tokens[i] === '-') {
                if (i === 0 || i === tokens.length - 1) {
                    // Invalid: operator at start or end
                    return parseInt(value.replace(/\D/g, '')) || 0;
                }
                
                var left = parseFloat(tokens[i - 1]) || 0;
                var operator = tokens[i];
                var right = parseFloat(tokens[i + 1]) || 0;
                var result;
                
                if (operator === '+') {
                    result = left + right;
                } else {
                    result = left - right;
                }
                
                // Replace the three tokens with the result
                tokens.splice(i - 1, 3, result.toString());
                i = i - 1; // Stay at same position to check next
            } else {
                i++;
            }
        }
        
        // Final result should be the only token left
        if (tokens.length !== 1) {
            return parseInt(value.replace(/\D/g, '')) || 0;
        }
        
        var finalResult = parseFloat(tokens[0]) || 0;
        // Return positive integer (no decimals for currency)
        return Math.floor(Math.abs(finalResult));
    } catch (e) {
        // If anything goes wrong, fall back to simple number parsing
        return parseInt(value.replace(/\D/g, '')) || 0;
    }
}

/**
 * Initialize currency input handlers on DOM ready
 * Handles formatting for: initial_cash, final_cash, envelope_amount, etc.
 */
function initializeCurrencyInputs() {
    // Fields that support calculator (allow math expressions)
    var calculatorFields = new Set([
        'credit_card_total',
        'debit_card_total',
        'credit_sales_total',
        'credit_payments_collected',
        'envelope_amount'
    ]);

    var currencyFieldNames = [
        'initial_cash',
        'final_cash',
        'envelope_amount',
        'credit_card_total',
        'debit_card_total',
        'credit_sales_total',
        'credit_payments_collected'
    ];

    currencyFieldNames.forEach(function(fieldName) {
        var selector = 'input[type="text"][name="' + fieldName + '"], input[type="number"][name="' + fieldName + '"]';
        var inputs = document.querySelectorAll(selector);
        inputs.forEach(function(input) {
            // Skip if already processed (avoid duplicates)
            if (input.dataset.calculatorInitialized === 'true') {
                return;
            }
            
            if (calculatorFields.has(fieldName)) {
                // Mark as calculator field to prevent other scripts from interfering
                input.setAttribute('data-calculator-field', 'true');
                input.dataset.calculatorInitialized = 'true';
                
                // Calculator-enabled fields: allow operators +, -, *, /
                // Use capture phase to ensure this runs before other handlers
                input.addEventListener('input', function (e) {
                    // Allow digits, operators, and decimal point
                    var newValue = this.value.replace(/[^\d+\-*/. ]/g, '');
                    if (newValue !== this.value) {
                        this.value = newValue;
                    }
                }, true); // Capture phase runs first

                // On blur: evaluate expression and format result
                input.addEventListener('blur', function (e) {
                    if (this.value) {
                        var result = parseCalculator(this.value);
                        this.value = currencyFormatter.formatForLocale(result);
                    }
                }, true); // Capture phase runs first
            } else {
                // Regular fields: only digits + single decimal point
                input.addEventListener('input', function () {
                    var value = this.value;
                    var parts = value.split('.');
                    var digits = parts[0].replace(/\D/g, '');
                    if (parts.length > 1) {
                        var decimals = parts.slice(1).join('').replace(/\D/g, '');
                        this.value = decimals ? digits + '.' + decimals : digits;
                    } else {
                        this.value = digits;
                    }
                });

                // On blur: format without decimals (Paraguay standard)
                input.addEventListener('blur', function () {
                    if (this.value) {
                        var num = parseInt(this.value.replace(/\D/g, '')) || 0;
                        this.value = currencyFormatter.formatForLocale(num);
                    }
                });
            }
        });
    });
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeCurrencyInputs);

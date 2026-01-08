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
        if (!tokens) {
            return parseInt(value.replace(/\D/g, '')) || 0;
        }
        
        // Handle unary minus: merge "-" with following number when it denotes a negative value
        // This handles cases like "5+-3" or "-10+5" correctly
        var processedTokens = [];
        var j = 0;
        while (j < tokens.length) {
            var current = tokens[j];
            // Check if this is a unary minus (at start or after an operator)
            if (current === '-' && (j === 0 || /[+\-*/]/.test(tokens[j - 1]))) {
                // Unary minus at start or after another operator
                var next = tokens[j + 1];
                if (next && /^\d+\.?\d*$/.test(next)) {
                    // Merge minus with next number
                    processedTokens.push('-' + next);
                    j += 2; // Skip both tokens
                    continue;
                }
            }
            processedTokens.push(current);
            j++;
        }
        tokens = processedTokens;
        
        // If expression reduces to a single numeric token, return it directly
        if (tokens.length === 1 && /^-?\d+(\.\d+)?$/.test(tokens[0])) {
            var singleResult = parseFloat(tokens[0]) || 0;
            return Math.floor(Math.abs(singleResult));
        }
        
        if (tokens.length < 3) {
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
                
                // Replace the three tokens (left, operator, right) with the result
                // After splice, the result is now at position i-1, and we want to check
                // if there are more operators at the same position (since we replaced 3 with 1)
                tokens.splice(i - 1, 3, result.toString());
                // Don't increment i - we need to check the result position again
                // in case there are consecutive operators (e.g., 2*3*4)
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
                
                // Replace the three tokens (left, operator, right) with the result
                tokens.splice(i - 1, 3, result.toString());
                // Don't increment i - check the result position again
            } else {
                i++;
            }
        }
        
        // Final result should be the only token left
        if (tokens.length !== 1) {
            return parseInt(value.replace(/\D/g, '')) || 0;
        }
        
        var finalResult = parseFloat(tokens[0]) || 0;
        // Currency amounts are treated as non-negative for this application.
        // If expression evaluates to negative, coerce to positive and log warning.
        var coercedResult = Math.floor(Math.abs(finalResult));
        if (finalResult < 0) {
            // Log warning in development (IE11 compatible console.warn)
            if (typeof console !== 'undefined' && console.warn) {
                console.warn('parseCalculator: negative result coerced to positive', {
                    expression: value,
                    evaluatedResult: finalResult,
                    returnedValue: coercedResult
                });
            }
        }
        return coercedResult;
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
        'card_total',
        'credit_sales_total',
        'credit_payments_collected',
        'envelope_amount'
    ]);

    var currencyFieldNames = [
        'initial_cash',
        'final_cash',
        'envelope_amount',
        'card_total',
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
                input.addEventListener('input', function () {
                    // Allow digits, operators, and decimal point
                    var newValue = this.value.replace(/[^\d+\-*/. ]/g, '');
                    if (newValue !== this.value) {
                        this.value = newValue;
                    }
                });

                // On blur: evaluate expression and format result
                // Use setTimeout to ensure this runs after other blur handlers
                input.addEventListener('blur', function () {
                    var self = this;
                    setTimeout(function() {
                        if (self.value) {
                            var originalValue = self.value;
                            var result = parseCalculator(originalValue);
                            // Format with thousand separators
                            var formatted = currencyFormatter.formatForLocale(result);
                            self.value = formatted;
                            
                            // Trigger change event if value was modified
                            if (originalValue !== formatted) {
                                // Dispatch input event for other listeners (IE11 compatible)
                                var event;
                                if (typeof Event === 'function') {
                                    event = new Event('input', { bubbles: true });
                                } else {
                                    event = document.createEvent('Event');
                                    event.initEvent('input', true, true);
                                }
                                self.dispatchEvent(event);
                            }
                        }
                    }, 0);
                });
            } else {
                // Mark regular fields as initialized to prevent duplicate handlers
                input.dataset.calculatorInitialized = 'true';
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

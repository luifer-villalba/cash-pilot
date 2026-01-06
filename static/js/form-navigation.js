// File: static/js/form-navigation.js

/**
 * Prevent accidental form submission on Enter key
 * - Enter moves focus to next field (like Tab)
 * - Forms submit only via button click or Ctrl+Enter
 * - Textareas allow Enter for multi-line input
 */
document.addEventListener('DOMContentLoaded', function() {
  document.addEventListener('keydown', function(e) {
    var target = e.target;

    // Allow Enter on textareas (multi-line input)
    if (target.tagName === 'TEXTAREA') {
      return;
    }

    // Allow Enter on submit buttons
    if (target.type === 'submit') {
      return;
    }

    // Allow Ctrl+Enter to submit form
    if (e.key === 'Enter' && e.ctrlKey) {
      var form = target.closest('form');
      if (form) {
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else {
          form.submit();
        }
      }
      return;
    }

    // Prevent Enter on input/select fields
    if (e.key === 'Enter' && (target.tagName === 'INPUT' || target.tagName === 'SELECT')) {
      e.preventDefault();

      // Move focus to next focusable element
      var form = target.closest('form');
      if (form) {
        var focusableElements = Array.from(
          form.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])')
        ).filter(function(el) {
          return el.offsetParent !== null;
        });

        var currentIndex = focusableElements.indexOf(target);
        var nextElement = focusableElements[currentIndex + 1];

        if (nextElement) {
          nextElement.focus();
        }
      }
    }
  });
});

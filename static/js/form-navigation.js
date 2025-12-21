// File: static/js/form-navigation.js

/**
 * Prevent accidental form submission on Enter key
 * - Enter moves focus to next field (like Tab)
 * - Forms submit only via button click or Ctrl+Enter
 * - Textareas allow Enter for multi-line input
 */
document.addEventListener('DOMContentLoaded', function() {
  document.addEventListener('keydown', function(e) {
    const target = e.target;

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
      const form = target.closest('form');
      if (form) {
        form.requestSubmit();
      }
      return;
    }

    // Prevent Enter on input/select fields
    if (e.key === 'Enter' && (target.tagName === 'INPUT' || target.tagName === 'SELECT')) {
      e.preventDefault();

      // Move focus to next focusable element
      const form = target.closest('form');
      if (form) {
        const focusableElements = Array.from(
          form.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])')
        ).filter(el => el.offsetParent !== null);

        const currentIndex = focusableElements.indexOf(target);
        const nextElement = focusableElements[currentIndex + 1];

        if (nextElement) {
          nextElement.focus();
        }
      }
    }
  });
});
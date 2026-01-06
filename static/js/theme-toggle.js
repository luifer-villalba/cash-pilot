/**
 * Theme toggle functionality for CashPilot
 * Persists preference to localStorage
 */

function initializeThemeToggle() {
    var toggleBtn = document.getElementById('theme-toggle');
    var sunIcon = document.getElementById('theme-icon-sun');
    var moonIcon = document.getElementById('theme-icon-moon');

    if (!toggleBtn || !sunIcon || !moonIcon) return;

    function updateIcons(theme) {
        if (theme === 'dark') {
            // Dark mode: show sun icon (to switch to light)
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        } else {
            // Light mode: show moon icon (to switch to dark)
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    }

    toggleBtn.addEventListener('click', function() {
        var current = document.documentElement.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateIcons(next);
    });

    // Set initial icon based on saved theme
    var saved = localStorage.getItem('theme') || 'light';
    updateIcons(saved);
}

document.addEventListener('DOMContentLoaded', initializeThemeToggle);

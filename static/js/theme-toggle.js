/**
 * Theme toggle functionality for CashPilot
 * Persists preference to localStorage
 */

function initializeThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    if (!toggleBtn || !themeIcon) return;

    toggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        themeIcon.textContent = next === 'dark' ? '☀️' : '🌙';
    });

    // Set initial icon based on saved theme
    const saved = localStorage.getItem('theme') || 'light';
    themeIcon.textContent = saved === 'dark' ? '☀️' : '🌙';
}

document.addEventListener('DOMContentLoaded', initializeThemeToggle);
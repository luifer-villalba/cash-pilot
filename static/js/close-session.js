// File: static/js/close-session.js

document.addEventListener('DOMContentLoaded', function () {
    // Prefill closed time
    const closedTimeInput = document.getElementById('closed-time');
    if (closedTimeInput && !closedTimeInput.value) {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        closedTimeInput.value = `${hours}:${minutes}`;
    }
});
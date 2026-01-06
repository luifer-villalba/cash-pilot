// File: static/js/close-session.js

document.addEventListener('DOMContentLoaded', function () {
    // Prefill closed time
    var closedTimeInput = document.getElementById('closed-time');
    if (closedTimeInput && !closedTimeInput.value) {
        var now = new Date();
        var hours = String(now.getHours()).padStart(2, '0');
        var minutes = String(now.getMinutes()).padStart(2, '0');
        closedTimeInput.value = hours + ':' + minutes;
    }
});

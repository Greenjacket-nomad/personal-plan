// Date/Time Formatting Utilities
// Standardizes date formatting throughout the application

// Format date as relative time for recent items, absolute for older
function formatDate(dateString, options = {}) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    // Use relative time for recent items (within last 7 days)
    if (options.useRelative !== false && diffDays < 7) {
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
    }
    
    // Use absolute date format
    const format = options.format || 'MM/DD/YYYY';
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    if (format === 'MM/DD/YYYY') {
        return `${month}/${day}/${year}`;
    } else if (format === 'YYYY-MM-DD') {
        return `${year}-${month}-${day}`;
    } else if (format === 'full') {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];
        return `${monthNames[date.getMonth()]} ${day}, ${year}`;
    } else if (format === 'datetime') {
        return `${month}/${day}/${year} ${hours}:${minutes}`;
    }
    
    return `${month}/${day}/${year}`;
}

// Format time duration
function formatDuration(hours) {
    if (hours < 1) {
        const mins = Math.round(hours * 60);
        return `${mins}m`;
    } else if (hours < 24) {
        return `${hours.toFixed(1)}h`;
    } else {
        const days = Math.floor(hours / 24);
        const remainingHours = hours % 24;
        if (remainingHours > 0) {
            return `${days}d ${remainingHours.toFixed(1)}h`;
        }
        return `${days}d`;
    }
}

// Update all date displays on page load
document.addEventListener('DOMContentLoaded', function() {
    // Find all elements with data-date attribute
    document.querySelectorAll('[data-date]').forEach(el => {
        const dateString = el.getAttribute('data-date');
        const format = el.getAttribute('data-date-format') || 'MM/DD/YYYY';
        const useRelative = el.getAttribute('data-date-relative') !== 'false';
        el.textContent = formatDate(dateString, { format, useRelative });
    });
    
    // Find all elements with data-duration attribute
    document.querySelectorAll('[data-duration]').forEach(el => {
        const hours = parseFloat(el.getAttribute('data-duration'));
        el.textContent = formatDuration(hours);
    });
});

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.formatDate = formatDate;
    window.formatDuration = formatDuration;
}


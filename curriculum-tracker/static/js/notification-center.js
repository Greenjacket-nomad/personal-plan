/**
 * Notification Center
 * Handles notification display, marking as read, and real-time updates
 */

let notifications = [];
let unreadCount = 0;

function toggleNotificationCenter() {
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) return;
    
    dropdown.classList.toggle('hidden');
    
    if (!dropdown.classList.contains('hidden')) {
        loadNotifications();
    }
}

function loadNotifications() {
    // Fetch notifications from API
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            notifications = data.notifications || [];
            unreadCount = data.unread_count || 0;
            renderNotifications();
            updateBadge();
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            // Use mock data for demo
            notifications = getMockNotifications();
            unreadCount = notifications.filter(n => !n.read).length;
            renderNotifications();
            updateBadge();
        });
}

function renderNotifications() {
    const list = document.getElementById('notification-list');
    if (!list) return;
    
    if (notifications.length === 0) {
        list.innerHTML = `
            <div class="notification-empty">
                <i class="fas fa-bell-slash"></i>
                <p>No notifications</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = notifications.map(notification => {
        const iconClass = getNotificationIconClass(notification.type);
        const icon = getNotificationIcon(notification.type);
        const timeAgo = formatTimeAgo(notification.created_at);
        
        return `
            <div class="notification-item ${notification.read ? '' : 'unread'}" 
                 onclick="handleNotificationClick(${notification.id})"
                 data-notification-id="${notification.id}">
                <div class="notification-icon ${iconClass}">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${escapeHtml(notification.title)}</div>
                    <div class="notification-message">${escapeHtml(notification.message)}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
            </div>
        `;
    }).join('');
}

function handleNotificationClick(notificationId) {
    // Mark as read
    markNotificationRead(notificationId);
    
    // Navigate to related item if applicable
    const notification = notifications.find(n => n.id === notificationId);
    if (notification && notification.link) {
        window.location.href = notification.link;
    }
}

function markNotificationRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            // Update local state
            const notification = notifications.find(n => n.id === notificationId);
            if (notification) {
                notification.read = true;
                unreadCount = Math.max(0, unreadCount - 1);
                renderNotifications();
                updateBadge();
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
            // Update locally anyway
            const notification = notifications.find(n => n.id === notificationId);
            if (notification) {
                notification.read = true;
                unreadCount = Math.max(0, unreadCount - 1);
                renderNotifications();
                updateBadge();
            }
        });
}

function markAllNotificationsRead() {
    fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            notifications.forEach(n => n.read = true);
            unreadCount = 0;
            renderNotifications();
            updateBadge();
        })
        .catch(error => {
            console.error('Error marking all as read:', error);
            // Update locally anyway
            notifications.forEach(n => n.read = true);
            unreadCount = 0;
            renderNotifications();
            updateBadge();
        });
}

function updateBadge() {
    const badge = document.getElementById('notification-badge-count');
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        } else {
            badge.textContent = '';
        }
    }
}

function getNotificationIconClass(type) {
    const classMap = {
        'success': 'success',
        'info': 'info',
        'warning': 'warning',
        'error': 'error'
    };
    return classMap[type] || 'info';
}

function getNotificationIcon(type) {
    const iconMap = {
        'success': 'fa-check-circle',
        'info': 'fa-info-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-exclamation-circle',
        'milestone': 'fa-trophy',
        'reminder': 'fa-clock',
        'update': 'fa-bell'
    };
    return iconMap[type] || 'fa-bell';
}

function formatTimeAgo(dateString) {
    if (!dateString) return 'Just now';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getMockNotifications() {
    return [
        {
            id: 1,
            type: 'success',
            title: 'Milestone Achieved!',
            message: 'You completed Phase 1 of your curriculum',
            created_at: new Date(Date.now() - 3600000).toISOString(),
            read: false,
            link: '/reports'
        },
        {
            id: 2,
            type: 'info',
            title: 'New Resource Added',
            message: 'A new resource was added to your curriculum',
            created_at: new Date(Date.now() - 7200000).toISOString(),
            read: false,
            link: '/resources'
        },
        {
            id: 3,
            type: 'reminder',
            title: 'Daily Check-in',
            message: "Don't forget to log your learning hours today",
            created_at: new Date(Date.now() - 86400000).toISOString(),
            read: true,
            link: '/dashboard'
        }
    ];
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const center = document.querySelector('.notification-center');
    const dropdown = document.getElementById('notification-dropdown');
    
    if (center && dropdown && !center.contains(event.target)) {
        dropdown.classList.add('hidden');
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('notification-bell-btn')) {
        loadNotifications();
        
        // Poll for new notifications every 30 seconds
        setInterval(loadNotifications, 30000);
    }
});

// Export for global access
window.toggleNotificationCenter = toggleNotificationCenter;
window.markAllNotificationsRead = markAllNotificationsRead;
window.handleNotificationClick = handleNotificationClick;


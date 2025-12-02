// Activity Page JavaScript
// Handles chronological grouping, filtering, and visual hierarchy

function groupActivitiesByDate(activities) {
    const groups = {
        'Today': [],
        'Yesterday': [],
        'This Week': [],
        'Last Week': [],
        'This Month': [],
        'Older': []
    };
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    const twoWeeksAgo = new Date(today);
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14);
    const monthAgo = new Date(today);
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    
    activities.forEach(activity => {
        if (!activity.created_at) return;
        const activityDate = new Date(activity.created_at);
        const activityDay = new Date(activityDate.getFullYear(), activityDate.getMonth(), activityDate.getDate());
        
        if (activityDay.getTime() === today.getTime()) {
            groups['Today'].push(activity);
        } else if (activityDay.getTime() === yesterday.getTime()) {
            groups['Yesterday'].push(activity);
        } else if (activityDate >= weekAgo) {
            groups['This Week'].push(activity);
        } else if (activityDate >= twoWeeksAgo) {
            groups['Last Week'].push(activity);
        } else if (activityDate >= monthAgo) {
            groups['This Month'].push(activity);
        } else {
            groups['Older'].push(activity);
        }
    });
    
    return groups;
}

function createActivityItem(activity, index = 0) {
    const item = document.createElement('div');
    const action = (activity.action || '').toLowerCase();
    const isUserAction = !action.includes('system') && !action.includes('auto');
    
    let iconClass = 'fa-bolt';
    let iconType = 'edit';
    if (action.includes('complete')) {
        iconClass = 'fa-check-circle';
        iconType = 'complete';
    } else if (action.includes('hours') || action.includes('log')) {
        iconClass = 'fa-clock';
        iconType = 'hours';
    } else if (action.includes('metric')) {
        iconClass = 'fa-trophy';
        iconType = 'metric';
    } else if (action.includes('reset')) {
        iconClass = 'fa-redo';
        iconType = 'edit';
    }
    
    const created = activity.created_at ? new Date(activity.created_at) : new Date();
    const timeStr = formatRelativeTime(created);
    
    item.className = `activity-item`;
    item.onclick = () => {
        // Navigate to related item if applicable
        if (activity.resource_id) {
            window.location.href = `/resources#resource-${activity.resource_id}`;
        }
    };
    
    const actionText = (activity.action || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    item.innerHTML = `
        <div class="activity-item-card">
            <div class="activity-item-header">
                <div class="activity-icon ${iconType}">
                    <i class="fas ${iconClass}"></i>
                </div>
                <div class="activity-title">${escapeHtml(actionText)}</div>
            </div>
            ${activity.details ? `<div class="activity-description">${escapeHtml(activity.details)}</div>` : ''}
            <div class="activity-meta">
                <div class="activity-timestamp">
                    <i class="fas fa-clock"></i>
                    <span>${timeStr}</span>
                </div>
                ${!isUserAction ? '<span class="text-xs">(System)</span>' : ''}
            </div>
        </div>
    `;
    
    return item;
}

function formatRelativeTime(date) {
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

function getActivityClass(action) {
    const act = action.toLowerCase();
    if (act.includes('complete')) return 'activity-complete';
    if (act.includes('hours') || act.includes('log')) return 'activity-hours';
    if (act.includes('reset')) return 'activity-reset';
    return 'activity-default';
}

function renderActivityGroups(groups, filter = 'all') {
    const timeline = document.getElementById('activity-timeline');
    if (!timeline) return;
    
    timeline.innerHTML = '';
    
    let globalIndex = 0;
    
    Object.keys(groups).forEach(groupName => {
        let activities = groups[groupName];
        
        // Apply filter
        if (filter !== 'all') {
            activities = activities.filter(a => {
                const action = (a.action || '').toLowerCase();
                if (filter === 'complete') return action.includes('complete');
                if (filter === 'hours') return action.includes('hours') || action.includes('log');
                if (filter === 'metric') return action.includes('metric');
                return true;
            });
        }
        
        if (activities.length === 0) return;
        
        const groupDiv = document.createElement('div');
        groupDiv.className = 'activity-timeline-group';
        
        // Date header with timeline node
        const header = document.createElement('div');
        header.className = 'activity-group-header';
        header.innerHTML = `
            <div class="activity-group-title">
                <span>${groupName}</span>
            </div>
            <div class="activity-group-count">${activities.length}</div>
        `;
        groupDiv.appendChild(header);
        
        // Activity items with alternating placement
        activities.forEach((activity, idx) => {
            const item = createActivityItem(activity, globalIndex);
            // Alternate between left and right on desktop
            if (window.innerWidth >= 768) {
                item.classList.add(idx % 2 === 0 ? 'timeline-item-left' : 'timeline-item-right');
            }
            groupDiv.appendChild(item);
            globalIndex++;
        });
        
        timeline.appendChild(groupDiv);
    });
}

function filterActivity(filter) {
    // Update active filter chip
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.classList.remove('active');
    });
    const activeChip = document.querySelector(`[data-filter="${filter}"]`);
    if (activeChip) {
        activeChip.classList.add('active');
    }
    
    // Re-render with filter
    if (window.activityLogs && window.activityLogs.length > 0) {
        const groups = groupActivitiesByDate(window.activityLogs);
        renderActivityGroups(groups, filter);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (window.activityLogs && window.activityLogs.length > 0) {
        const groups = groupActivitiesByDate(window.activityLogs);
        renderActivityGroups(groups);
    }
});

// Export for global access
window.filterActivity = filterActivity;


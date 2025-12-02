// UI Interaction Functions

// CSRF Protection Helper
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

// Dark Mode Functions
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon();
}

function updateThemeIcon() {
    const theme = document.documentElement.getAttribute('data-theme');
    const icon = document.querySelector('.theme-icon');
    if (icon) {
        icon.innerHTML = theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }
}

// Initialize theme icon on load
document.addEventListener('DOMContentLoaded', function() {
    updateThemeIcon();
});

// Log Time Collapsible
function toggleLogTime() {
    const content = document.getElementById('log-time-content');
    const chevron = document.getElementById('log-time-chevron');
    if (content.classList.contains('hidden-field')) {
        content.classList.remove('hidden-field');
        chevron.style.transform = 'rotate(180deg)';
        localStorage.setItem('logTimeExpanded', 'true');
    } else {
        content.classList.add('hidden-field');
        chevron.style.transform = 'rotate(0deg)';
        localStorage.setItem('logTimeExpanded', 'false');
    }
}

// Journal Widget Collapsible
function toggleJournalWidget() {
    const content = document.getElementById('journal-widget-content');
    const chevron = document.getElementById('journal-chevron');
    if (content.classList.contains('hidden-field')) {
        content.classList.remove('hidden-field');
        chevron.style.transform = 'rotate(180deg)';
        localStorage.setItem('journalWidgetExpanded', 'true');
    } else {
        content.classList.add('hidden-field');
        chevron.style.transform = 'rotate(0deg)';
        localStorage.setItem('journalWidgetExpanded', 'false');
    }
}

// Curriculum Day Fields Toggle
function toggleCurriculumDayFields() {
    const checkbox = document.getElementById('link-to-day');
    const fields = document.getElementById('curriculum-day-fields');
    if (checkbox.checked) {
        fields.classList.remove('hidden-field');
    } else {
        fields.classList.add('hidden-field');
    }
}

// Success Metrics Expansion
function toggleMetricDetails(element) {
    const card = element.closest('.success-metric-card');
    const details = card.querySelector('.metric-details');
    const chevron = card.querySelector('.fa-chevron-down');
    
    if (details.classList.contains('hidden')) {
        details.classList.remove('hidden');
        if (chevron) chevron.style.transform = 'rotate(180deg)';
        
        // Load linked resources if not already loaded
        if (details.innerHTML.includes('Brewing') || details.innerHTML.includes('No linked resources yet')) {
            const metricText = card.dataset.metric;
            
            // Get resources linked to this metric from the API (by metric_text only, works for any day)
            const apiUrl = `/api/metric-resources?metric_text=${encodeURIComponent(metricText)}`;
            fetch(apiUrl)
                .then(r => r.json())
                .then(data => {
                    if (data.resources && data.resources.length > 0) {
                        let html = '<p class="text-sm font-semibold text-primary mb-2">Linked Resources:</p><ul class="space-y-1">';
                        data.resources.forEach(r => {
                            const statusIcon = r.status === 'complete' ? '<i class="fas fa-check-circle text-success"></i>' : 
                                              r.status === 'in_progress' ? '<i class="fas fa-circle-notch text-warning"></i>' : 
                                              '<i class="far fa-circle text-muted"></i>';
                            html += `<li class="text-sm text-secondary flex items-center gap-2">
                                ${statusIcon}
                                <a href="/view/${r.phase_index}/${r.week}#resource-${r.id}" class="hover:text-accent">
                                    ${r.title} <span class="text-xs text-muted">(Week ${r.week}, Day ${r.day})</span>
                                </a>
                            </li>`;
                        });
                        html += '</ul>';
                        details.innerHTML = html;
                    } else {
                        details.innerHTML = '<p class="text-sm text-secondary">No linked resources yet</p>';
                    }
                })
                .catch(err => {
                    console.error('Error loading resources:', err);
                    details.innerHTML = '<p class="text-sm text-error">Oops, something went sideways loading resources</p>';
                });
        }
    } else {
        details.classList.add('hidden');
        if (chevron) chevron.style.transform = 'rotate(0deg)';
    }
}

// Mobile menu toggle
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Back button function
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// Generate breadcrumbs dynamically
function generateBreadcrumbs() {
    const breadcrumbs = document.getElementById('breadcrumbs');
    if (!breadcrumbs) return;
    
    const path = window.location.pathname;
    const parts = path.split('/').filter(Boolean);
    
    // Dashboard is the root
    if (parts.length === 0) {
        breadcrumbs.innerHTML = '<span>Dashboard</span>';
        return;
    }
    
    let html = '<a href="/" class="hover:text-accent">Dashboard</a>';
    
    // Map routes to display names
    const routeNames = {
        'resources': 'Curriculum',
        'curriculum': 'Curriculum',
        'journal': 'Journal',
        'calendar': 'Calendar',
        'reports': 'Reports',
        'activity': 'Activity',
        'view': 'Week View',
        'edit': 'Edit'
    };
    
    let currentPath = '';
    parts.forEach((part, index) => {
        currentPath += '/' + part;
        
        // Special handling for calendar route: /calendar/2025/1
        if (part === 'calendar' && parts.length > index + 1) {
            const year = parts[index + 1];
            const month = parts[index + 2];
            if (month) {
                const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                                   'July', 'August', 'September', 'October', 'November', 'December'];
                const monthName = monthNames[parseInt(month) - 1] || month;
                html += ` <i class="fas fa-chevron-right text-xs"></i> <span>${monthName} ${year}</span>`;
                return; // Skip next two parts
            }
        }
        
        // Special handling for view route: /view/0/2
        if (part === 'view' && parts.length > index + 1) {
            const phaseIndex = parseInt(parts[index + 1]);
            const week = parts[index + 2];
            if (week) {
                html += ` <i class="fas fa-chevron-right text-xs"></i> <span>Phase ${phaseIndex + 1} > Week ${week}</span>`;
                return; // Skip next two parts
            }
        }
        
        // Skip if already handled
        if (index > 0 && parts[index - 1] === 'calendar' && (part.match(/^\d+$/) || index === 1)) {
            return;
        }
        if (index > 0 && parts[index - 1] === 'view' && part.match(/^\d+$/)) {
            return;
        }
        
        const name = routeNames[part] || part.charAt(0).toUpperCase() + part.slice(1);
        
        if (index === parts.length - 1) {
            // Last item - not clickable
            html += ` <i class="fas fa-chevron-right text-xs"></i> <span>${name}</span>`;
        } else {
            // Intermediate item - clickable
            html += ` <i class="fas fa-chevron-right text-xs"></i> <a href="${currentPath}" class="hover:text-accent">${name}</a>`;
        }
    });
    
    breadcrumbs.innerHTML = html;
}

// Navigate week function (for sidebar navigation)
function navigateWeek(direction) {
    // Get current phase and week from the page
    const phaseElement = document.querySelector('.phase-current');
    if (!phaseElement) return;
    
    const form = phaseElement.closest('form');
    if (!form) return;
    
    const currentPhase = parseInt(form.action.match(/\/jump-to-phase\/(\d+)/)?.[1] || '0');
    
    // This would need to be passed from the template or fetched
    // For now, we'll use the API endpoint
    fetch('/api/navigate-week', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            direction: direction,
            current_phase: currentPhase,
            current_week: parseInt(document.querySelector('[data-current-week]')?.dataset.currentWeek || '1')
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Reload page to show new week
            window.location.reload();
        }
    })
    .catch(err => {
        console.error('Error navigating week:', err);
    });
}

// Toast Notification Functions
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${iconMap[type] || iconMap.info}"></i>
        </div>
        <div class="toast-content">${message}</div>
        <button class="toast-close" onclick="removeToast(this.parentElement)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after duration
    setTimeout(() => {
        removeToast(toast);
    }, duration);
}

function removeToast(toast) {
    if (!toast) return;
    toast.classList.add('removing');
    setTimeout(() => {
        toast.remove();
    }, 300);
}

// Scroll to resource function
function scrollToResource(resourceId) {
    const targetElement = document.getElementById(`resource-${resourceId}`);
    if (targetElement) {
        targetElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
        targetElement.classList.add('highlight-flash');
        setTimeout(() => {
            targetElement.classList.remove('highlight-flash');
        }, 2000);
    }
}

// Initialize UI on page load
document.addEventListener('DOMContentLoaded', function() {
    generateBreadcrumbs();
    
    // Handle scroll-to-hash on page load (for Continue button, metric links, and calendar)
    if (window.location.hash.startsWith('#resource-')) {
        const resourceId = window.location.hash.replace('#resource-', '');
        setTimeout(() => {
            scrollToResource(resourceId);
        }, 100);
    } else if (window.location.hash === '#week-calendar-view') {
        // Scroll to calendar view
        setTimeout(() => {
            const element = document.getElementById('week-calendar-view');
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    }
    
    // Log Time - default collapsed
    const logTimeExpanded = localStorage.getItem('logTimeExpanded') === 'true';
    const logTimeContent = document.getElementById('log-time-content');
    const logTimeChevron = document.getElementById('log-time-chevron');
    if (logTimeExpanded && logTimeContent) {
        logTimeContent.classList.remove('hidden-field');
        if (logTimeChevron) logTimeChevron.style.transform = 'rotate(180deg)';
    }
    
    // Journal Widget - default expanded
    const journalExpanded = localStorage.getItem('journalWidgetExpanded') !== 'false';
    const journalContent = document.getElementById('journal-widget-content');
    const journalChevron = document.getElementById('journal-chevron');
    if (journalExpanded && journalContent) {
        journalContent.classList.remove('hidden-field');
        if (journalChevron) journalChevron.style.transform = 'rotate(180deg)';
    }
});


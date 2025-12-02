// Resource Management Functions

// CSRF Protection Helper
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

let selectedResources = new Set();

function toggleSelection(id, checkbox) {
    if (checkbox.checked) {
        selectedResources.add(id);
    } else {
        selectedResources.delete(id);
    }
    updateBulkBar();
}

function updateBulkBar() {
    const bar = document.getElementById('bulk-actions');
    const count = document.getElementById('selected-count');
    if (selectedResources.size > 0) {
        bar.classList.remove('hidden');
        count.textContent = selectedResources.size;
    } else {
        bar.classList.add('hidden');
    }
}

function bulkAction(action) {
    if (selectedResources.size === 0) return;
    
    const form = document.getElementById('bulk-form');
    document.getElementById('bulk-action').value = action;
    document.getElementById('bulk-ids').value = Array.from(selectedResources).join(',');
    
    if (action === 'delete' && !confirm(`Yeet ${selectedResources.size} resource${selectedResources.size > 1 ? 's' : ''} into the void?`)) {
        return;
    }
    
    form.submit();
}

// Drag-and-Drop Functionality
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.day-resources-container').forEach(container => {
        new Sortable(container, {
            animation: 150,
            handle: '.drag-handle',
            ghostClass: 'bg-blue-100',
            dragClass: 'opacity-50',
            onEnd: function(evt) {
                const resourceId = evt.item.dataset.resourceId;
                const newPosition = evt.newIndex;
                const day = container.dataset.day;
                const week = container.dataset.week;
                const phase = container.dataset.phase;
                
                // Save new order via fetch
                fetch('/reorder', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        resource_id: parseInt(resourceId),
                        new_position: newPosition,
                        day: parseInt(day),
                        week: parseInt(week),
                        phase: parseInt(phase)
                    })
                }).catch(err => console.error('Reorder failed:', err));
            }
        });
    });
});

// Toggle resource status - opens dropdown menu
window.toggleResourceStatus = function(button) {
    const form = button.closest('form');
    const resourceId = form.dataset.resourceId;
    const currentStatus = form.dataset.currentStatus;
    
    // Remove existing menus
    document.querySelectorAll('.status-dropdown').forEach(m => m.remove());
    
    // Create dropdown menu
    const menu = document.createElement('div');
    menu.className = 'status-dropdown absolute z-50 mt-2 bg-secondary rounded-lg shadow-lg border border-primary p-2';
    menu.style.minWidth = '180px';
    
    const statuses = [
        { value: 'not_started', label: 'Not Started', icon: 'far fa-circle', color: 'text-muted' },
        { value: 'in_progress', label: 'In Progress', icon: 'fas fa-circle-notch', color: 'text-warning' },
        { value: 'complete', label: 'Complete', icon: 'fas fa-check-circle', color: 'text-success' },
        { value: 'skipped', label: 'Skipped', icon: 'fas fa-ban', color: 'text-error' }
    ];
    
    let html = '';
    statuses.forEach(status => {
        const isActive = currentStatus === status.value;
        html += `
            <button onclick="setResourceStatus(${resourceId}, '${status.value}', this)" 
                    class="status-menu-item w-full text-left px-3 py-2 rounded flex items-center gap-2 ${isActive ? 'active' : ''}">
                <i class="${status.icon} ${status.color}"></i>
                <span>${status.label}</span>
                ${isActive ? '<i class="fas fa-check ml-auto text-accent"></i>' : ''}
            </button>
        `;
    });
    menu.innerHTML = html;
    
    // Position menu below button
    const rect = button.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = (rect.bottom + 5) + 'px';
    menu.style.left = rect.left + 'px';
    
    // Add to body
    document.body.appendChild(menu);
    
    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && !button.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        }, { once: true });
    }, 0);
};

// Set resource status via API
window.setResourceStatus = function(resourceId, newStatus, menuItem) {
    fetch(`/api/resource/${resourceId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({status: newStatus})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Remove dropdown
            document.querySelectorAll('.status-dropdown').forEach(m => m.remove());
            
            // If marking as complete, celebrate
            if (newStatus === 'complete') {
                const button = document.querySelector(`[data-resource-id="${resourceId}"] button`);
                if (button) {
                    if (typeof animateCheck === 'function') {
                        animateCheck(button);
                    }
                    if (typeof confetti === 'function') {
                        confetti('small');
                    }
                    const card = button.closest('.resource-card') || button.closest('.card');
                    if (card && typeof glowCard === 'function') {
                        glowCard(card);
                    }
                }
            }
            
            // Reload page to show updated status
            location.reload();
        } else {
            if (typeof showToast === 'function') {
                showToast('Error updating status: ' + (data.error || 'Unknown error'), 'error');
            }
        }
    })
    .catch(err => {
        console.error('Error:', err);
        if (typeof showToast === 'function') {
            showToast('Failed to update status', 'error');
        }
    });
};


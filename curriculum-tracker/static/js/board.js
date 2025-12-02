// Curriculum Board - Kanban Board Implementation

// CSRF Protection Helper
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

let boardData = null;
let selectedResources = new Set();
let sortableInstances = {};

// Resource type icons mapping
const RESOURCE_TYPE_ICONS = {
    'video': 'fa-video',
    'article': 'fa-file-alt',
    'docs': 'fa-book',
    'course': 'fa-graduation-cap',
    'project': 'fa-tools',
    'lab': 'fa-flask',
    'tutorial': 'fa-book-open',
    'action': 'fa-check',
    'deliverable': 'fa-box',
    'note': 'fa-pen',
    'link': 'fa-link'
};

// Difficulty colors
const DIFFICULTY_COLORS = {
    'easy': 'var(--success)',
    'medium': 'var(--warning)',
    'hard': 'var(--error)'
};

// ============================================================================
// Core Loading & Rendering
// ============================================================================

async function loadBoard() {
    try {
        const response = await fetch('/api/structure?include_resources=true');
        if (!response.ok) throw new Error('Failed to load board');
        
        boardData = await response.json();
        renderBoard();
        
        // Hide skeleton, show board
        document.getElementById('board-skeleton').classList.add('hidden');
        document.getElementById('board-phases').classList.remove('hidden');
        
        // Initialize Sortable instances after rendering
        setTimeout(() => {
            initializeSortables();
            loadInboxResources();
            setupInlineEditing();
        }, 100);
    } catch (error) {
        console.error('Error loading board:', error);
        showToast('Failed to load board. Please refresh.', 'error');
    }
}

function renderBoard() {
    const container = document.getElementById('board-phases');
    container.innerHTML = '';
    
    if (!boardData || !boardData.phases || boardData.phases.length === 0) {
        container.innerHTML = `
            <div class="empty-state text-center py-12">
                <i class="fas fa-th text-6xl mb-4 text-muted opacity-30"></i>
                <p class="text-lg text-secondary mb-4">No phases yet</p>
                <button onclick="createPhase()" class="btn-primary">
                    <i class="fas fa-plus mr-2"></i>Create First Phase
                </button>
            </div>
        `;
        return;
    }
    
    boardData.phases.forEach(phase => {
        container.appendChild(renderPhase(phase));
    });
}

function renderPhase(phase) {
    const phaseDiv = document.createElement('div');
    phaseDiv.className = 'phase-swimlane';
    phaseDiv.dataset.phaseId = phase.id;
    
    const isCollapsed = localStorage.getItem(`phase-${phase.id}-collapsed`) === 'true';
    
    // Calculate progress
    const progress = calculatePhaseProgress(phase);
    
    phaseDiv.innerHTML = `
        <div class="phase-header glass sticky top-0 z-40 p-4 rounded-lg mb-4" style="border-left: 4px solid ${phase.color || '#6366f1'}">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4 flex-1">
                    <button onclick="togglePhaseCollapse(${phase.id})" class="text-muted hover:text-primary">
                        <i class="fas fa-chevron-${isCollapsed ? 'right' : 'down'}"></i>
                    </button>
                    <div class="editable-title flex-1" data-type="phase" data-id="${phase.id}">
                        <h2 class="text-xl font-bold text-primary inline-block">${escapeHtml(phase.title)}</h2>
                        <input type="text" value="${escapeHtml(phase.title)}" class="hidden w-full text-xl font-bold bg-transparent border-b-2 border-accent outline-none">
                    </div>
                </div>
                
                <div class="flex items-center gap-4">
                    <div class="progress-bar-container flex items-center gap-2 min-w-[200px]">
                        <div class="flex-1 h-2 bg-tertiary rounded-full overflow-hidden">
                            <div class="h-full bg-accent transition-all" style="width: ${progress.percent}%"></div>
                        </div>
                        <span class="text-sm text-secondary">${progress.completed}/${progress.total}</span>
                    </div>
                    
                    <button onclick="showAddWeek(${phase.id})" class="btn-secondary px-3 py-1 text-sm" aria-label="Add week">
                        <i class="fas fa-plus mr-1"></i>Add Week
                    </button>
                    
                    <button onclick="editPhaseSettings(${phase.id})" class="btn-secondary px-3 py-1 text-sm" aria-label="Edit phase settings">
                        <i class="fas fa-cog"></i>
                    </button>
                </div>
            </div>
        </div>
        
        <div class="phase-content ${isCollapsed ? 'hidden' : ''}">
            <div class="weeks-container flex gap-4 overflow-x-auto pb-4 min-h-[200px]" data-phase-id="${phase.id}">
                ${phase.weeks && phase.weeks.length > 0 
                    ? phase.weeks.map(week => renderWeekHTML(week, phase.id)).join('')
                    : '<div class="empty-state text-center py-8 w-full"><p class="text-secondary">No weeks yet</p></div>'
                }
            </div>
        </div>
    `;
    
    return phaseDiv;
}

function renderWeekHTML(week, phaseId) {
    return `
        <div class="week-column flex-shrink-0 w-72" data-week-id="${week.id}" data-phase-id="${phaseId}">
            <div class="week-header glass p-3 rounded-lg mb-2 flex items-center gap-2">
                <i class="fas fa-grip-vertical drag-handle text-muted cursor-move"></i>
                <div class="editable-title flex-1" data-type="week" data-id="${week.id}">
                    <h3 class="font-semibold text-primary inline-block">${escapeHtml(week.title)}</h3>
                    <input type="text" value="${escapeHtml(week.title)}" class="hidden w-full font-semibold bg-transparent border-b-2 border-accent outline-none">
                </div>
            </div>
            
            <div class="days-container space-y-2" data-week-id="${week.id}">
                ${week.days && week.days.length > 0
                    ? week.days.map(day => renderDayHTML(day, week.id)).join('')
                    : ''
                }
            </div>
            
            <button onclick="showAddDay(${week.id})" class="w-full mt-2 px-3 py-2 text-sm btn-secondary text-center" aria-label="Add day">
                <i class="fas fa-plus mr-1"></i>Add Day
            </button>
        </div>
    `;
}

function renderDayHTML(day, weekId) {
    const resources = day.resources || [];
    return `
        <div class="day-card card p-3" data-day-id="${day.id}" data-week-id="${weekId}">
            <div class="day-header flex items-center justify-between mb-2">
                <div class="editable-title flex-1" data-type="day" data-id="${day.id}">
                    <h4 class="font-medium text-primary text-sm inline-block">${escapeHtml(day.title)}</h4>
                    <input type="text" value="${escapeHtml(day.title)}" class="hidden w-full font-medium text-sm bg-transparent border-b-2 border-accent outline-none">
                </div>
            </div>
            
            <div class="resources-container space-y-1.5 min-h-[40px]" data-day-id="${day.id}">
                ${resources.length > 0
                    ? resources.map(resource => renderResourceHTML(resource, day.id)).join('')
                    : '<div class="empty-state text-center py-4"><p class="text-xs text-muted">No resources</p></div>'
                }
            </div>
            
            <div class="day-footer mt-2 pt-2 border-t border-primary">
                <div class="quick-add-resource hidden" data-day-id="${day.id}">
                    <input type="text" placeholder="Paste URL or type title..." class="w-full text-sm mb-2" id="quick-add-title-${day.id}">
                    <div class="flex gap-2">
                        <select class="text-sm flex-1" id="quick-add-type-${day.id}">
                            <option value="link">Link</option>
                            <option value="video">Video</option>
                            <option value="article">Article</option>
                            <option value="docs">Docs</option>
                            <option value="course">Course</option>
                            <option value="project">Project</option>
                            <option value="lab">Lab</option>
                            <option value="tutorial">Tutorial</option>
                            <option value="action">Action</option>
                            <option value="note">Note</option>
                        </select>
                        <button onclick="createResource(${day.id})" class="btn-primary px-3 py-1 text-sm">
                            <i class="fas fa-check"></i>
                        </button>
                        <button onclick="hideQuickAdd(${day.id})" class="btn-secondary px-3 py-1 text-sm">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <button onclick="showQuickAddResource(${day.id})" class="w-full text-xs text-muted hover:text-accent text-center py-1" aria-label="Add resource">
                    <i class="fas fa-plus mr-1"></i>Add Resource
                </button>
            </div>
        </div>
    `;
}

function renderResourceHTML(resource, dayId) {
    const icon = RESOURCE_TYPE_ICONS[resource.resource_type] || 'fa-link';
    const difficulty = resource.difficulty || 'medium';
    const difficultyColor = DIFFICULTY_COLORS[difficulty] || DIFFICULTY_COLORS.medium;
    const isComplete = resource.status === 'complete';
    const timeDisplay = resource.estimated_minutes 
        ? (resource.estimated_minutes < 60 
            ? `${resource.estimated_minutes}m` 
            : `${(resource.estimated_minutes / 60).toFixed(1)}h`)
        : '';
    
    return `
        <div class="resource-item card p-2 text-sm cursor-pointer hover:border-accent group focus:ring-2 focus:ring-accent focus:outline-none ${isComplete ? 'opacity-60' : ''}" 
             data-resource-id="${resource.id}" 
             data-day-id="${dayId}"
             tabindex="0"
             role="button"
             aria-label="Resource: ${escapeHtml(resource.title)}"
             onclick="handleResourceClick(event, ${resource.id})"
             onkeydown="handleResourceKeydown(event, ${resource.id})">
            <div class="flex items-start gap-2">
                <i class="fas ${icon} text-muted mt-0.5 flex-shrink-0"></i>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="difficulty-dot w-2 h-2 rounded-full flex-shrink-0" style="background: ${difficultyColor}"></span>
                        <span class="font-medium text-primary ${isComplete ? 'line-through' : ''} truncate">${escapeHtml(resource.title)}</span>
                    </div>
                    ${timeDisplay ? `<div class="text-xs text-muted mt-1">${timeDisplay}</div>` : ''}
                </div>
                <div class="resource-actions flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                    <button onclick="event.stopPropagation(); toggleResourceComplete(${resource.id})" 
                            class="text-success hover:opacity-80"
                            aria-label="${isComplete ? 'Mark as incomplete' : 'Mark as complete'}">
                        <i class="fas fa-check"></i>
                    </button>
                    <button onclick="event.stopPropagation(); editResource(${resource.id})" 
                            class="text-muted hover:text-accent"
                            aria-label="Edit resource">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="event.stopPropagation(); deleteResource(${resource.id})" 
                            class="text-error hover:opacity-80"
                            aria-label="Delete resource">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ============================================================================
// SortableJS Integration
// ============================================================================

function initializeSortables() {
    // Initialize week columns (horizontal drag)
    document.querySelectorAll('.weeks-container').forEach(container => {
        if (sortableInstances[`weeks-${container.dataset.phaseId}`]) {
            sortableInstances[`weeks-${container.dataset.phaseId}`].destroy();
        }
        
        sortableInstances[`weeks-${container.dataset.phaseId}`] = new Sortable(container, {
            animation: 150,
            handle: '.drag-handle',
            direction: 'horizontal',
            ghostClass: 'opacity-50',
            onEnd: (evt) => handleWeekReorder(evt)
        });
    });
    
    // Initialize day cards (vertical drag within weeks)
    document.querySelectorAll('.days-container').forEach(container => {
        if (sortableInstances[`days-${container.dataset.weekId}`]) {
            sortableInstances[`days-${container.dataset.weekId}`].destroy();
        }
        
        sortableInstances[`days-${container.dataset.weekId}`] = new Sortable(container, {
            animation: 150,
            handle: '.day-card',
            ghostClass: 'opacity-50',
            group: 'days',
            onEnd: (evt) => handleDayReorder(evt)
        });
    });
    
    // Initialize resources (vertical drag within/between days)
    document.querySelectorAll('.resources-container').forEach(container => {
        if (sortableInstances[`resources-${container.dataset.dayId}`]) {
            sortableInstances[`resources-${container.dataset.dayId}`].destroy();
        }
        
        sortableInstances[`resources-${container.dataset.dayId}`] = new Sortable(container, {
            animation: 150,
            ghostClass: 'opacity-50',
            group: 'resources',
            onEnd: (evt) => handleResourceReorder(evt)
        });
    });
}

async function handleWeekReorder(evt) {
    const weekId = parseInt(evt.item.dataset.weekId);
    const newParentId = parseInt(evt.to.dataset.phaseId);
    const newIndex = evt.newIndex;
    
    // Optimistic update already happened (SortableJS moved DOM)
    try {
        const response = await fetch('/api/structure/reorder', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                type: 'week',
                id: weekId,
                new_parent_id: newParentId,
                new_index: newIndex
            })
        });
        
        if (!response.ok) {
            throw new Error('Reorder failed');
        }
        
        // Reload board to ensure consistency
        await loadBoard();
    } catch (error) {
        console.error('Reorder error:', error);
        showToast('Failed to reorder week', 'error');
        await loadBoard(); // Reload to fix state
    }
}

async function handleDayReorder(evt) {
    const dayId = parseInt(evt.item.dataset.dayId);
    const newParentId = parseInt(evt.to.dataset.weekId);
    const newIndex = evt.newIndex;
    
    try {
        const response = await fetch('/api/structure/reorder', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                type: 'day',
                id: dayId,
                new_parent_id: newParentId,
                new_index: newIndex
            })
        });
        
        if (!response.ok) throw new Error('Reorder failed');
        await loadBoard();
    } catch (error) {
        console.error('Reorder error:', error);
        showToast('Failed to reorder day', 'error');
        await loadBoard();
    }
}

async function handleResourceReorder(evt) {
    const resourceId = parseInt(evt.item.dataset.resourceId);
    const newDayId = parseInt(evt.to.dataset.dayId);
    const newIndex = evt.newIndex;
    
    try {
        // Use the resource reorder endpoint if it exists, or update day_id
        const response = await fetch(`/api/resource/${resourceId}/reorder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                day_id: newDayId,
                sort_order: newIndex
            })
        });
        
        if (!response.ok) {
            // Fallback: just update the day_id
            await fetch(`/api/resource/${resourceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({day_id: newDayId})
            });
        }
        
        await loadBoard();
    } catch (error) {
        console.error('Reorder error:', error);
        showToast('Failed to reorder resource', 'error');
        await loadBoard();
    }
}

// ============================================================================
// Inline Editing
// ============================================================================

function setupInlineEditing() {
    // Remove old listeners
    document.querySelectorAll('.editable-title').forEach(el => {
        el.removeEventListener('click', handleEditableClick);
    });
    
    // Add new listeners
    document.querySelectorAll('.editable-title').forEach(el => {
        el.addEventListener('click', handleEditableClick);
    });
}

function handleEditableClick(e) {
    const editable = e.target.closest('.editable-title');
    if (editable && !editable.querySelector('input:focus') && !e.target.tagName === 'INPUT') {
        enableEditTitle(editable);
    }
}

function enableEditTitle(element) {
    const display = element.querySelector('h2, h3, h4');
    const input = element.querySelector('input');
    if (!display || !input) return;
    
    display.classList.add('hidden');
    input.classList.remove('hidden');
    input.focus();
    input.select();
    
    const save = () => {
        const type = element.dataset.type;
        const id = parseInt(element.dataset.id);
        const title = input.value.trim();
        
        if (title && title !== display.textContent.trim()) {
            updateStructureTitle(type, id, title);
        } else {
            cancelEdit(element);
        }
    };
    
    input.onblur = save;
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            save();
        } else if (e.key === 'Escape') {
            cancelEdit(element);
        }
    };
}

function cancelEdit(element) {
    const display = element.querySelector('h2, h3, h4');
    const input = element.querySelector('input');
    if (display && input) {
        display.classList.remove('hidden');
        input.classList.add('hidden');
        input.value = display.textContent.trim();
    }
}

async function updateStructureTitle(type, id, title) {
    try {
        const response = await fetch(`/api/structure/${type}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({title})
        });
        
        if (!response.ok) throw new Error('Update failed');
        
        await loadBoard();
    } catch (error) {
        console.error('Error updating title:', error);
        showToast('Failed to update title', 'error');
        await loadBoard();
    }
}

// ============================================================================
// Quick Add Features
// ============================================================================

function showQuickAddResource(dayId) {
    const quickAdd = document.querySelector(`.quick-add-resource[data-day-id="${dayId}"]`);
    const button = event.target.closest('button');
    
    if (quickAdd) {
        quickAdd.classList.remove('hidden');
        button.classList.add('hidden');
        const input = document.getElementById(`quick-add-title-${dayId}`);
        if (input) input.focus();
    }
}

function hideQuickAdd(dayId) {
    const quickAdd = document.querySelector(`.quick-add-resource[data-day-id="${dayId}"]`);
    const button = quickAdd?.nextElementSibling;
    
    if (quickAdd) quickAdd.classList.add('hidden');
    if (button) button.classList.remove('hidden');
}

async function createResource(dayId) {
    const titleInput = document.getElementById(`quick-add-title-${dayId}`);
    const typeSelect = document.getElementById(`quick-add-type-${dayId}`);
    
    if (!titleInput || !typeSelect) return;
    
    const title = titleInput.value.trim();
    const resourceType = typeSelect.value;
    
    if (!title) {
        showToast('Title is required', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/resource', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                day_id: dayId,
                title,
                resource_type: resourceType
            })
        });
        
        if (!response.ok) throw new Error('Create failed');
        
        await loadBoard();
        hideQuickAdd(dayId);
    } catch (error) {
        console.error('Error creating resource:', error);
        showToast('Failed to create resource', 'error');
    }
}

// ============================================================================
// CRUD Operations
// ============================================================================

async function createPhase() {
    const title = prompt('Phase title:');
    if (!title) return;
    
    try {
        const response = await fetch('/api/structure/phase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({title})
        });
        
        if (!response.ok) throw new Error('Create failed');
        await loadBoard();
    } catch (error) {
        console.error('Error creating phase:', error);
        showToast('Failed to create phase', 'error');
    }
}

function showAddWeek(phaseId) {
    const title = prompt('Week title:');
    if (!title) return;
    
    fetch('/api/structure/week', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({phase_id: phaseId, title})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        loadBoard();
    })
    .catch(err => {
        console.error('Error:', err);
        showToast('Failed to create week', 'error');
    });
}

function showAddDay(weekId) {
    const title = prompt('Day title:');
    if (!title) return;
    
    fetch('/api/structure/day', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({week_id: weekId, title})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        loadBoard();
    })
    .catch(err => {
        console.error('Error:', err);
        showToast('Failed to create day', 'error');
    });
}

function togglePhaseCollapse(phaseId) {
    const content = document.querySelector(`[data-phase-id="${phaseId}"] .phase-content`);
    const isCollapsed = content.classList.toggle('hidden');
    localStorage.setItem(`phase-${phaseId}-collapsed`, isCollapsed);
    loadBoard(); // Update icon
}

function editPhaseSettings(phaseId) {
    // TODO: Open modal for phase settings (color, etc.)
    showToast('Phase settings coming soon', 'info');
}

// ============================================================================
// Resource Management
// ============================================================================

function handleResourceClick(event, resourceId) {
    // Handle Shift+Click for multi-select
    if (event.shiftKey) {
        event.preventDefault();
        if (selectedResources.has(resourceId)) {
            selectedResources.delete(resourceId);
        } else {
            selectedResources.add(resourceId);
        }
        updateResourceSelection();
        return;
    }
    
    // Single click: open resource details
    // TODO: Show resource detail modal
}

function handleResourceKeydown(event, resourceId) {
    const resourceElement = event.target.closest('.resource-item');
    if (!resourceElement) return;
    
    switch(event.key) {
        case ' ':
        case 'Enter':
            event.preventDefault();
            if (event.key === 'Enter') {
                // Enter: edit resource
                editResource(resourceId);
            } else {
                // Space: toggle complete
                toggleResourceComplete(resourceId);
            }
            break;
        case 'ArrowUp':
            event.preventDefault();
            moveFocus(resourceElement, 'up');
            break;
        case 'ArrowDown':
            event.preventDefault();
            moveFocus(resourceElement, 'down');
            break;
        case 'ArrowLeft':
            event.preventDefault();
            moveFocus(resourceElement, 'left');
            break;
        case 'ArrowRight':
            event.preventDefault();
            moveFocus(resourceElement, 'right');
            break;
        case 'Escape':
            resourceElement.blur();
            break;
    }
}

function moveFocus(currentElement, direction) {
    const allResources = Array.from(document.querySelectorAll('.resource-item'));
    const currentIndex = allResources.indexOf(currentElement);
    
    if (currentIndex === -1) return;
    
    let nextIndex = currentIndex;
    const currentDayId = currentElement.dataset.dayId;
    
    switch(direction) {
        case 'up':
            // Find previous resource in same or previous day
            for (let i = currentIndex - 1; i >= 0; i--) {
                if (allResources[i].dataset.dayId) {
                    nextIndex = i;
                    break;
                }
            }
            break;
        case 'down':
            // Find next resource in same or next day
            for (let i = currentIndex + 1; i < allResources.length; i++) {
                if (allResources[i].dataset.dayId) {
                    nextIndex = i;
                    break;
                }
            }
            break;
        case 'left':
            // Move to previous day
            const currentDay = document.querySelector(`[data-day-id="${currentDayId}"]`);
            const currentWeekForLeft = currentDay?.closest('[data-week-id]');
            const prevDay = currentWeekForLeft?.querySelectorAll('.day-card');
            const currentDayIndex = Array.from(prevDay || []).findIndex(d => d.dataset.dayId === currentDayId);
            if (currentDayIndex > 0 && prevDay) {
                const prevDayCard = prevDay[currentDayIndex - 1];
                const firstResource = prevDayCard.querySelector('.resource-item');
                if (firstResource) {
                    firstResource.focus();
                    return;
                }
            }
            break;
        case 'right':
            // Move to next day
            const currentDayForRight = document.querySelector(`[data-day-id="${currentDayId}"]`);
            const currentWeekForRight = currentDayForRight?.closest('[data-week-id]');
            const allDays = currentWeekForRight?.querySelectorAll('.day-card');
            const currentDayIndexForRight = Array.from(allDays || []).findIndex(d => d.dataset.dayId === currentDayId);
            if (currentDayIndexForRight >= 0 && allDays && currentDayIndexForRight < allDays.length - 1) {
                const nextDayCard = allDays[currentDayIndexForRight + 1];
                const firstResource = nextDayCard.querySelector('.resource-item');
                if (firstResource) {
                    firstResource.focus();
                    return;
                }
            }
            break;
    }
    
    if (nextIndex !== currentIndex && allResources[nextIndex]) {
        allResources[nextIndex].focus();
    }
}

function updateResourceSelection() {
    document.querySelectorAll('.resource-item').forEach(item => {
        const id = parseInt(item.dataset.resourceId);
        if (selectedResources.has(id)) {
            item.classList.add('ring-2', 'ring-accent');
        } else {
            item.classList.remove('ring-2', 'ring-accent');
        }
    });
}

async function toggleResourceComplete(resourceId) {
    // Find the resource in boardData to get current status
    let currentStatus = 'not_started';
    let resource = null;
    
    if (boardData && boardData.phases) {
        for (const phase of boardData.phases) {
            if (phase.weeks) {
                for (const week of phase.weeks) {
                    if (week.days) {
                        for (const day of week.days) {
                            if (day.resources) {
                                const found = day.resources.find(r => r.id === resourceId);
                                if (found) {
                                    resource = found;
                                    currentStatus = found.status || 'not_started';
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Toggle between complete and not_started
    const newStatus = currentStatus === 'complete' ? 'not_started' : 'complete';
    
    // Optimistic UI update
    const resourceElement = document.querySelector(`[data-resource-id="${resourceId}"]`);
    if (resourceElement) {
        if (newStatus === 'complete') {
            resourceElement.classList.add('opacity-60');
            resourceElement.querySelector('.font-medium').classList.add('line-through');
        } else {
            resourceElement.classList.remove('opacity-60');
            resourceElement.querySelector('.font-medium').classList.remove('line-through');
        }
    }
    
    try {
        const response = await fetch(`/api/resource/${resourceId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update status');
        }
        
        // Reload board to ensure consistency
        await loadBoard();
        showToast(newStatus === 'complete' ? 'Resource marked as complete' : 'Resource marked as incomplete', 'success');
    } catch (error) {
        console.error('Error toggling resource status:', error);
        showToast('Failed to update resource status', 'error');
        // Reload to fix UI state
        await loadBoard();
    }
}

async function editResource(resourceId) {
    // Find the resource in boardData to populate the form
    let resource = null;
    
    if (boardData && boardData.phases) {
        for (const phase of boardData.phases) {
            if (phase.weeks) {
                for (const week of phase.weeks) {
                    if (week.days) {
                        for (const day of week.days) {
                            if (day.resources) {
                                const found = day.resources.find(r => r.id === resourceId);
                                if (found) {
                                    resource = found;
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    if (!resource) {
        showToast('Resource not found', 'error');
        return;
    }
    
    // Populate the modal form
    document.getElementById('edit-resource-id').value = resourceId;
    document.getElementById('edit-resource-title').value = resource.title || '';
    document.getElementById('edit-resource-url').value = resource.url || '';
    document.getElementById('edit-resource-type').value = resource.resource_type || 'link';
    document.getElementById('edit-resource-difficulty').value = resource.difficulty || 'medium';
    document.getElementById('edit-resource-minutes').value = resource.estimated_minutes || '';
    document.getElementById('edit-resource-notes').value = resource.notes || '';
    
    // Show the modal
    document.getElementById('edit-resource-modal').classList.remove('hidden');
    document.getElementById('edit-resource-title').focus();
}

function closeEditResourceModal() {
    document.getElementById('edit-resource-modal').classList.add('hidden');
    document.getElementById('edit-resource-form').reset();
}

async function saveResourceEdit(event) {
    event.preventDefault();
    
    const resourceId = document.getElementById('edit-resource-id').value;
    const title = document.getElementById('edit-resource-title').value.trim();
    
    if (!title) {
        showToast('Title is required', 'error');
        return;
    }
    
    const updateData = {
        title: title,
        url: document.getElementById('edit-resource-url').value.trim() || null,
        resource_type: document.getElementById('edit-resource-type').value,
        difficulty: document.getElementById('edit-resource-difficulty').value,
        estimated_minutes: document.getElementById('edit-resource-minutes').value ? parseInt(document.getElementById('edit-resource-minutes').value) : null,
        notes: document.getElementById('edit-resource-notes').value.trim() || null
    };
    
    try {
        const response = await fetch(`/api/resource/${resourceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(updateData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update resource');
        }
        
        closeEditResourceModal();
        await loadBoard();
        showToast('Resource updated successfully', 'success');
    } catch (error) {
        console.error('Error updating resource:', error);
        showToast('Failed to update resource', 'error');
    }
}

async function deleteResource(resourceId) {
    if (!confirm('Delete this resource?')) return;
    
    try {
        const response = await fetch(`/api/resource/${resourceId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        if (!response.ok) throw new Error('Delete failed');
        await loadBoard();
    } catch (error) {
        console.error('Error deleting resource:', error);
        showToast('Failed to delete resource', 'error');
    }
}

// ============================================================================
// Inbox Drawer
// ============================================================================

function toggleInbox() {
    const drawer = document.getElementById('inbox-drawer');
    drawer.classList.toggle('hidden');
}

async function loadInboxResources() {
    // TODO: Load resources with day_id = null or from inbox day
    // For now, just update count
    document.getElementById('inbox-count').textContent = '0';
}

// ============================================================================
// Utility Functions
// ============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function calculatePhaseProgress(phase) {
    let total = 0;
    let completed = 0;
    
    if (phase.weeks) {
        phase.weeks.forEach(week => {
            if (week.days) {
                week.days.forEach(day => {
                    if (day.resources) {
                        day.resources.forEach(resource => {
                            total++;
                            if (resource.status === 'complete' || resource.is_completed) {
                                completed++;
                            }
                        });
                    }
                });
            }
        });
    }
    
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
    return {completed, total, percent};
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        </div>
        <div class="toast-content">${escapeHtml(message)}</div>
        <button onclick="this.parentElement.remove()" class="toast-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

// Make functions available globally
window.loadBoard = loadBoard;
window.showQuickAddResource = showQuickAddResource;
window.hideQuickAdd = hideQuickAdd;
window.createResource = createResource;
window.createPhase = createPhase;
window.showAddWeek = showAddWeek;
window.showAddDay = showAddDay;
window.togglePhaseCollapse = togglePhaseCollapse;
window.editPhaseSettings = editPhaseSettings;
window.handleResourceClick = handleResourceClick;
window.toggleResourceComplete = toggleResourceComplete;
window.editResource = editResource;
window.deleteResource = deleteResource;
window.toggleInbox = toggleInbox;
window.closeEditResourceModal = closeEditResourceModal;
window.saveResourceEdit = saveResourceEdit;
window.handleResourceKeydown = handleResourceKeydown;


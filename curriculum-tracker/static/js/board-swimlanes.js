/**
 * Board Swimlane Grouping
 * Allows organizing board by category, priority, or custom criteria
 */

let swimlaneMode = 'none'; // 'none', 'category', 'priority', 'custom'
let swimlanes = {};

function toggleSwimlaneMode(mode) {
    swimlaneMode = mode;
    renderSwimlanes();
    updateSwimlaneToggle();
}

function renderSwimlanes() {
    const board = document.querySelector('.kanban-board');
    if (!board) return;
    
    if (swimlaneMode === 'none') {
        // Remove swimlanes, show normal board
        removeSwimlanes();
        return;
    }
    
    // Group cards by swimlane criteria
    const cards = Array.from(document.querySelectorAll('.kanban-card'));
    const grouped = groupCardsBySwimlane(cards);
    
    // Create swimlane structure
    createSwimlaneStructure(grouped);
}

function groupCardsBySwimlane(cards) {
    const grouped = {};
    
    cards.forEach(card => {
        let key = 'Uncategorized';
        
        if (swimlaneMode === 'category') {
            // Group by tags or category
            const tags = card.dataset.tags ? card.dataset.tags.split(',') : [];
            key = tags.length > 0 ? tags[0] : 'Uncategorized';
        } else if (swimlaneMode === 'priority') {
            // Group by priority
            key = card.dataset.priority || 'Normal';
        } else if (swimlaneMode === 'custom') {
            // Group by custom field
            key = card.dataset.customGroup || 'Uncategorized';
        }
        
        if (!grouped[key]) {
            grouped[key] = [];
        }
        grouped[key].push(card);
    });
    
    return grouped;
}

function createSwimlaneStructure(grouped) {
    const board = document.querySelector('.kanban-board');
    if (!board) return;
    
    // Remove existing swimlanes
    removeSwimlanes();
    
    // Create swimlane container
    const container = document.createElement('div');
    container.className = 'swimlanes-container';
    
    Object.keys(grouped).forEach(laneName => {
        const swimlane = createSwimlane(laneName, grouped[laneName]);
        container.appendChild(swimlane);
    });
    
    // Insert before existing columns or replace board content
    const columns = board.querySelector('.kanban-columns');
    if (columns) {
        board.insertBefore(container, columns);
        columns.style.display = 'none';
    }
}

function createSwimlane(name, cards) {
    const swimlane = document.createElement('div');
    swimlane.className = 'swimlane';
    swimlane.dataset.laneName = name;
    
    const header = document.createElement('div');
    header.className = 'swimlane-header';
    header.innerHTML = `
        <h3 class="swimlane-title">${escapeHtml(name)}</h3>
        <span class="swimlane-count">${cards.length} items</span>
        <button class="swimlane-toggle" onclick="toggleSwimlaneCollapse('${name}')">
            <i class="fas fa-chevron-down"></i>
        </button>
    `;
    
    const content = document.createElement('div');
    content.className = 'swimlane-content';
    content.id = `swimlane-${name}`;
    
    // Create columns within swimlane
    const columns = document.createElement('div');
    columns.className = 'swimlane-columns kanban-columns';
    
    // Get existing column structure
    const existingColumns = document.querySelectorAll('.kanban-column');
    existingColumns.forEach(column => {
        const columnClone = column.cloneNode(false);
        columnClone.className = 'kanban-column';
        columnClone.dataset.status = column.dataset.status;
        
        // Add cards that belong to this column
        const columnStatus = column.dataset.status;
        cards.forEach(card => {
            if (card.closest(`[data-status="${columnStatus}"]`)) {
                columnClone.appendChild(card.cloneNode(true));
            }
        });
        
        columns.appendChild(columnClone);
    });
    
    content.appendChild(columns);
    swimlane.appendChild(header);
    swimlane.appendChild(content);
    
    return swimlane;
}

function removeSwimlanes() {
    const container = document.querySelector('.swimlanes-container');
    if (container) {
        container.remove();
    }
    
    // Show normal columns
    const columns = document.querySelector('.kanban-columns');
    if (columns) {
        columns.style.display = '';
    }
}

function toggleSwimlaneCollapse(laneName) {
    const content = document.getElementById(`swimlane-${laneName}`);
    const toggle = event.target.closest('.swimlane-toggle');
    
    if (content && toggle) {
        content.classList.toggle('collapsed');
        const icon = toggle.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
        }
    }
}

function updateSwimlaneToggle() {
    const buttons = document.querySelectorAll('.swimlane-mode-btn');
    buttons.forEach(btn => {
        if (btn.dataset.mode === swimlaneMode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.kanban-board')) {
        // Add swimlane toggle buttons
        addSwimlaneControls();
    }
});

function addSwimlaneControls() {
    const board = document.querySelector('.kanban-board');
    if (!board) return;
    
    // Check if controls already exist
    if (document.getElementById('swimlane-controls')) return;
    
    const controls = document.createElement('div');
    controls.id = 'swimlane-controls';
    controls.className = 'swimlane-controls';
    controls.innerHTML = `
        <div class="flex items-center gap-2 mb-4">
            <span class="text-sm text-secondary">Group by:</span>
            <button class="swimlane-mode-btn btn-secondary btn-sm" data-mode="none" onclick="toggleSwimlaneMode('none')">
                None
            </button>
            <button class="swimlane-mode-btn btn-secondary btn-sm" data-mode="category" onclick="toggleSwimlaneMode('category')">
                Category
            </button>
            <button class="swimlane-mode-btn btn-secondary btn-sm" data-mode="priority" onclick="toggleSwimlaneMode('priority')">
                Priority
            </button>
        </div>
    `;
    
    board.parentNode.insertBefore(controls, board);
    updateSwimlaneToggle();
}

// Export for global access
window.toggleSwimlaneMode = toggleSwimlaneMode;
window.toggleSwimlaneCollapse = toggleSwimlaneCollapse;


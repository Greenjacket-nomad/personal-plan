/**
 * Resource Filtering System
 * Handles faceted filtering sidebar and filter application
 */

let activeFilters = {
    types: [],
    tags: [],
    statuses: [],
    dateRange: 'all'
};

function toggleFiltersSidebar() {
    const sidebar = document.querySelector('.resource-filters-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

function applyFilters() {
    // Collect active filters
    activeFilters.types = Array.from(document.querySelectorAll('input[name="filter-type"]:checked'))
        .map(cb => cb.value);
    activeFilters.tags = Array.from(document.querySelectorAll('input[name="filter-tag"]:checked'))
        .map(cb => cb.value);
    activeFilters.statuses = Array.from(document.querySelectorAll('input[name="filter-status"]:checked'))
        .map(cb => cb.value);
    
    const dateRadio = document.querySelector('input[name="filter-date"]:checked');
    activeFilters.dateRange = dateRadio ? dateRadio.value : 'all';
    
    // Apply filters to resource cards
    const resourceCards = document.querySelectorAll('.resource-card');
    let visibleCount = 0;
    
    resourceCards.forEach(card => {
        let visible = true;
        
        // Type filter
        if (activeFilters.types.length > 0) {
            const resourceType = card.dataset.resourceType;
            if (!activeFilters.types.includes(resourceType)) {
                visible = false;
            }
        }
        
        // Tag filter
        if (visible && activeFilters.tags.length > 0) {
            const cardTags = card.dataset.tags ? card.dataset.tags.split(',') : [];
            const hasMatchingTag = activeFilters.tags.some(tag => cardTags.includes(tag));
            if (!hasMatchingTag) {
                visible = false;
            }
        }
        
        // Status filter
        if (visible && activeFilters.statuses.length > 0) {
            const status = card.dataset.status || 'not_started';
            const isFavorite = card.dataset.isFavorite === 'true';
            
            let matchesStatus = false;
            if (activeFilters.statuses.includes('favorites') && isFavorite) {
                matchesStatus = true;
            } else if (activeFilters.statuses.includes(status)) {
                matchesStatus = true;
            }
            
            if (!matchesStatus) {
                visible = false;
            }
        }
        
        // Date filter
        if (visible && activeFilters.dateRange !== 'all') {
            const createdDate = card.dataset.createdAt;
            if (createdDate) {
                const date = new Date(createdDate);
                const now = new Date();
                const daysDiff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
                
                if (activeFilters.dateRange === 'today' && daysDiff !== 0) {
                    visible = false;
                } else if (activeFilters.dateRange === 'week' && daysDiff > 7) {
                    visible = false;
                } else if (activeFilters.dateRange === 'month' && daysDiff > 30) {
                    visible = false;
                }
            }
        }
        
        // Show/hide card
        if (visible) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update result count
    updateResultCount(visibleCount);
}

function clearAllFilters() {
    // Uncheck all checkboxes
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        if (radio.value === 'all') radio.checked = true;
        else radio.checked = false;
    });
    
    activeFilters = {
        types: [],
        tags: [],
        statuses: [],
        dateRange: 'all'
    };
    
    applyFilters();
}

function updateResultCount(count) {
    const countElement = document.getElementById('filter-result-count');
    if (countElement) {
        countElement.textContent = `${count} resources`;
    }
}

function initializeFilters() {
    // Populate tag filters
    const tagFiltersContainer = document.getElementById('tag-filters');
    if (tagFiltersContainer && window.allTags) {
        window.allTags.forEach(tag => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" name="filter-tag" value="${tag.name}" onchange="applyFilters()">
                <span style="color: ${tag.color}"><i class="fas fa-tag"></i> ${tag.name}</span>
                <span class="filter-count" id="count-tag-${tag.name}">0</span>
            `;
            tagFiltersContainer.appendChild(label);
        });
    }
    
    // Calculate initial counts
    calculateFilterCounts();
}

function calculateFilterCounts() {
    const resourceCards = document.querySelectorAll('.resource-card');
    
    // Count by type
    const typeCounts = {};
    const tagCounts = {};
    const statusCounts = {};
    
    resourceCards.forEach(card => {
        const type = card.dataset.resourceType;
        typeCounts[type] = (typeCounts[type] || 0) + 1;
        
        const status = card.dataset.status || 'not_started';
        statusCounts[status] = (statusCounts[status] || 0) + 1;
        
        const isFavorite = card.dataset.isFavorite === 'true';
        if (isFavorite) {
            statusCounts['favorites'] = (statusCounts['favorites'] || 0) + 1;
        }
        
        const tags = card.dataset.tags ? card.dataset.tags.split(',') : [];
        tags.forEach(tag => {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        });
    });
    
    // Update count displays
    Object.keys(typeCounts).forEach(type => {
        const countEl = document.getElementById(`count-type-${type}`);
        if (countEl) countEl.textContent = typeCounts[type];
    });
    
    Object.keys(tagCounts).forEach(tag => {
        const countEl = document.getElementById(`count-tag-${tag}`);
        if (countEl) countEl.textContent = tagCounts[tag];
    });
    
    Object.keys(statusCounts).forEach(status => {
        const countEl = document.getElementById(`count-status-${status}`);
        if (countEl) countEl.textContent = statusCounts[status];
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.resource-filters-sidebar')) {
        initializeFilters();
    }
});

// Export for global access
window.toggleFiltersSidebar = toggleFiltersSidebar;
window.applyFilters = applyFilters;
window.clearAllFilters = clearAllFilters;


/**
 * Resource View Switching
 * Handles grid/list/compact view switching for resources page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Restore saved view preference
    const savedView = localStorage.getItem('resourceViewMode') || 'list';
    setViewMode(savedView);
    
    // Initialize view toggle buttons
    document.querySelectorAll('.view-toggle-button').forEach(button => {
        button.addEventListener('click', function() {
            const viewMode = this.dataset.view;
            setViewMode(viewMode);
        });
    });
});

function setViewMode(mode) {
    const container = document.getElementById('resources-container');
    if (!container) return;
    
    // Remove all view classes
    container.classList.remove('resources-list-view', 'resources-grid-view', 'resources-compact-view');
    
    // Add new view class
    container.classList.add(`resources-${mode}-view`);
    
    // Update toggle buttons
    document.querySelectorAll('.view-toggle-button').forEach(button => {
        button.classList.remove('active');
        if (button.dataset.view === mode) {
            button.classList.add('active');
        }
    });
    
    // Save preference
    localStorage.setItem('resourceViewMode', mode);
    
    // Trigger resize event for any layout-dependent code
    window.dispatchEvent(new Event('resize'));
}

// Export for global access
window.setViewMode = setViewMode;


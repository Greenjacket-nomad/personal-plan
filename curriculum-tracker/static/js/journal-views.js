/**
 * Journal View Switching
 * Handles list/grid/timeline view switching for journal page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Restore saved view preference
    const savedView = localStorage.getItem('journalViewMode') || 'list';
    setJournalView(savedView);
    
    // Initialize view toggle buttons
    document.querySelectorAll('.view-toggle-button').forEach(button => {
        button.addEventListener('click', function() {
            const viewMode = this.dataset.view;
            setJournalView(viewMode);
        });
    });
    
    // Writing mode toggle
    const writingModeToggle = document.getElementById('writing-mode-toggle');
    if (writingModeToggle) {
        writingModeToggle.addEventListener('click', toggleWritingMode);
    }
    
    // ESC key to exit writing mode
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && document.querySelector('.writing-mode.active')) {
            toggleWritingMode();
        }
    });
});

function setJournalView(mode) {
    const container = document.getElementById('journal-entries-list');
    if (!container) return;
    
    // Remove all view classes
    container.classList.remove('journal-list-view', 'journal-grid-view', 'journal-timeline-view');
    
    // Add new view class
    container.classList.add(`journal-${mode}-view`);
    
    // Update toggle buttons
    document.querySelectorAll('.view-toggle-button').forEach(button => {
        button.classList.remove('active');
        if (button.dataset.view === mode) {
            button.classList.add('active');
        }
    });
    
    // Save preference
    localStorage.setItem('journalViewMode', mode);
}

function toggleWritingMode() {
    const writingMode = document.getElementById('writing-mode');
    if (!writingMode) return;
    
    const isActive = writingMode.classList.contains('active');
    
    if (isActive) {
        writingMode.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        writingMode.classList.add('active');
        document.body.style.overflow = 'hidden';
        const textarea = writingMode.querySelector('textarea');
        if (textarea) {
            setTimeout(() => textarea.focus(), 100);
        }
    }
}

// Export for global access
window.setJournalView = setJournalView;
window.toggleWritingMode = toggleWritingMode;


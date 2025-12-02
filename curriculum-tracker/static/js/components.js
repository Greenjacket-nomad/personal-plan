// Component Improvements
// Handles modals, tooltips, dropdowns, and other UI components

// Modal Management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Auto-focus first input
        const firstInput = modal.querySelector('input, textarea, select, button');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
        
        // Trap focus
        trapFocusInModal(modal);
        
        // Close on ESC
        const escHandler = function(e) {
            if (e.key === 'Escape') {
                closeModal(modalId);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        modal._escHandler = escHandler;
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        
        // Remove focus trap
        removeFocusTrap(modal);
        
        // Remove ESC handler
        if (modal._escHandler) {
            document.removeEventListener('keydown', modal._escHandler);
            delete modal._escHandler;
        }
    }
}

// Close modal on background click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        closeModal(e.target.id);
    }
});

// Dropdown Positioning
function positionDropdown(dropdown, menu) {
    if (!dropdown || !menu) return;
    
    const rect = dropdown.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Reset classes
    menu.classList.remove('right', 'top');
    
    // Check if menu would overflow right
    if (rect.left + menuRect.width > viewportWidth) {
        menu.classList.add('right');
    }
    
    // Check if menu would overflow bottom
    if (rect.bottom + menuRect.height > viewportHeight) {
        menu.classList.add('top');
    }
}

// Initialize dropdowns
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (toggle && menu) {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                const isOpen = menu.classList.contains('show');
                
                // Close all other dropdowns
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {
                    if (m !== menu) m.classList.remove('show');
                });
                
                if (isOpen) {
                    menu.classList.remove('show');
                } else {
                    positionDropdown(dropdown, menu);
                    menu.classList.add('show');
                }
            });
        }
    });
    
    // Close dropdowns on outside click
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });
});

// Export for global access
window.openModal = openModal;
window.closeModal = closeModal;


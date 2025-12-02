// Modal Focus Management
// Handles auto-focus and focus trapping for modals

/**
 * Auto-focus first input in modal when opened
 */
function autoFocusModal(modalElement) {
    if (!modalElement) return;
    
    // Find first focusable element
    const focusableSelectors = 'input:not([disabled]):not([type="hidden"]), textarea:not([disabled]), select:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const firstFocusable = modalElement.querySelector(focusableSelectors);
    
    if (firstFocusable) {
        setTimeout(() => {
            firstFocusable.focus();
        }, 100);
    }
}

/**
 * Trap focus within modal
 */
function trapFocusInModal(modalElement) {
    if (!modalElement) return;
    
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusableElements = Array.from(modalElement.querySelectorAll(focusableSelectors));
    
    if (focusableElements.length === 0) return;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleTab = function(e) {
        if (e.key !== 'Tab') return;
        
        if (e.shiftKey) {
            // Shift + Tab
            if (document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
        } else {
            // Tab
            if (document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    };
    
    modalElement.addEventListener('keydown', handleTab);
    
    // Store handler for cleanup
    modalElement._focusTrapHandler = handleTab;
}

/**
 * Remove focus trap from modal
 */
function removeFocusTrap(modalElement) {
    if (!modalElement || !modalElement._focusTrapHandler) return;
    modalElement.removeEventListener('keydown', modalElement._focusTrapHandler);
    delete modalElement._focusTrapHandler;
}

/**
 * Setup modal with auto-focus and focus trapping
 */
function setupModal(modalElement) {
    if (!modalElement) return;
    
    // Auto-focus when modal becomes visible
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                if (!modalElement.classList.contains('hidden')) {
                    autoFocusModal(modalElement);
                    trapFocusInModal(modalElement);
                } else {
                    removeFocusTrap(modalElement);
                }
            }
        });
    });
    
    observer.observe(modalElement, {
        attributes: true,
        attributeFilter: ['class']
    });
    
    // Also check on initial load
    if (!modalElement.classList.contains('hidden')) {
        autoFocusModal(modalElement);
        trapFocusInModal(modalElement);
    }
}

/**
 * Initialize all modals on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.modal, [role="dialog"]').forEach(modal => {
        setupModal(modal);
    });
    
    // Watch for dynamically added modals
    const modalObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    if (node.classList && (node.classList.contains('modal') || node.getAttribute('role') === 'dialog')) {
                        setupModal(node);
                    }
                    // Also check children
                    node.querySelectorAll && node.querySelectorAll('.modal, [role="dialog"]').forEach(modal => {
                        setupModal(modal);
                    });
                }
            });
        });
    });
    
    modalObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for global access
window.autoFocusModal = autoFocusModal;
window.trapFocusInModal = trapFocusInModal;
window.setupModal = setupModal;


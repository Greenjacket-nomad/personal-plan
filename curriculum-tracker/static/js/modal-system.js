/**
 * Enhanced Modal System
 * Handles modal opening, closing, animations, and focus management
 */

// Store reference to element that opened modal (for focus restoration)
let lastFocusedElement = null;
let activeModal = null;

/**
 * Open a modal
 */
function openModal(modalId, firstFocusableSelector = null) {
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.warn(`Modal with id "${modalId}" not found`);
        return;
    }
    
    // Store currently focused element
    lastFocusedElement = document.activeElement;
    
    // Set as active modal
    activeModal = modal;
    
    // Show modal overlay
    modal.classList.add('show');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('role', 'dialog');
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    
    // Focus management
    const modalContent = modal.querySelector('.modal');
    if (modalContent) {
        // Auto-focus first focusable element or specified element
        setTimeout(() => {
            let firstFocusable = null;
            
            if (firstFocusableSelector) {
                firstFocusable = modalContent.querySelector(firstFocusableSelector);
            }
            
            if (!firstFocusable) {
                // Find first focusable element
                const focusableSelectors = 'input:not([disabled]):not([type="hidden"]), textarea:not([disabled]), select:not([disabled]), button:not([disabled]):not(.modal-close), [tabindex]:not([tabindex="-1"])';
                const focusableElements = Array.from(modalContent.querySelectorAll(focusableSelectors));
                firstFocusable = focusableElements.find(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                });
            }
            
            if (firstFocusable) {
                firstFocusable.focus();
            } else {
                // Fallback: focus the modal itself
                modalContent.focus();
            }
        }, 100);
    }
    
    // Trap focus within modal
    trapFocusInModal(modal);
    
    // Handle ESC key
    const handleEscape = function(e) {
        if (e.key === 'Escape' && activeModal === modal) {
            closeModal(modalId);
        }
    };
    
    document.addEventListener('keydown', handleEscape);
    modal._escapeHandler = handleEscape;
    
    // Handle backdrop click
    const handleBackdropClick = function(e) {
        if (e.target === modal) {
            closeModal(modalId);
        }
    };
    
    modal.addEventListener('click', handleBackdropClick);
    modal._backdropHandler = handleBackdropClick;
}

/**
 * Show a modal (alias for openModal for consistency)
 */
function showModal(modalId, firstFocusableSelector = null) {
    openModal(modalId, firstFocusableSelector);
}

/**
 * Close a modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    // Remove show class
    modal.classList.remove('show');
    modal.removeAttribute('aria-modal');
    modal.removeAttribute('role');
    
    // Restore body scroll
    document.body.style.overflow = '';
    
    // Remove focus trap
    if (modal._focusTrapHandler) {
        removeFocusTrap(modal);
    }
    
    // Remove event listeners
    if (modal._escapeHandler) {
        document.removeEventListener('keydown', modal._escapeHandler);
        delete modal._escapeHandler;
    }
    
    if (modal._backdropHandler) {
        modal.removeEventListener('click', modal._backdropHandler);
        delete modal._backdropHandler;
    }
    
    // Restore focus to element that opened modal
    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        setTimeout(() => {
            lastFocusedElement.focus();
        }, 100);
    }
    
    // Clear active modal
    if (activeModal === modal) {
        activeModal = null;
    }
    
    lastFocusedElement = null;
}

/**
 * Trap focus within modal (enhanced version)
 */
function trapFocusInModal(modalElement) {
    if (!modalElement) return;
    
    const modalContent = modalElement.querySelector('.modal');
    if (!modalContent) return;
    
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusableElements = Array.from(modalContent.querySelectorAll(focusableSelectors))
        .filter(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden';
        });
    
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
 * Initialize modal system
 */
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize modals with data attributes
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = trigger.dataset.modalTarget;
            const firstFocus = trigger.dataset.firstFocus;
            openModal(modalId, firstFocus);
        });
    });
    
    // Auto-initialize close buttons
    document.querySelectorAll('.modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const modal = closeBtn.closest('.modal-overlay');
            if (modal && modal.id) {
                closeModal(modal.id);
            }
        });
    });
});

// Export for global access
window.openModal = openModal;
window.showModal = showModal;
window.closeModal = closeModal;
window.trapFocusInModal = trapFocusInModal;
window.removeFocusTrap = removeFocusTrap;


// Accessibility Utilities
// Focus management, skip links, ARIA helpers, and keyboard navigation

// Skip to main content functionality
function initSkipLink() {
    const skipLink = document.getElementById('skip-to-main');
    if (skipLink) {
        skipLink.addEventListener('click', function(e) {
            e.preventDefault();
            const main = document.querySelector('main') || document.querySelector('#main-content') || document.querySelector('.main-content');
            if (main) {
                main.setAttribute('tabindex', '-1');
                main.focus();
                main.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Remove tabindex after focus to prevent tabbing to it
                setTimeout(() => {
                    main.removeAttribute('tabindex');
                }, 1000);
            }
        });
    }
}

// Focus trap for modals
function trapFocus(container) {
    const focusableElements = container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    function handleTab(e) {
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
    }
    
    container.addEventListener('keydown', handleTab);
    
    // Focus first element when modal opens
    if (firstElement) {
        firstElement.focus();
    }
    
    // Return cleanup function
    return () => {
        container.removeEventListener('keydown', handleTab);
    };
}

// Initialize modal focus trap
function initModalFocusTrap() {
    // Find all modals
    const modals = document.querySelectorAll('.modal, [role="dialog"], [data-modal]');
    
    modals.forEach(modal => {
        // Only trap focus if modal is visible
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const isVisible = !modal.classList.contains('hidden') && 
                                    !modal.classList.contains('d-none') &&
                                    modal.style.display !== 'none';
                    
                    if (isVisible && !modal.dataset.focusTrapInitialized) {
                        modal.dataset.focusTrapInitialized = 'true';
                        trapFocus(modal);
                    }
                }
            });
        });
        
        observer.observe(modal, {
            attributes: true,
            attributeFilter: ['class', 'style']
        });
        
        // Check initial state
        const isVisible = !modal.classList.contains('hidden') && 
                         !modal.classList.contains('d-none') &&
                         modal.style.display !== 'none';
        if (isVisible) {
            modal.dataset.focusTrapInitialized = 'true';
            trapFocus(modal);
        }
    });
}

// Close modal on ESC key
function initModalEscapeKey() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal:not(.hidden), [role="dialog"]:not(.hidden)');
            modals.forEach(modal => {
                const closeButton = modal.querySelector('[data-modal-close], .modal-close, [aria-label="Close"]');
                if (closeButton) {
                    closeButton.click();
                }
            });
        }
    });
}

// ARIA live region for announcements
function createLiveRegion() {
    let liveRegion = document.getElementById('aria-live-region');
    if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'aria-live-region';
        liveRegion.setAttribute('role', 'status');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
        document.body.appendChild(liveRegion);
    }
    return liveRegion;
}

// Announce message to screen readers
function announceToScreenReader(message, priority = 'polite') {
    const liveRegion = createLiveRegion();
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.textContent = message;
    
    // Clear after announcement
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
}

// Fix tab order in forms
function fixFormTabOrder() {
    const forms = document.querySelectorAll('form');
    forms.forEach((form, formIndex) => {
        const focusableElements = form.querySelectorAll(
            'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        
        focusableElements.forEach((element, index) => {
            // Only set tabindex if it's not already set or if order seems wrong
            if (!element.hasAttribute('tabindex') || element.tabIndex !== (formIndex * 1000 + index + 1)) {
                element.tabIndex = formIndex * 1000 + index + 1;
            }
        });
    });
}

// Initialize all accessibility features
document.addEventListener('DOMContentLoaded', function() {
    initSkipLink();
    initModalFocusTrap();
    initModalEscapeKey();
    fixFormTabOrder();
    
    // Add keyboard shortcut hints
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search (if search exists)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            const searchInput = document.querySelector('input[type="search"], #search-input');
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
            }
        }
    });
});

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        trapFocus,
        announceToScreenReader,
        createLiveRegion
    };
}


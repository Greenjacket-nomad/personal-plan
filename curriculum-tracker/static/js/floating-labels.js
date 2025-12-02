/**
 * Floating Labels System
 * Handles floating label animations for form fields
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize floating labels for all form fields
    initFloatingLabels();
    
    // Handle dynamic form field additions
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    const formFields = node.querySelectorAll ? node.querySelectorAll('.form-field-container') : [];
                    formFields.forEach(initField);
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

function initFloatingLabels() {
    const formFields = document.querySelectorAll('.form-field-container');
    formFields.forEach(initField);
}

function initField(container) {
    const input = container.querySelector('.form-input');
    const label = container.querySelector('.form-label');
    
    if (!input || !label) return;
    
    // Check if field has value on load
    if (input.value && input.value.trim() !== '') {
        label.classList.add('form-label-floating');
    }
    
    // Handle focus
    input.addEventListener('focus', function() {
        label.classList.add('form-label-floating');
        container.classList.add('form-field-focused');
    });
    
    // Handle blur
    input.addEventListener('blur', function() {
        container.classList.remove('form-field-focused');
        if (!input.value || input.value.trim() === '') {
            label.classList.remove('form-label-floating');
        }
    });
    
    // Handle input (for real-time updates)
    input.addEventListener('input', function() {
        if (input.value && input.value.trim() !== '') {
            label.classList.add('form-label-floating');
        } else {
            label.classList.remove('form-label-floating');
        }
    });
    
    // Handle validation state changes
    input.addEventListener('invalid', function() {
        container.classList.add('form-field-invalid');
    });
    
    input.addEventListener('input', function() {
        if (input.validity.valid) {
            container.classList.remove('form-field-invalid');
        }
    });
}

// Export for use in other scripts
window.initFloatingLabels = initFloatingLabels;


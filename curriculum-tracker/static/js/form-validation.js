// Enhanced Form Validation with Better UX
// Provides inline error messages, ARIA support, and visual feedback

// Create ARIA live region for error announcements
function createAriaLiveRegion() {
    let liveRegion = document.getElementById('aria-live-errors');
    if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'aria-live-errors';
        liveRegion.setAttribute('role', 'alert');
        liveRegion.setAttribute('aria-live', 'assertive');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        document.body.appendChild(liveRegion);
    }
    return liveRegion;
}

// Validate a single field
function validateField(field) {
    const fieldId = field.id || field.name;
    const errorId = `error-${fieldId}`;
    let errorElement = document.getElementById(errorId);
    
    // Remove existing error styling
    field.classList.remove('field-error');
    field.setAttribute('aria-invalid', 'false');
    
    // Remove existing error message
    if (errorElement) {
        errorElement.remove();
    }
    
    // Check if field is required
    if (field.hasAttribute('required') && !field.value.trim()) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Check email format
    if (field.type === 'email' && field.value && !isValidEmail(field.value)) {
        showFieldError(field, 'Please enter a valid email address');
        return false;
    }
    
    // Check URL format
    if (field.type === 'url' && field.value && !isValidUrl(field.value)) {
        showFieldError(field, 'Please enter a valid URL');
        return false;
    }
    
    // Check min/max length
    if (field.hasAttribute('minlength')) {
        const minLength = parseInt(field.getAttribute('minlength'));
        if (field.value.length < minLength) {
            showFieldError(field, `Please enter at least ${minLength} characters`);
            return false;
        }
    }
    
    if (field.hasAttribute('maxlength')) {
        const maxLength = parseInt(field.getAttribute('maxlength'));
        if (field.value.length > maxLength) {
            showFieldError(field, `Please enter no more than ${maxLength} characters`);
            return false;
        }
    }
    
    // Check number range
    if (field.type === 'number') {
        const min = field.getAttribute('min');
        const max = field.getAttribute('max');
        const value = parseFloat(field.value);
        
        if (min !== null && value < parseFloat(min)) {
            showFieldError(field, `Value must be at least ${min}`);
            return false;
        }
        
        if (max !== null && value > parseFloat(max)) {
            showFieldError(field, `Value must be at most ${max}`);
            return false;
        }
    }
    
    // Field is valid
    field.setAttribute('aria-invalid', 'false');
    return true;
}

// Show error for a field
function showFieldError(field, message) {
    const fieldId = field.id || field.name;
    const errorId = `error-${fieldId}`;
    
    // Add error styling
    field.classList.add('field-error');
    field.setAttribute('aria-invalid', 'true');
    field.setAttribute('aria-describedby', errorId);
    
    // Create error message element
    const errorElement = document.createElement('div');
    errorElement.id = errorId;
    errorElement.className = 'field-error-message';
    errorElement.setAttribute('role', 'alert');
    errorElement.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>${message}`;
    
    // Insert error message after field
    field.parentNode.insertBefore(errorElement, field.nextSibling);
    
    // Announce to screen readers
    const liveRegion = createAriaLiveRegion();
    liveRegion.textContent = `${field.labels?.[0]?.textContent || field.name || 'Field'}: ${message}`;
    
    // Clear announcement after a moment
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
}

// Validate entire form
function validateForm(form) {
    const fields = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
    let isValid = true;
    let firstInvalidField = null;
    
    // Clear previous errors
    form.querySelectorAll('.field-error-message').forEach(el => el.remove());
    form.querySelectorAll('.field-error').forEach(el => {
        el.classList.remove('field-error');
        el.setAttribute('aria-invalid', 'false');
        el.removeAttribute('aria-describedby');
    });
    
    // Validate each field
    fields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
            if (!firstInvalidField) {
                firstInvalidField = field;
            }
        }
    });
    
    // Scroll to first invalid field
    if (!isValid && firstInvalidField) {
        firstInvalidField.focus();
        firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Announce error summary
        const liveRegion = createAriaLiveRegion();
        const errorCount = form.querySelectorAll('.field-error').length;
        liveRegion.textContent = `Form has ${errorCount} error${errorCount > 1 ? 's' : ''}. Please review and correct.`;
        
        setTimeout(() => {
            liveRegion.textContent = '';
        }, 2000);
    }
    
    return isValid;
}

// Helper functions
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

// Initialize form validation on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add validation to all forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        // Validate on submit
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });
        
        // Real-time validation on blur
        const fields = form.querySelectorAll('input, textarea, select');
        fields.forEach(field => {
            field.addEventListener('blur', function() {
                validateField(field);
            });
            
            // Clear errors on input
            field.addEventListener('input', function() {
                if (field.classList.contains('field-error')) {
                    const fieldId = field.id || field.name;
                    const errorId = `error-${fieldId}`;
                    const errorElement = document.getElementById(errorId);
                    if (errorElement) {
                        errorElement.remove();
                    }
                    field.classList.remove('field-error');
                    field.setAttribute('aria-invalid', 'false');
                    field.removeAttribute('aria-describedby');
                }
            });
        });
    });
});

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.validateForm = validateForm;
    window.validateField = validateField;
    window.showFieldError = showFieldError;
}


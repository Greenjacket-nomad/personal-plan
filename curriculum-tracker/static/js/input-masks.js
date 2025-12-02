// Input Masks for Formatted Fields
// Provides automatic formatting for dates, phone numbers, etc.

/**
 * Apply input mask to an input field
 * @param {HTMLInputElement} input - The input element to mask
 * @param {string} pattern - The mask pattern (e.g., 'MM/DD/YYYY', '(###) ###-####')
 */
function applyInputMask(input, pattern) {
    if (!input || !pattern) return;
    
    // Remove existing mask listener
    if (input.dataset.masked) {
        input.removeEventListener('input', input._maskHandler);
    }
    
    input.dataset.masked = 'true';
    input.classList.add('input-masked');
    
    const maskHandler = function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
        let formatted = '';
        let valueIndex = 0;
        
        for (let i = 0; i < pattern.length && valueIndex < value.length; i++) {
            if (pattern[i] === '#') {
                formatted += value[valueIndex++];
            } else if (pattern[i] === 'M' || pattern[i] === 'D' || pattern[i] === 'Y') {
                // Date pattern
                if (pattern[i] === 'M') {
                    formatted += value[valueIndex++];
                } else if (pattern[i] === 'D') {
                    formatted += value[valueIndex++];
                } else if (pattern[i] === 'Y') {
                    formatted += value[valueIndex++];
                }
            } else {
                formatted += pattern[i];
            }
        }
        
        e.target.value = formatted;
    };
    
    input._maskHandler = maskHandler;
    input.addEventListener('input', maskHandler);
    
    // Handle paste
    input.addEventListener('paste', function(e) {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        // Simulate typing
        for (let char of pasted) {
            input.value += char;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    });
}

/**
 * Apply date mask (MM/DD/YYYY)
 */
function applyDateMask(input) {
    applyInputMask(input, 'MM/DD/YYYY');
}

/**
 * Apply phone mask ((###) ###-####)
 */
function applyPhoneMask(input) {
    applyInputMask(input, '(###) ###-####');
}

/**
 * Apply time mask (##:##)
 */
function applyTimeMask(input) {
    applyInputMask(input, '##:##');
}

/**
 * Initialize all input masks on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Date inputs
    document.querySelectorAll('input[type="date"], input[data-mask="date"]').forEach(input => {
        if (input.type === 'text' || input.hasAttribute('data-mask')) {
            applyDateMask(input);
        }
    });
    
    // Phone inputs
    document.querySelectorAll('input[type="tel"], input[data-mask="phone"]').forEach(input => {
        applyPhoneMask(input);
    });
    
    // Time inputs
    document.querySelectorAll('input[type="time"], input[data-mask="time"]').forEach(input => {
        if (input.type === 'text' || input.hasAttribute('data-mask')) {
            applyTimeMask(input);
        }
    });
    
    // Custom masks
    document.querySelectorAll('[data-mask]').forEach(input => {
        const mask = input.getAttribute('data-mask');
        if (mask && mask !== 'date' && mask !== 'phone' && mask !== 'time') {
            applyInputMask(input, mask);
        }
    });
});

// Export for global access
window.applyInputMask = applyInputMask;
window.applyDateMask = applyDateMask;
window.applyPhoneMask = applyPhoneMask;
window.applyTimeMask = applyTimeMask;


/**
 * Password Strength Indicator
 * Provides visual feedback on password strength
 */

function checkPasswordStrength(password) {
    if (!password) return { strength: 0, label: '', color: '' };
    
    let strength = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 8) strength += 1;
    else feedback.push('At least 8 characters');
    
    if (password.length >= 12) strength += 1;
    
    // Character variety
    if (/[a-z]/.test(password)) strength += 1;
    else feedback.push('lowercase letters');
    
    if (/[A-Z]/.test(password)) strength += 1;
    else feedback.push('uppercase letters');
    
    if (/[0-9]/.test(password)) strength += 1;
    else feedback.push('numbers');
    
    if (/[^a-zA-Z0-9]/.test(password)) strength += 1;
    else feedback.push('special characters');
    
    // Determine strength level
    let label, color;
    if (strength <= 2) {
        label = 'Weak';
        color = 'var(--error)';
    } else if (strength <= 4) {
        label = 'Fair';
        color = 'var(--warning)';
    } else if (strength <= 5) {
        label = 'Good';
        color = 'var(--info)';
    } else {
        label = 'Strong';
        color = 'var(--success)';
    }
    
    return { strength, label, color, feedback };
}

function updatePasswordStrengthIndicator(password) {
    const indicator = document.getElementById('password-strength');
    if (!indicator) return;
    
    if (!password) {
        indicator.innerHTML = '';
        return;
    }
    
    const result = checkPasswordStrength(password);
    
    // Create strength bar
    const percentage = (result.strength / 6) * 100;
    
    indicator.innerHTML = `
        <div class="password-strength-bar">
            <div class="password-strength-fill" style="width: ${percentage}%; background: ${result.color};"></div>
        </div>
        <div class="password-strength-label" style="color: ${result.color};">
            ${result.label}
        </div>
        ${result.feedback.length > 0 ? `
            <div class="password-strength-feedback">
                Add: ${result.feedback.slice(0, 2).join(', ')}
            </div>
        ` : ''}
    `;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            updatePasswordStrengthIndicator(this.value);
        });
    }
});

// Export for global access
window.checkPasswordStrength = checkPasswordStrength;
window.updatePasswordStrengthIndicator = updatePasswordStrengthIndicator;


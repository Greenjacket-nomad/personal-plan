// Micro-celebrations for accomplishments
// Uses Font Awesome icons, no emojis

// Check if celebrations are enabled
function celebrationsEnabled() {
    return localStorage.getItem('celebrationsEnabled') !== 'false';
}

// Confetti burst
function confetti(intensity = 'small') {
    if (!celebrationsEnabled()) return;
    
    // Simple confetti using canvas or CSS
    // For now, use a simple visual effect
    const colors = ['var(--accent)', 'var(--success)', 'var(--warning)', 'var(--phase-1)', 'var(--phase-2)'];
    const particleCount = intensity === 'small' ? 20 : intensity === 'medium' ? 50 : 100;
    
    // Create temporary confetti elements
    for (let i = 0; i < particleCount; i++) {
        const confetti = document.createElement('div');
        confetti.style.position = 'fixed';
        confetti.style.left = Math.random() * 100 + '%';
        confetti.style.top = '-10px';
        confetti.style.width = '10px';
        confetti.style.height = '10px';
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.borderRadius = '50%';
        confetti.style.pointerEvents = 'none';
        confetti.style.zIndex = '9999';
        confetti.style.transition = 'all 1s ease-out';
        document.body.appendChild(confetti);
        
        setTimeout(() => {
            confetti.style.top = '100vh';
            confetti.style.transform = `translateX(${(Math.random() - 0.5) * 200}px) rotate(${Math.random() * 360}deg)`;
            confetti.style.opacity = '0';
        }, 10);
        
        setTimeout(() => confetti.remove(), 1100);
    }
}

// Checkmark animation
function animateCheck(element) {
    if (!celebrationsEnabled()) return;
    element.classList.add('check-animate');
    setTimeout(() => element.classList.remove('check-animate'), 600);
}

// Card glow effect
function glowCard(element) {
    if (!celebrationsEnabled()) return;
    element.classList.add('glow-success');
    setTimeout(() => element.classList.remove('glow-success'), 1000);
}

// Toast notification with Font Awesome icon
function showToast(message, type = 'success', icon = null) {
    if (!celebrationsEnabled()) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let content = message;
    if (icon) {
        content += ` <i class="fas fa-${icon}"></i>`;
    }
    toast.innerHTML = content;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Streak pulse
function pulseStreak(element) {
    if (!celebrationsEnabled()) return;
    element.classList.add('pulse');
    setTimeout(() => element.classList.remove('pulse'), 500);
}

// Slide in animation
function slideIn(element) {
    if (!celebrationsEnabled()) return;
    element.classList.add('slide-in');
    setTimeout(() => element.classList.remove('slide-in'), 300);
}


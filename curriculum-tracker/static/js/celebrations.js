/**
 * Celebration System for Milestones
 * Handles confetti, badges, and achievement animations
 */

// Simple confetti implementation
function createConfetti() {
    const colors = ['#0066ff', '#16a34a', '#ca8a04', '#dc2626', '#7c3aed'];
    const confettiCount = 100;
    const duration = 3000;
    
    for (let i = 0; i < confettiCount; i++) {
        setTimeout(() => {
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
            confetti.style.opacity = '0.8';
            
            document.body.appendChild(confetti);
            
            const animation = confetti.animate([
                { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                { transform: `translateY(${window.innerHeight + 100}px) rotate(720deg)`, opacity: 0 }
            ], {
                duration: duration + Math.random() * 1000,
                easing: 'cubic-bezier(0.5, 0, 0.5, 1)'
            });
            
            animation.onfinish = () => confetti.remove();
        }, i * 10);
    }
}

function showMilestoneBadge(type, data) {
    const badge = document.createElement('div');
    badge.className = 'milestone-badge';
    badge.innerHTML = `
        <div class="milestone-badge-content">
            <div class="milestone-icon">
                <i class="fas ${getMilestoneIcon(type)}"></i>
            </div>
            <h3>${getMilestoneTitle(type)}</h3>
            <p>${getMilestoneMessage(type, data)}</p>
            <div class="milestone-actions">
                <button onclick="shareMilestone('${type}', ${JSON.stringify(data).replace(/"/g, '&quot;')})" class="btn-secondary btn-sm">
                    <i class="fas fa-share mr-1"></i>Share
                </button>
                <button onclick="this.closest('.milestone-badge').remove()" class="btn-secondary btn-sm">
                    Dismiss
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(badge);
    
    // Animate in
    setTimeout(() => badge.classList.add('active'), 100);
    
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
        badge.classList.remove('active');
        setTimeout(() => badge.remove(), 500);
    }, 8000);
}

function getMilestoneIcon(type) {
    const icons = {
        'streak': 'fa-fire',
        'completion': 'fa-trophy',
        'hours': 'fa-clock',
        'module': 'fa-graduation-cap'
    };
    return icons[type] || 'fa-star';
}

function getMilestoneTitle(type) {
    const titles = {
        'streak': '🔥 Streak Milestone!',
        'completion': '🎉 Achievement Unlocked!',
        'hours': '⏰ Time Milestone!',
        'module': '📚 Module Complete!'
    };
    return titles[type] || '🎊 Milestone Achieved!';
}

function getMilestoneMessage(type, data) {
    if (type === 'streak') {
        return `You've maintained a ${data.days}-day learning streak! Keep it up!`;
    } else if (type === 'completion') {
        return `You've completed ${data.count} items! Amazing progress!`;
    } else if (type === 'hours') {
        return `You've logged ${data.hours} hours of learning!`;
    } else if (type === 'module') {
        return `You've completed ${data.module}! Well done!`;
    }
    return 'Congratulations on reaching this milestone!';
}

function shareMilestone(type, data) {
    const text = getMilestoneMessage(type, data);
    if (navigator.share) {
        navigator.share({
            title: getMilestoneTitle(type),
            text: text
        });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(`${getMilestoneTitle(type)} - ${text}`);
        if (typeof showToast === 'function') {
            showToast('Copied to clipboard!', 'success');
        }
    }
}

function celebrateMilestone(type, data) {
    createConfetti();
    showMilestoneBadge(type, data);
}

// Check for milestones on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check streak milestones
    const streakElement = document.querySelector('[data-streak]');
    if (streakElement) {
        const streak = parseInt(streakElement.dataset.streak);
        if (streak > 0 && streak % 7 === 0) {
            celebrateMilestone('streak', { days: streak });
        }
    }
    
    // Check for milestone data passed from backend
    if (window.milestoneData) {
        celebrateMilestone(window.milestoneData.type, window.milestoneData.data);
    }
});

// Export for global access
window.celebrateMilestone = celebrateMilestone;
window.shareMilestone = shareMilestone;


// Mobile Experience Improvements
// Handles header hide on scroll, swipe gestures, and mobile optimizations

let lastScrollTop = 0;
let scrollTimeout;

// Header hide on scroll down, show on scroll up
function handleHeaderScroll() {
    const header = document.querySelector('.header');
    if (!header || window.innerWidth > 768) return;
    
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    
    if (scrollTop > lastScrollTop && scrollTop > 100) {
        // Scrolling down
        header.classList.add('hidden');
    } else {
        // Scrolling up
        header.classList.remove('hidden');
    }
    
    lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
}

// Throttle scroll events
window.addEventListener('scroll', function() {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(handleHeaderScroll, 10);
}, { passive: true });

// Mobile menu swipe to close
function initMobileMenuSwipe() {
    const mobileMenu = document.getElementById('mobile-menu');
    const overlay = document.querySelector('.mobile-menu-overlay');
    
    if (!mobileMenu || window.innerWidth > 768) return;
    
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    
    mobileMenu.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });
    
    mobileMenu.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Swipe right to close (if menu is open)
        if (Math.abs(deltaX) > Math.abs(deltaY) && deltaX > 50 && !mobileMenu.classList.contains('hidden')) {
            toggleMobileMenu();
        }
    }
    
    // Close on overlay tap
    if (overlay) {
        overlay.addEventListener('click', function() {
            if (!mobileMenu.classList.contains('hidden')) {
                toggleMobileMenu();
            }
        });
    }
}

// Enhanced mobile menu toggle
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    const overlay = document.querySelector('.mobile-menu-overlay');
    
    if (!menu) return;
    
    const isHidden = menu.classList.contains('hidden');
    
    if (isHidden) {
        menu.classList.remove('hidden');
        if (overlay) {
            overlay.classList.add('show');
        }
        document.body.style.overflow = 'hidden';
    } else {
        menu.classList.add('hidden');
        if (overlay) {
            overlay.classList.remove('show');
        }
        document.body.style.overflow = '';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenuSwipe();
    
    // Ensure touch targets are minimum size
    document.querySelectorAll('button, a, input[type="checkbox"], input[type="radio"]').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width < 44 || rect.height < 44) {
            el.style.minWidth = '44px';
            el.style.minHeight = '44px';
        }
    });
});

// Export for global access
window.toggleMobileMenu = toggleMobileMenu;


// Lazy Loading for Images
// Implements lazy loading for images and content below the fold

function initLazyLoading() {
    // Use native lazy loading if supported
    if ('loading' in HTMLImageElement.prototype) {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
            img.loading = 'lazy';
            img.classList.add('lazy-load');
            img.onload = function() {
                this.classList.add('loaded');
            };
        });
    } else {
        // Fallback: Intersection Observer
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('lazy-load');
                    img.onload = function() {
                        this.classList.add('loaded');
                    };
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Lazy load content sections
    const contentObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('loaded');
                contentObserver.unobserve(entry.target);
            }
        });
    }, {
        rootMargin: '50px'
    });
    
    document.querySelectorAll('.lazy-load').forEach(element => {
        if (element.tagName !== 'IMG') {
            contentObserver.observe(element);
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initLazyLoading);


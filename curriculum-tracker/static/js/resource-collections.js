/**
 * Resource Collections System
 * Handles creating, organizing, and filtering resources by collections
 */

let collections = [];
let activeCollectionId = null;

function loadCollections() {
    fetch('/api/collections')
        .then(response => response.json())
        .then(data => {
            collections = data.collections || [];
            renderCollections();
        })
        .catch(error => {
            console.error('Error loading collections:', error);
            collections = getMockCollections();
            renderCollections();
        });
}

function renderCollections() {
    const list = document.getElementById('collections-list');
    if (!list) return;
    
    if (collections.length === 0) {
        list.innerHTML = `
            <div class="collections-empty">
                <p class="text-sm text-muted">No collections yet. Create one to organize your resources!</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = collections.map(collection => {
        const isActive = activeCollectionId === collection.id;
        return `
            <div class="collection-item ${isActive ? 'active' : ''}" 
                 onclick="selectCollection(${collection.id})">
                <div class="collection-color" style="background: ${collection.color}"></div>
                <div class="collection-name">${escapeHtml(collection.name)}</div>
                <div class="collection-count">${collection.resource_count || 0}</div>
            </div>
        `;
    }).join('');
}

function selectCollection(collectionId) {
    activeCollectionId = collectionId;
    renderCollections();
    filterResourcesByCollection(collectionId);
}

function filterResourcesByCollection(collectionId) {
    const resourceCards = document.querySelectorAll('.resource-card');
    resourceCards.forEach(card => {
        const cardCollections = card.dataset.collections ? card.dataset.collections.split(',') : [];
        if (collectionId === null || cardCollections.includes(collectionId.toString())) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

function showCreateCollectionModal() {
    if (typeof showModal === 'function') {
        showModal('create-collection-modal');
    } else if (typeof openModal === 'function') {
        openModal('create-collection-modal');
    } else {
        const modal = document.getElementById('create-collection-modal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('show');
        }
    }
}

function hideCreateCollectionModal() {
    if (typeof closeModal === 'function') {
        closeModal('create-collection-modal');
    } else {
        const modal = document.getElementById('create-collection-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('show');
        }
    }
    const form = document.getElementById('create-collection-form');
    if (form) {
        form.reset();
    }
}

function toggleCollectionsSidebar() {
    const sidebar = document.querySelector('.resource-collections-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('hidden');
    }
}

// Handle form submission
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('create-collection-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const collection = {
                name: document.getElementById('collection-name').value,
                description: document.getElementById('collection-description').value,
                color: document.getElementById('collection-color').value
            };
            
            fetch('/api/collections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(collection)
            })
                .then(response => response.json())
                .then(data => {
                    loadCollections();
                    hideCreateCollectionModal();
                    if (typeof showToast === 'function') {
                        showToast('Collection created successfully', 'success');
                    }
                })
                .catch(error => {
                    console.error('Error creating collection:', error);
                    if (typeof showToast === 'function') {
                        showToast('Failed to create collection', 'error');
                    }
                });
        });
    }
    
    if (document.getElementById('collections-list')) {
        loadCollections();
    }
});

function getMockCollections() {
    return [
        {
            id: 1,
            name: 'React Resources',
            description: 'All React-related learning materials',
            color: '#61dafb',
            resource_count: 12
        },
        {
            id: 2,
            name: 'Backend Development',
            description: 'Server-side resources',
            color: '#339933',
            resource_count: 8
        },
        {
            id: 3,
            name: 'Favorites',
            description: 'My favorite resources',
            color: '#ffd700',
            resource_count: 5
        }
    ];
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export for global access
window.selectCollection = selectCollection;
window.showCreateCollectionModal = showCreateCollectionModal;
window.hideCreateCollectionModal = hideCreateCollectionModal;
window.toggleCollectionsSidebar = toggleCollectionsSidebar;


/**
 * Resource Preview Modal Integration
 * Handles opening and populating resource preview modals
 */

function openResourcePreview(resourceId) {
    // Fetch resource data
    fetch(`/api/resources/${resourceId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                if (typeof showToast === 'function') {
                    showToast('Failed to load resource preview', 'error');
                }
                return;
            }
            
            populatePreviewModal(data);
            openModal('resource-preview-modal');
        })
        .catch(error => {
            console.error('Error fetching resource:', error);
            if (typeof showToast === 'function') {
                showToast('Failed to load resource preview', 'error');
            }
        });
}

function populatePreviewModal(resource) {
    const modal = document.getElementById('resource-preview-modal');
    if (!modal) return;
    
    // Update modal title
    const titleEl = modal.querySelector('.modal-title');
    if (titleEl) {
        titleEl.textContent = resource.title || 'Resource Preview';
    }
    
    // Populate preview content
    const previewBody = modal.querySelector('.resource-preview-body') || modal.querySelector('.modal-body');
    if (previewBody) {
        let content = '';
        
        // Image preview
        if (resource.resource_type === 'image' && resource.url) {
            content = `
                <div class="resource-preview-image">
                    <img src="${escapeHtml(resource.url)}" alt="${escapeHtml(resource.title)}" loading="lazy">
                </div>
            `;
        }
        // Video preview
        else if (resource.resource_type === 'video' && resource.url) {
            content = `
                <div class="resource-preview-video">
                    <iframe src="${escapeHtml(resource.url)}" frameborder="0" allowfullscreen></iframe>
                </div>
            `;
        }
        // PDF preview
        else if (resource.url && resource.url.toLowerCase().endsWith('.pdf')) {
            content = `
                <div class="resource-preview-pdf">
                    <iframe src="${escapeHtml(resource.url)}" frameborder="0"></iframe>
                </div>
            `;
        }
        // Link preview
        else if (resource.url) {
            content = `
                <div class="resource-preview-link">
                    <a href="${escapeHtml(resource.url)}" target="_blank" rel="noopener noreferrer" class="btn-primary">
                        <i class="fas fa-external-link-alt"></i> Open Link
                    </a>
                </div>
            `;
        }
        
        // Add description
        if (resource.description || resource.notes) {
            content += `
                <div class="resource-preview-description">
                    <h4>Description</h4>
                    <p>${escapeHtml(resource.description || resource.notes || 'No description available')}</p>
                </div>
            `;
        }
        
        // Add metadata
        const tags = resource.tags || [];
        const createdAt = resource.created_at ? new Date(resource.created_at).toLocaleDateString() : 'Unknown';
        
        content += `
            <div class="resource-preview-meta">
                <div class="meta-item">
                    <i class="fas fa-tag"></i>
                    <span>Tags: ${tags.length > 0 ? tags.join(', ') : 'None'}</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-calendar"></i>
                    <span>Added: ${createdAt}</span>
                </div>
                ${resource.resource_type ? `
                <div class="meta-item">
                    <i class="fas fa-file"></i>
                    <span>Type: ${escapeHtml(resource.resource_type)}</span>
                </div>
                ` : ''}
            </div>
        `;
        
        previewBody.innerHTML = content;
    }
    
    // Update footer buttons
    const viewBtn = modal.querySelector('#preview-view-btn');
    const downloadBtn = modal.querySelector('#preview-download-btn');
    const editBtn = modal.querySelector('#preview-edit-btn');
    
    if (viewBtn && resource.url) {
        viewBtn.href = resource.url;
        viewBtn.style.display = '';
    }
    
    if (downloadBtn && resource.url) {
        downloadBtn.href = resource.url;
        downloadBtn.download = resource.title || 'resource';
        downloadBtn.style.display = '';
    }
    
    if (editBtn) {
        editBtn.onclick = () => {
            closeModal('resource-preview-modal');
            // Navigate to edit page or open edit modal
            window.location.href = `/resources#resource-${resource.id}`;
        };
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        // Auto-focus first interactive element
        const firstInput = modal.querySelector('input, button, a');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Add click handlers to resource cards
document.addEventListener('DOMContentLoaded', function() {
    // Add preview button to resource cards
    document.querySelectorAll('.resource-card').forEach(card => {
        const resourceId = card.id.replace('resource-', '');
        if (resourceId) {
            // Add preview button if not exists
            let previewBtn = card.querySelector('.resource-preview-btn');
            if (!previewBtn) {
                previewBtn = document.createElement('button');
                previewBtn.className = 'resource-preview-btn btn-icon';
                previewBtn.innerHTML = '<i class="fas fa-eye"></i>';
                previewBtn.title = 'Preview Resource';
                previewBtn.onclick = (e) => {
                    e.stopPropagation();
                    openResourcePreview(resourceId);
                };
                
                // Insert after favorite button
                const favoriteBtn = card.querySelector('.btn-favorite');
                if (favoriteBtn && favoriteBtn.parentNode) {
                    favoriteBtn.parentNode.insertBefore(previewBtn, favoriteBtn.nextSibling);
                }
            }
        }
    });
});

// Export for global access
window.openResourcePreview = openResourcePreview;
window.openModal = openModal;
window.closeModal = closeModal;


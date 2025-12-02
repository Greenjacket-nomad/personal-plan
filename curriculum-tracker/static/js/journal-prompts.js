/**
 * Journal Prompts and Templates
 * Handles prompt selection and template insertion
 */

let promptsData = null;
let currentCategory = 'all';

async function loadPrompts() {
    try {
        const response = await fetch('/static/data/journal_prompts.json');
        promptsData = await response.json();
        return promptsData;
    } catch (error) {
        console.error('Error loading prompts:', error);
        // Fallback prompts
        promptsData = {
            prompts: [
                {
                    id: "daily-reflection",
                    title: "Daily Reflection",
                    category: "reflection",
                    template: "## What I Learned Today\n\n\n\n## Challenges I Faced\n\n\n\n## Plans for Tomorrow\n\n"
                }
            ],
            categories: []
        };
        return promptsData;
    }
}

function openJournalPrompts() {
    const modal = document.getElementById('journal-prompts-modal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    
    // Load prompts if not loaded
    if (!promptsData) {
        loadPrompts().then(() => {
            renderPrompts();
            renderCategories();
        });
    } else {
        renderPrompts();
        renderCategories();
    }
}

function closeJournalPrompts() {
    if (typeof closeModal === 'function') {
        closeModal('journal-prompts-modal');
    } else {
        const modal = document.getElementById('journal-prompts-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('show');
        }
    }
}

function renderCategories() {
    if (!promptsData || !promptsData.categories) return;
    
    const container = document.querySelector('.prompts-categories');
    if (!container) return;
    
    // Add category buttons (skip "All" as it's already there)
    promptsData.categories.forEach(category => {
        const btn = document.createElement('button');
        btn.className = 'prompt-category-btn';
        btn.dataset.category = category.id;
        btn.innerHTML = `<i class="fas ${category.icon} mr-1"></i>${category.name}`;
        btn.onclick = () => filterPromptsByCategory(category.id);
        container.appendChild(btn);
    });
}

function renderPrompts() {
    if (!promptsData || !promptsData.prompts) return;
    
    const grid = document.getElementById('prompts-grid');
    if (!grid) return;
    
    // Filter prompts by category
    let filteredPrompts = promptsData.prompts;
    if (currentCategory !== 'all') {
        filteredPrompts = promptsData.prompts.filter(p => p.category === currentCategory);
    }
    
    grid.innerHTML = filteredPrompts.map(prompt => {
        const category = promptsData.categories.find(c => c.id === prompt.category);
        return `
            <div class="prompt-card" onclick="selectPrompt('${prompt.id}')">
                <div class="prompt-card-header">
                    <i class="fas ${category ? category.icon : 'fa-file-alt'} prompt-card-icon"></i>
                    <div class="prompt-card-title">${escapeHtml(prompt.title)}</div>
                </div>
                <div class="prompt-card-category">${category ? category.name : prompt.category}</div>
            </div>
        `;
    }).join('');
}

function filterPromptsByCategory(category) {
    currentCategory = category;
    
    // Update active button
    document.querySelectorAll('.prompt-category-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.category === category) {
            btn.classList.add('active');
        }
    });
    
    renderPrompts();
}

function selectPrompt(promptId) {
    const prompt = promptsData.prompts.find(p => p.id === promptId);
    if (!prompt) return;
    
    // Insert template into textarea
    const textarea = document.getElementById('journal-content');
    if (textarea) {
        textarea.value = prompt.template;
        textarea.focus();
        
        // Trigger input event for auto-save
        textarea.dispatchEvent(new Event('input'));
    }
    
    closeJournalPrompts();
    
    if (typeof showToast === 'function') {
        showToast(`Loaded template: ${prompt.title}`, 'success');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('journal-prompts-modal')) {
        loadPrompts();
    }
});

// Export for global access
window.openJournalPrompts = openJournalPrompts;
window.closeJournalPrompts = closeJournalPrompts;
window.filterPromptsByCategory = filterPromptsByCategory;
window.selectPrompt = selectPrompt;


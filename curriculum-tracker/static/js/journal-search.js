/**
 * Advanced Journal Search with Saved Searches
 * Handles full-text search, filters, and saved search presets
 */

let savedSearches = [];
let currentSearchFilters = {
    query: '',
    dateRange: 'all',
    moods: [],
    tags: [],
    wordCountMin: null,
    wordCountMax: null
};

function initializeJournalSearch() {
    // Load saved searches from localStorage
    const saved = localStorage.getItem('journalSavedSearches');
    if (saved) {
        savedSearches = JSON.parse(saved);
        renderSavedSearches();
    }
    
    // Add saved searches UI
    addSavedSearchesUI();
}

function addSavedSearchesUI() {
    const searchBar = document.querySelector('.journal-search-bar');
    if (!searchBar) return;
    
    // Add advanced search toggle
    const advancedToggle = document.createElement('button');
    advancedToggle.className = 'btn-secondary btn-sm mt-2';
    advancedToggle.innerHTML = '<i class="fas fa-sliders-h mr-1"></i>Advanced Search';
    advancedToggle.onclick = toggleAdvancedSearch;
    searchBar.appendChild(advancedToggle);
    
    // Add saved searches dropdown
    const savedSearchesContainer = document.createElement('div');
    savedSearchesContainer.className = 'saved-searches-container';
    savedSearchesContainer.innerHTML = `
        <div class="saved-searches-header">
            <h4>Saved Searches</h4>
            <button class="btn-icon" onclick="this.closest('.saved-searches-container').classList.toggle('expanded')">
                <i class="fas fa-chevron-down"></i>
            </button>
        </div>
        <div class="saved-searches-list" id="saved-searches-list">
            <!-- Saved searches will be populated here -->
        </div>
        <button class="btn-secondary btn-sm w-full mt-2" onclick="showSaveSearchDialog()">
            <i class="fas fa-bookmark mr-1"></i>Save Current Search
        </button>
    `;
    searchBar.appendChild(savedSearchesContainer);
    
    renderSavedSearches();
}

function toggleAdvancedSearch() {
    const panel = document.getElementById('advanced-search-panel');
    if (panel) {
        panel.classList.toggle('hidden');
        return;
    }
    
    // Create advanced search panel
    const panelEl = document.createElement('div');
    panelEl.id = 'advanced-search-panel';
    panelEl.className = 'advanced-search-panel';
    panelEl.innerHTML = `
        <div class="advanced-search-header">
            <h4>Advanced Search</h4>
            <button class="btn-icon" onclick="this.closest('.advanced-search-panel').classList.add('hidden')">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="advanced-search-content">
            <div class="form-field-group">
                <label>Date Range</label>
                <select id="search-date-range" onchange="updateSearchFilters()">
                    <option value="all">All Time</option>
                    <option value="today">Today</option>
                    <option value="week">This Week</option>
                    <option value="month">This Month</option>
                    <option value="year">This Year</option>
                    <option value="custom">Custom Range</option>
                </select>
            </div>
            
            <div class="form-field-group">
                <label>Moods</label>
                <div class="checkbox-group">
                    <label><input type="checkbox" value="great" onchange="updateSearchFilters()"> Great</label>
                    <label><input type="checkbox" value="okay" onchange="updateSearchFilters()"> Okay</label>
                    <label><input type="checkbox" value="struggling" onchange="updateSearchFilters()"> Struggling</label>
                    <label><input type="checkbox" value="fire" onchange="updateSearchFilters()"> Fire</label>
                </div>
            </div>
            
            <div class="form-field-group">
                <label>Word Count Range</label>
                <div class="range-inputs">
                    <input type="number" id="word-count-min" placeholder="Min" onchange="updateSearchFilters()">
                    <span>to</span>
                    <input type="number" id="word-count-max" placeholder="Max" onchange="updateSearchFilters()">
                </div>
            </div>
            
            <div class="advanced-search-actions">
                <button class="btn-secondary" onclick="clearAdvancedSearch()">Clear</button>
                <button class="btn-primary" onclick="applyAdvancedSearch()">Apply</button>
            </div>
        </div>
    `;
    
    document.querySelector('.journal-search-bar').appendChild(panelEl);
}

function updateSearchFilters() {
    const dateRange = document.getElementById('search-date-range')?.value || 'all';
    const moodCheckboxes = document.querySelectorAll('#advanced-search-panel input[type="checkbox"]:checked');
    const moods = Array.from(moodCheckboxes).map(cb => cb.value);
    const wordCountMin = document.getElementById('word-count-min')?.value || null;
    const wordCountMax = document.getElementById('word-count-max')?.value || null;
    
    currentSearchFilters = {
        ...currentSearchFilters,
        dateRange,
        moods,
        wordCountMin: wordCountMin ? parseInt(wordCountMin) : null,
        wordCountMax: wordCountMax ? parseInt(wordCountMax) : null
    };
}

function applyAdvancedSearch() {
    const query = document.getElementById('journal-search')?.value || '';
    currentSearchFilters.query = query;
    
    filterJournalEntries(query);
    applyAdvancedFilters();
}

function applyAdvancedFilters() {
    const entries = document.querySelectorAll('.journal-entry-card');
    let visibleCount = 0;
    
    entries.forEach(entry => {
        let visible = true;
        
        // Date range filter
        if (currentSearchFilters.dateRange !== 'all') {
            const entryDate = new Date(entry.dataset.date);
            const now = new Date();
            const daysDiff = Math.floor((now - entryDate) / (1000 * 60 * 60 * 24));
            
            if (currentSearchFilters.dateRange === 'today' && daysDiff !== 0) {
                visible = false;
            } else if (currentSearchFilters.dateRange === 'week' && daysDiff > 7) {
                visible = false;
            } else if (currentSearchFilters.dateRange === 'month' && daysDiff > 30) {
                visible = false;
            } else if (currentSearchFilters.dateRange === 'year' && daysDiff > 365) {
                visible = false;
            }
        }
        
        // Mood filter
        if (visible && currentSearchFilters.moods.length > 0) {
            const entryMood = entry.dataset.mood;
            if (!currentSearchFilters.moods.includes(entryMood)) {
                visible = false;
            }
        }
        
        // Word count filter
        if (visible && (currentSearchFilters.wordCountMin || currentSearchFilters.wordCountMax)) {
            const wordCount = parseInt(entry.dataset.wordCount) || 0;
            if (currentSearchFilters.wordCountMin && wordCount < currentSearchFilters.wordCountMin) {
                visible = false;
            }
            if (currentSearchFilters.wordCountMax && wordCount > currentSearchFilters.wordCountMax) {
                visible = false;
            }
        }
        
        if (visible) {
            entry.style.display = '';
            visibleCount++;
        } else {
            entry.style.display = 'none';
        }
    });
    
    updateSearchResultCount(visibleCount);
}

function clearAdvancedSearch() {
    currentSearchFilters = {
        query: '',
        dateRange: 'all',
        moods: [],
        tags: [],
        wordCountMin: null,
        wordCountMax: null
    };
    
    document.getElementById('search-date-range').value = 'all';
    document.querySelectorAll('#advanced-search-panel input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.getElementById('word-count-min').value = '';
    document.getElementById('word-count-max').value = '';
    
    // Show all entries
    document.querySelectorAll('.journal-entry-card').forEach(entry => {
        entry.style.display = '';
    });
}

function saveCurrentSearch() {
    const name = prompt('Enter a name for this search:');
    if (!name) return;
    
    const search = {
        id: Date.now().toString(),
        name,
        filters: { ...currentSearchFilters },
        createdAt: new Date().toISOString()
    };
    
    savedSearches.push(search);
    localStorage.setItem('journalSavedSearches', JSON.stringify(savedSearches));
    
    renderSavedSearches();
    
    if (typeof showToast === 'function') {
        showToast(`Search "${name}" saved`, 'success');
    }
}

function loadSavedSearch(searchId) {
    const search = savedSearches.find(s => s.id === searchId);
    if (!search) return;
    
    currentSearchFilters = { ...search.filters };
    
    // Apply filters
    if (currentSearchFilters.query) {
        document.getElementById('journal-search').value = currentSearchFilters.query;
        filterJournalEntries(currentSearchFilters.query);
    }
    
    applyAdvancedFilters();
    
    if (typeof showToast === 'function') {
        showToast(`Loaded search: ${search.name}`, 'success');
    }
}

function deleteSavedSearch(searchId) {
    if (!confirm('Delete this saved search?')) return;
    
    savedSearches = savedSearches.filter(s => s.id !== searchId);
    localStorage.setItem('journalSavedSearches', JSON.stringify(savedSearches));
    
    renderSavedSearches();
}

function renderSavedSearches() {
    const container = document.getElementById('saved-searches-list');
    if (!container) return;
    
    if (savedSearches.length === 0) {
        container.innerHTML = '<p class="text-muted text-sm">No saved searches</p>';
        return;
    }
    
    container.innerHTML = savedSearches.map(search => `
        <div class="saved-search-item">
            <button class="saved-search-name" onclick="loadSavedSearch('${search.id}')">
                <i class="fas fa-bookmark"></i>
                ${escapeHtml(search.name)}
            </button>
            <button class="saved-search-delete" onclick="deleteSavedSearch('${search.id}')" title="Delete">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function updateSearchResultCount(count) {
    const countEl = document.getElementById('search-result-count');
    if (countEl) {
        countEl.textContent = `${count} entries found`;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSaveSearchDialog() {
    saveCurrentSearch();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.journal-search-bar')) {
        initializeJournalSearch();
    }
});

// Export for global access
window.toggleAdvancedSearch = toggleAdvancedSearch;
window.updateSearchFilters = updateSearchFilters;
window.applyAdvancedSearch = applyAdvancedSearch;
window.clearAdvancedSearch = clearAdvancedSearch;
window.saveCurrentSearch = saveCurrentSearch;
window.loadSavedSearch = loadSavedSearch;
window.deleteSavedSearch = deleteSavedSearch;
window.showSaveSearchDialog = showSaveSearchDialog;


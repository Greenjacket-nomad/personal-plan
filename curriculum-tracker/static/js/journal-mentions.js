/**
 * Journal Entry Relationships (@mentions)
 * Handles @mention autocomplete and entry linking
 */

let journalEntriesCache = [];

async function loadJournalEntries() {
    try {
        const response = await fetch('/api/journal/entries');
        if (response.ok) {
            journalEntriesCache = await response.json();
            return journalEntriesCache;
        }
    } catch (error) {
        console.error('Error loading journal entries:', error);
    }
    return [];
}

function initializeMentions() {
    const textarea = document.getElementById('journal-content');
    if (!textarea) return;
    
    // Load entries on focus
    textarea.addEventListener('focus', () => {
        if (journalEntriesCache.length === 0) {
            loadJournalEntries();
        }
    });
    
    // Handle @ mention trigger
    textarea.addEventListener('input', function(e) {
        const cursorPos = this.selectionStart;
        const textBeforeCursor = this.value.substring(0, cursorPos);
        const match = textBeforeCursor.match(/@(\w*)$/);
        
        if (match) {
            showMentionAutocomplete(this, match[1], cursorPos);
        } else {
            hideMentionAutocomplete();
        }
    });
    
    // Hide autocomplete on blur (with delay to allow click)
    textarea.addEventListener('blur', () => {
        setTimeout(hideMentionAutocomplete, 200);
    });
}

function showMentionAutocomplete(textarea, query, cursorPos) {
    // Remove existing autocomplete
    hideMentionAutocomplete();
    
    // Filter entries by query
    const filtered = journalEntriesCache.filter(entry => {
        const searchText = `${entry.date} ${entry.content || ''}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
    }).slice(0, 5);
    
    if (filtered.length === 0) return;
    
    // Create autocomplete dropdown
    const dropdown = document.createElement('div');
    dropdown.id = 'mention-autocomplete';
    dropdown.className = 'mention-autocomplete';
    
    dropdown.innerHTML = filtered.map((entry, index) => {
        const preview = (entry.content || '').substring(0, 50);
        return `
            <div class="mention-item ${index === 0 ? 'selected' : ''}" 
                 data-entry-id="${entry.id}"
                 data-date="${entry.date}"
                 onclick="insertMention(${entry.id}, '${entry.date}')">
                <div class="mention-date">${entry.date}</div>
                <div class="mention-preview">${escapeHtml(preview)}${preview.length < (entry.content || '').length ? '...' : ''}</div>
            </div>
        `;
    }).join('');
    
    // Position dropdown near cursor
    const textareaRect = textarea.getBoundingClientRect();
    dropdown.style.position = 'absolute';
    dropdown.style.top = `${textareaRect.bottom + 5}px`;
    dropdown.style.left = `${textareaRect.left}px`;
    dropdown.style.zIndex = '10000';
    
    document.body.appendChild(dropdown);
    
    // Handle keyboard navigation
    let selectedIndex = 0;
    const handleKeyDown = (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, filtered.length - 1);
            updateSelection();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, 0);
            updateSelection();
        } else if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            insertMention(filtered[selectedIndex].id, filtered[selectedIndex].date);
        } else if (e.key === 'Escape') {
            hideMentionAutocomplete();
        }
    };
    
    textarea.addEventListener('keydown', handleKeyDown);
    dropdown._keyHandler = handleKeyDown;
    
    function updateSelection() {
        dropdown.querySelectorAll('.mention-item').forEach((item, idx) => {
            item.classList.toggle('selected', idx === selectedIndex);
        });
    }
}

function hideMentionAutocomplete() {
    const dropdown = document.getElementById('mention-autocomplete');
    if (dropdown) {
        const textarea = document.getElementById('journal-content');
        if (textarea && dropdown._keyHandler) {
            textarea.removeEventListener('keydown', dropdown._keyHandler);
        }
        dropdown.remove();
    }
}

function insertMention(entryId, date) {
    const textarea = document.getElementById('journal-content');
    if (!textarea) return;
    
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPos);
    const textAfterCursor = textarea.value.substring(cursorPos);
    
    // Find @ mention start
    const mentionStart = textBeforeCursor.lastIndexOf('@');
    if (mentionStart === -1) return;
    
    // Replace @query with @[date]
    const beforeMention = textarea.value.substring(0, mentionStart);
    const afterMention = textarea.value.substring(cursorPos);
    const mentionText = `@[${date}](#entry-${entryId})`;
    
    textarea.value = beforeMention + mentionText + ' ' + afterMention;
    
    // Set cursor after mention
    const newCursorPos = mentionStart + mentionText.length + 1;
    textarea.setSelectionRange(newCursorPos, newCursorPos);
    textarea.focus();
    
    hideMentionAutocomplete();
    
    // Trigger input event
    textarea.dispatchEvent(new Event('input'));
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('journal-content')) {
        initializeMentions();
    }
});

// Export for global access
window.insertMention = insertMention;


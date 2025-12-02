/**
 * Report Customization
 * Allows users to show/hide and reorder report sections
 */

const REPORT_SECTIONS = [
    'summary-statistics',
    'insights-section',
    'phase-chart-section',
    'type-chart-section',
    'week-chart-section',
    'burndown-section'
];

function initializeReportCustomization() {
    // Load saved preferences
    const savedPreferences = localStorage.getItem('reportPreferences');
    if (savedPreferences) {
        const prefs = JSON.parse(savedPreferences);
        applyReportPreferences(prefs);
    }
    
    // Add customization button
    addCustomizationButton();
}

function addCustomizationButton() {
    const header = document.querySelector('.reports-header');
    if (!header) return;
    
    const button = document.createElement('button');
    button.className = 'btn-secondary';
    button.innerHTML = '<i class="fas fa-cog mr-2"></i>Customize';
    button.onclick = toggleCustomizationPanel;
    
    const controls = header.querySelector('.reports-controls');
    if (controls) {
        controls.appendChild(button);
    }
}

function toggleCustomizationPanel() {
    const panel = document.getElementById('report-customization-panel');
    if (panel) {
        panel.classList.toggle('hidden');
        return;
    }
    
    // Create panel
    const panelEl = document.createElement('div');
    panelEl.id = 'report-customization-panel';
    panelEl.className = 'report-customization-panel';
    panelEl.innerHTML = `
        <div class="customization-header">
            <h3>Customize Report</h3>
            <button class="btn-icon" onclick="this.closest('.report-customization-panel').classList.add('hidden')">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="customization-content">
            <h4>Show/Hide Sections</h4>
            <div class="customization-options">
                ${REPORT_SECTIONS.map(section => {
                    const sectionEl = document.getElementById(section) || document.querySelector(`[data-section="${section}"]`);
                    const isVisible = sectionEl ? !sectionEl.classList.contains('hidden') : true;
                    return `
                        <label class="customization-option">
                            <input type="checkbox" data-section="${section}" ${isVisible ? 'checked' : ''} onchange="toggleReportSection('${section}')">
                            <span>${formatSectionName(section)}</span>
                        </label>
                    `;
                }).join('')}
            </div>
            <div class="customization-actions">
                <button class="btn-secondary" onclick="resetReportPreferences()">Reset to Default</button>
                <button class="btn-primary" onclick="saveReportPreferences()">Save Preferences</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(panelEl);
}

function formatSectionName(section) {
    return section
        .replace(/-/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function toggleReportSection(sectionId) {
    const section = document.getElementById(sectionId) || document.querySelector(`[data-section="${sectionId}"]`);
    if (!section) return;
    
    const checkbox = document.querySelector(`input[data-section="${sectionId}"]`);
    if (checkbox && checkbox.checked) {
        section.classList.remove('hidden');
    } else {
        section.classList.add('hidden');
    }
}

function saveReportPreferences() {
    const preferences = {
        sections: {}
    };
    
    REPORT_SECTIONS.forEach(sectionId => {
        const section = document.getElementById(sectionId) || document.querySelector(`[data-section="${sectionId}"]`);
        const checkbox = document.querySelector(`input[data-section="${sectionId}"]`);
        if (section && checkbox) {
            preferences.sections[sectionId] = checkbox.checked;
        }
    });
    
    localStorage.setItem('reportPreferences', JSON.stringify(preferences));
    
    if (typeof showToast === 'function') {
        showToast('Report preferences saved', 'success');
    }
    
    // Close panel
    const panel = document.getElementById('report-customization-panel');
    if (panel) {
        panel.classList.add('hidden');
    }
}

function applyReportPreferences(prefs) {
    if (!prefs || !prefs.sections) return;
    
    Object.keys(prefs.sections).forEach(sectionId => {
        const section = document.getElementById(sectionId) || document.querySelector(`[data-section="${sectionId}"]`);
        if (section) {
            if (prefs.sections[sectionId]) {
                section.classList.remove('hidden');
            } else {
                section.classList.add('hidden');
            }
        }
    });
}

function resetReportPreferences() {
    localStorage.removeItem('reportPreferences');
    
    // Show all sections
    REPORT_SECTIONS.forEach(sectionId => {
        const section = document.getElementById(sectionId) || document.querySelector(`[data-section="${sectionId}"]`);
        if (section) {
            section.classList.remove('hidden');
        }
    });
    
    // Update checkboxes
    document.querySelectorAll('input[data-section]').forEach(checkbox => {
        checkbox.checked = true;
    });
    
    if (typeof showToast === 'function') {
        showToast('Report preferences reset', 'success');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.reports-header')) {
        initializeReportCustomization();
    }
});

// Export for global access
window.toggleReportSection = toggleReportSection;
window.saveReportPreferences = saveReportPreferences;
window.resetReportPreferences = resetReportPreferences;
window.toggleCustomizationPanel = toggleCustomizationPanel;


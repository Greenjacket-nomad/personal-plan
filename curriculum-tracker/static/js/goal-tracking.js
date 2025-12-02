/**
 * Goal Tracking Visualization
 * Displays progress against user-defined goals with thermometers, radial charts, etc.
 */

let goals = [];

function loadGoals() {
    // Fetch goals from API
    fetch('/api/goals')
        .then(response => response.json())
        .then(data => {
            goals = data.goals || [];
            renderGoals();
        })
        .catch(error => {
            console.error('Error loading goals:', error);
            // Use mock data for demo
            goals = getMockGoals();
            renderGoals();
        });
}

function renderGoals() {
    const grid = document.getElementById('goals-grid');
    if (!grid) return;
    
    if (goals.length === 0) {
        grid.innerHTML = `
            <div class="goal-empty">
                <i class="fas fa-bullseye"></i>
                <p>No goals set yet</p>
                <button class="btn-primary mt-4" onclick="toggleGoalSettings()">
                    Set Your First Goal
                </button>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = goals.map(goal => {
        const progress = calculateProgress(goal);
        const percentage = Math.min(100, (progress.current / goal.target) * 100);
        
        return `
            <div class="goal-card">
                <div class="goal-header">
                    <div class="goal-title">${escapeHtml(goal.name)}</div>
                    <button class="btn-icon" onclick="editGoal(${goal.id})" title="Edit goal">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
                
                <div class="goal-progress">
                    ${goal.visualization_type === 'thermometer' ? renderThermometer(percentage) : ''}
                    ${goal.visualization_type === 'radial' ? renderRadial(percentage) : ''}
                    ${goal.visualization_type === 'bar' ? renderProgressBar(progress, goal) : ''}
                </div>
                
                <div class="goal-stats">
                    <div class="goal-stat">
                        <div class="goal-stat-value">${progress.current}</div>
                        <div class="goal-stat-label">Current</div>
                    </div>
                    <div class="goal-stat">
                        <div class="goal-stat-value">${goal.target}</div>
                        <div class="goal-stat-label">Target</div>
                    </div>
                    <div class="goal-stat">
                        <div class="goal-stat-value">${goal.target - progress.current}</div>
                        <div class="goal-stat-label">Remaining</div>
                    </div>
                </div>
                
                ${progress.projection ? `
                    <div class="goal-projection">
                        <p class="text-sm text-secondary">
                            <i class="fas fa-chart-line"></i>
                            At this pace, you'll reach ${progress.projection} by ${goal.deadline || 'your deadline'}
                        </p>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderThermometer(percentage) {
    return `
        <div class="goal-thermometer">
            <div class="goal-thermometer-fill" style="height: ${percentage}%"></div>
        </div>
        <div class="goal-progress-text">
            <span>${percentage.toFixed(1)}% Complete</span>
        </div>
    `;
}

function renderRadial(percentage) {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;
    
    return `
        <div class="goal-radial">
            <svg width="120" height="120">
                <circle cx="60" cy="60" r="${radius}" fill="none" stroke="var(--bg-tertiary)" stroke-width="8"/>
                <circle cx="60" cy="60" r="${radius}" fill="none" 
                        stroke="var(--accent)" stroke-width="8" 
                        stroke-dasharray="${circumference}" 
                        stroke-dashoffset="${offset}"
                        stroke-linecap="round"/>
            </svg>
            <div class="goal-radial-text">
                <div class="goal-radial-value">${percentage.toFixed(0)}%</div>
                <div class="goal-radial-label">Complete</div>
            </div>
        </div>
    `;
}

function renderProgressBar(progress, goal) {
    const percentage = Math.min(100, (progress.current / goal.target) * 100);
    return `
        <div class="goal-progress-bar">
            <div class="goal-progress-fill" style="width: ${percentage}%"></div>
        </div>
        <div class="goal-progress-text">
            <span>${progress.current} / ${goal.target}</span>
            <span>${percentage.toFixed(1)}%</span>
        </div>
    `;
}

function calculateProgress(goal) {
    // This would fetch actual data based on goal type
    // For demo, return mock progress
    const current = Math.floor(Math.random() * goal.target * 0.8);
    const projection = goal.target;
    
    return {
        current,
        target: goal.target,
        projection
    };
}

function toggleGoalSettings() {
    const modal = document.getElementById('goal-settings-modal');
    if (!modal) return;
    
    const isHidden = modal.classList.contains('hidden') || !modal.classList.contains('show');
    
    if (isHidden) {
        // Show modal
        if (typeof showModal === 'function') {
            showModal('goal-settings-modal');
        } else if (typeof openModal === 'function') {
            openModal('goal-settings-modal');
        } else {
            modal.classList.remove('hidden');
            modal.classList.add('show');
        }
        renderGoalSettings();
    } else {
        // Hide modal
        if (typeof closeModal === 'function') {
            closeModal('goal-settings-modal');
        } else {
            modal.classList.add('hidden');
            modal.classList.remove('show');
        }
    }
}

function renderGoalSettings() {
    const content = document.getElementById('goal-settings-content');
    if (!content) return;
    
    content.innerHTML = `
        <form id="goal-form" class="space-y-4">
            <div class="form-field-group">
                <label for="goal-name">Goal Name</label>
                <input type="text" id="goal-name" class="form-input" placeholder="e.g., Complete 50 resources this month" required>
            </div>
            
            <div class="form-field-group">
                <label for="goal-type">Goal Type</label>
                <select id="goal-type" class="form-input" onchange="updateGoalType()">
                    <option value="hours">Total Hours</option>
                    <option value="completions">Resource Completions</option>
                    <option value="streak">Learning Streak</option>
                    <option value="custom">Custom Metric</option>
                </select>
            </div>
            
            <div class="form-field-group">
                <label for="goal-target">Target Value</label>
                <input type="number" id="goal-target" class="form-input" placeholder="e.g., 100" required>
            </div>
            
            <div class="form-field-group">
                <label for="goal-visualization">Visualization Type</label>
                <select id="goal-visualization" class="form-input">
                    <option value="bar">Progress Bar</option>
                    <option value="thermometer">Thermometer</option>
                    <option value="radial">Radial Chart</option>
                </select>
            </div>
            
            <div class="form-field-group">
                <label for="goal-deadline">Deadline (Optional)</label>
                <input type="date" id="goal-deadline" class="form-input">
            </div>
            
            <div class="flex gap-2">
                <button type="submit" class="btn-primary flex-1">Save Goal</button>
                <button type="button" class="btn-secondary" onclick="toggleGoalSettings()">Cancel</button>
            </div>
        </form>
    `;
    
    document.getElementById('goal-form').addEventListener('submit', saveGoal);
}

function saveGoal(e) {
    e.preventDefault();
    
    const goal = {
        name: document.getElementById('goal-name').value,
        type: document.getElementById('goal-type').value,
        target: parseInt(document.getElementById('goal-target').value),
        visualization_type: document.getElementById('goal-visualization').value,
        deadline: document.getElementById('goal-deadline').value || null
    };
    
    fetch('/api/goals', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(goal)
    })
        .then(response => response.json())
        .then(data => {
            loadGoals();
            toggleGoalSettings();
            if (typeof showToast === 'function') {
                showToast('Goal saved successfully', 'success');
            }
        })
        .catch(error => {
            console.error('Error saving goal:', error);
            if (typeof showToast === 'function') {
                showToast('Failed to save goal', 'error');
            }
        });
}

function editGoal(goalId) {
    const goal = goals.find(g => g.id === goalId);
    if (!goal) return;
    
    toggleGoalSettings();
    // Populate form with goal data
    setTimeout(() => {
        document.getElementById('goal-name').value = goal.name;
        document.getElementById('goal-type').value = goal.type;
        document.getElementById('goal-target').value = goal.target;
        document.getElementById('goal-visualization').value = goal.visualization_type;
        if (goal.deadline) {
            document.getElementById('goal-deadline').value = goal.deadline;
        }
    }, 100);
}

function getMockGoals() {
    return [
        {
            id: 1,
            name: 'Complete 50 Resources',
            type: 'completions',
            target: 50,
            visualization_type: 'thermometer',
            deadline: '2024-12-31'
        },
        {
            id: 2,
            name: 'Log 200 Hours',
            type: 'hours',
            target: 200,
            visualization_type: 'radial',
            deadline: '2024-12-31'
        }
    ];
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('goals-grid')) {
        loadGoals();
    }
});

// Export for global access
window.toggleGoalSettings = toggleGoalSettings;
window.editGoal = editGoal;
window.updateGoalType = function() {
    // Update form based on goal type
};


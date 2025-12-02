// Dashboard-specific JavaScript logic
// Extracted from dashboard.html for maintainability

// Load theme before page renders to prevent flash
(function() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
})();

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize burndown chart if data is available
    const burndownChartData = window.burndownChartData;
    if (burndownChartData && burndownChartData.burndown_data && burndownChartData.start_date) {
        initBurndownChart(burndownChartData);
    }
    
    // Initialize celebration triggers
    const currentStreak = window.currentStreak || 0;
    initCelebrations(currentStreak);
});

/**
 * Initialize burndown chart with data from server.
 */
function initBurndownChart(config) {
    const burndownCtx = document.getElementById('burndown-chart');
    if (!burndownCtx || typeof Chart === 'undefined') {
        return;
    }
    
    const burndownData = config.burndown_data;
    const actualData = burndownData.actual || [];
    const startDate = new Date(config.start_date);
    const today = new Date();
    const curriculumDays = config.curriculum_days || 119; // Default: 17 weeks * 7 days
    
    // Generate date labels from start_date
    const dateLabels = [];
    const idealRemaining = [];
    for (let i = 0; i <= curriculumDays; i++) {
        const date = new Date(startDate);
        date.setDate(date.getDate() + i);
        // Format as "Jan 1" or "1/1"
        dateLabels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        idealRemaining.push(burndownData.total - (burndownData.total * i / curriculumDays));
    }
    
    // Map actual data to dates
    const actualDataArray = new Array(curriculumDays + 1).fill(null);
    actualData.forEach(point => {
        const pointDate = new Date(point.date + 'T00:00:00');
        const dayNum = Math.ceil((pointDate - startDate) / (1000 * 60 * 60 * 24));
        if (dayNum >= 0 && dayNum <= curriculumDays) {
            actualDataArray[dayNum] = point.remaining;
        }
    });
    
    const chart = new Chart(burndownCtx, {
        type: 'line',
        data: {
            labels: dateLabels,
            datasets: [{
                label: 'Ideal Progress',
                data: idealRemaining,
                borderColor: 'var(--accent)',
                borderDash: [5, 5],
                borderWidth: 2,
                fill: false,
                pointRadius: 0,
                tension: 0
            }, {
                label: 'Actual Progress',
                data: actualDataArray,
                borderColor: 'var(--success)',
                borderWidth: 2,
                fill: false,
                pointRadius: 4,
                pointBackgroundColor: 'var(--success)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    },
                    beginAtZero: true
                },
                y: {
                    title: {
                        display: true,
                        text: 'Hours Remaining'
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
    
    // Fetch completion progress and add third line
    const totalResources = config.total_resources || 0;
    if (totalResources > 0) {
        fetch('/api/completion-progress')
            .then(r => r.json())
            .then(data => {
                const completionData = new Array(curriculumDays + 1).fill(null);
                data.forEach(point => {
                    const pointDate = new Date(point.date + 'T00:00:00');
                    const dayNum = Math.ceil((pointDate - startDate) / (1000 * 60 * 60 * 24));
                    if (dayNum >= 0 && dayNum <= curriculumDays) {
                        const percentComplete = (point.completed / totalResources) * 100;
                        completionData[dayNum] = percentComplete;
                    }
                });
                
                // Add third dataset
                chart.data.datasets.push({
                    label: 'Curriculum Completion',
                    data: completionData,
                    borderColor: 'var(--warning)',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: 'var(--warning)',
                    tension: 0.1,
                    yAxisID: 'y2'
                });
                
                // Add secondary y-axis for percentage
                chart.options.scales.y2 = {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Completion %'
                    },
                    min: 0,
                    max: 100,
                    grid: {
                        drawOnChartArea: false
                    }
                };
                
                chart.update();
            })
            .catch(err => {
                console.error('Error loading completion progress:', err);
            });
    }
}

/**
 * Initialize celebration animations based on streak.
 */
function initCelebrations(currentStreak) {
    if (currentStreak >= 7 && currentStreak < 30) {
        const streakElement = document.querySelector('[data-streak]');
        if (streakElement && typeof pulseStreak === 'function') {
            pulseStreak(streakElement);
            if (currentStreak === 7) {
                if (typeof showToast === 'function') {
                    showToast('7-day streak! Keep it up!', 'success', 'fire');
                }
                if (typeof confetti === 'function') {
                    confetti('medium');
                }
            }
        }
    }
    
    if (currentStreak >= 30 && currentStreak < 100) {
        const streakElement = document.querySelector('[data-streak]');
        if (streakElement && typeof pulseStreak === 'function') {
            pulseStreak(streakElement);
            if (currentStreak === 30) {
                if (typeof showToast === 'function') {
                    showToast('30 days! Unstoppable!', 'success', 'trophy');
                }
                if (typeof confetti === 'function') {
                    confetti('large');
                }
            }
        }
    }
    
    if (currentStreak >= 100) {
        const streakElement = document.querySelector('[data-streak]');
        if (streakElement && typeof pulseStreak === 'function') {
            pulseStreak(streakElement);
            if (currentStreak === 100) {
                if (typeof showToast === 'function') {
                    showToast('100 days! Legend status!', 'success', 'crown');
                }
                if (typeof confetti === 'function') {
                    confetti('large');
                }
            }
        }
    }
}


/**
 * Mood Calendar Visualization
 * Displays journal entry moods in a calendar grid format
 */

let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

function renderMoodCalendar() {
    const grid = document.getElementById('mood-calendar-grid');
    if (!grid) return;
    
    // Get month/year from window or use current
    if (window.moodCalendarMonth !== null && window.moodCalendarMonth !== undefined) {
        currentMonth = window.moodCalendarMonth;
    }
    if (window.moodCalendarYear !== null && window.moodCalendarYear !== undefined) {
        currentYear = window.moodCalendarYear;
    }
    
    const moodData = window.moodCalendarData || {};
    const firstDay = new Date(currentYear, currentMonth, 1).getDay();
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    
    // Update month/year display
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    const titleElement = document.getElementById('mood-calendar-month-year');
    if (titleElement) {
        titleElement.textContent = `${monthNames[currentMonth]} ${currentYear}`;
    }
    
    // Clear grid
    grid.innerHTML = '';
    
    // Add day labels
    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayLabels.forEach(label => {
        const labelCell = document.createElement('div');
        labelCell.className = 'mood-calendar-day-label';
        labelCell.textContent = label;
        grid.appendChild(labelCell);
    });
    
    // Add empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
        const emptyCell = document.createElement('div');
        emptyCell.className = 'mood-calendar-day empty';
        grid.appendChild(emptyCell);
    }
    
    // Add cells for each day of the month
    for (let day = 1; day <= daysInMonth; day++) {
        const dayCell = document.createElement('div');
        dayCell.className = 'mood-calendar-day';
        dayCell.dataset.day = day;
        dayCell.dataset.date = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        
        // Check if there's mood data for this day
        const dateKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const mood = moodData[dateKey];
        
        if (mood) {
            dayCell.classList.add(`mood-${mood}`);
            dayCell.title = `Mood: ${mood.charAt(0).toUpperCase() + mood.slice(1)}`;
            
            // Add icon
            const icon = document.createElement('i');
            const iconMap = {
                'great': 'fa-smile',
                'okay': 'fa-meh',
                'struggling': 'fa-tired',
                'fire': 'fa-fire-alt'
            };
            icon.className = `fas ${iconMap[mood] || 'fa-circle'}`;
            dayCell.appendChild(icon);
        } else {
            dayCell.classList.add('mood-none');
        }
        
        // Add day number
        const dayNumber = document.createElement('span');
        dayNumber.className = 'mood-calendar-day-number';
        dayNumber.textContent = day;
        dayCell.appendChild(dayNumber);
        
        // Add click handler to view entry
        dayCell.addEventListener('click', () => {
            if (mood) {
                // Navigate to journal entry for this date
                window.location.href = `/journal?date=${dateKey}`;
            }
        });
        
        grid.appendChild(dayCell);
    }
}

function changeMoodCalendarMonth(delta) {
    currentMonth += delta;
    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    } else if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }
    
    // Fetch mood data for new month
    fetchMoodCalendarData(currentYear, currentMonth + 1).then(() => {
        renderMoodCalendar();
    });
}

async function fetchMoodCalendarData(year, month) {
    try {
        const response = await fetch(`/api/journal/mood-calendar?year=${year}&month=${month}`);
        if (response.ok) {
            const data = await response.json();
            window.moodCalendarData = data.moods || {};
            window.moodCalendarMonth = month - 1;
            window.moodCalendarYear = year;
        }
    } catch (error) {
        console.error('Error fetching mood calendar data:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('mood-calendar-grid')) {
        renderMoodCalendar();
    }
});

// Export for global access
window.changeMoodCalendarMonth = changeMoodCalendarMonth;
window.renderMoodCalendar = renderMoodCalendar;


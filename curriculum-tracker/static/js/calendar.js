// Week Calendar Functions
let currentWeekStart = new Date();
let currentMonthView = new Date();

// Set currentWeekStart to start of current week (Monday)
function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    return new Date(d.setDate(diff));
}

currentWeekStart = getWeekStart(new Date());
currentMonthView = new Date();

function renderWeekCalendar() {
    const grid = document.getElementById('week-calendar-grid');
    const weekLabel = document.getElementById('calendar-week-label');
    if (!grid) return;
    
    // Clear grid
    grid.innerHTML = '';
    
    // Add day headers
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    dayNames.forEach(name => {
        const header = document.createElement('div');
        header.className = 'text-center font-semibold text-sm p-2 text-secondary';
        header.textContent = name;
        grid.appendChild(header);
    });
    
    // Get week dates (Monday to Sunday)
    const weekDates = [];
    for (let i = 0; i < 7; i++) {
        const date = new Date(currentWeekStart);
        date.setDate(date.getDate() + i);
        weekDates.push(date);
    }
    
    // Update week label
    const startDate = weekDates[0];
    const endDate = weekDates[6];
    weekLabel.textContent = `${startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
    
    // Create day cells
    weekDates.forEach(date => {
        const dateStr = date.toISOString().split('T')[0];
        const dayNum = date.getDate();
        const dayCell = createDayCell(dateStr, dayNum);
        grid.appendChild(dayCell);
    });
}

function createDayCell(dateStr, dayNum) {
    const cell = document.createElement('div');
    cell.className = 'calendar-day-cell p-3 rounded-lg border cursor-pointer hover:border-accent transition-all';
    cell.onclick = () => openDayModal(dateStr);
    
    // Fetch day data from API
    fetch(`/api/calendar-day/${dateStr}`)
        .then(r => r.json())
        .then(data => {
            let html = `<div class="font-bold text-sm mb-2">${dayNum}</div>`;
            
            // Show curriculum days
            if (data.curriculum_days && data.curriculum_days.length > 0) {
                data.curriculum_days.forEach(cd => {
                    // Get topic from first resource
                    const topic = cd.resources && cd.resources[0] ? cd.resources[0].title : '';
                    html += `<div class="text-xs mt-1 text-primary">
                        <div class="font-semibold">${topic.substring(0, 30)}${topic.length > 30 ? '...' : ''}</div>
                        <div class="text-secondary">${cd.completed_count}/${cd.resource_count} complete</div>
                    </div>`;
                });
            }
            
            // Show hours logged
            if (data.hours > 0) {
                html += `<div class="text-xs mt-2 text-accent font-semibold">${data.hours}h logged</div>`;
            }
            
            // Show blocked indicator
            if (data.blocked) {
                cell.classList.add('calendar-day-blocked');
                html += `<div class="text-xs mt-2 text-error font-semibold">
                    <i class="fas fa-ban mr-1"></i>Blocked
                    ${data.blocked_reason ? `<br>${data.blocked_reason}` : ''}
                </div>`;
            }
            
            cell.innerHTML = html;
            
            // Color code by hours
            if (data.hours >= 4) {
                cell.classList.add('calendar-day-high');
            } else if (data.hours >= 2) {
                cell.classList.add('calendar-day-medium');
            } else if (data.hours > 0) {
                cell.classList.add('calendar-day-low');
            }
        })
        .catch(err => {
            console.error('Error loading day:', err);
            cell.innerHTML = `<div class="font-bold text-sm">${dayNum}</div>`;
        });
    
    return cell;
}

function previousWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() - 7);
    renderWeekCalendar();
}

function nextWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() + 7);
    renderWeekCalendar();
}

function expandToMonth() {
    const weekView = document.getElementById('week-calendar-grid');
    const monthView = document.getElementById('month-calendar-view');
    
    if (weekView && monthView) {
        weekView.style.display = 'none';
        monthView.classList.remove('hidden');
        renderMonthCalendar(currentWeekStart);
    }
}

function collapseToWeek() {
    const weekView = document.getElementById('week-calendar-grid');
    const monthView = document.getElementById('month-calendar-view');
    
    if (weekView && monthView) {
        monthView.classList.add('hidden');
        weekView.style.display = 'grid';
    }
}

function renderMonthCalendar(date) {
    const grid = document.getElementById('month-calendar-grid');
    const monthLabel = document.getElementById('month-label');
    if (!grid || !monthLabel) return;
    
    const year = date.getFullYear();
    const month = date.getMonth();
    
    // Set month label
    monthLabel.textContent = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    
    // Get days in month
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = firstDay.getDay(); // 0 = Sunday
    const daysInMonth = lastDay.getDate();
    
    // Clear grid
    grid.innerHTML = '';
    
    // Add day headers
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayNames.forEach(name => {
        const header = document.createElement('div');
        header.className = 'text-center font-semibold text-sm p-2 text-secondary';
        header.textContent = name;
        grid.appendChild(header);
    });
    
    // Add empty cells before first day
    for (let i = 0; i < startDay; i++) {
        const empty = document.createElement('div');
        grid.appendChild(empty);
    }
    
    // Add days
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const dayCell = createDayCell(dateStr, day);
        grid.appendChild(dayCell);
    }
}

function previousMonth() {
    currentMonthView.setMonth(currentMonthView.getMonth() - 1);
    renderMonthCalendar(currentMonthView);
}

function nextMonth() {
    currentMonthView.setMonth(currentMonthView.getMonth() + 1);
    renderMonthCalendar(currentMonthView);
}

// Day Modal Functions
function openDayModal(dateStr) {
    fetch(`/api/calendar-day/${dateStr}`)
        .then(r => r.json())
        .then(data => {
            // Create or get modal
            let modal = document.getElementById('day-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'day-modal';
                modal.className = 'hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
                modal.onclick = closeDayModal;
                document.body.appendChild(modal);
            }
            
            const modalContent = document.createElement('div');
            modalContent.className = 'card p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto';
            modalContent.onclick = (e) => e.stopPropagation();
            
            const date = new Date(dateStr + 'T00:00:00');
            let html = `
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-primary">${date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</h3>
                    <button onclick="closeDayModal()" class="text-secondary hover:text-primary"><i class="fas fa-times"></i></button>
                </div>
            `;
            
            // Blocked day section
            if (data.blocked) {
                html += `
                    <div class="mb-4 p-3 rounded-lg" style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--error);">
                        <p class="font-semibold text-error mb-2">
                            <i class="fas fa-ban mr-2"></i>This day is blocked
                        </p>
                        ${data.blocked_reason ? `<p class="text-sm text-secondary mb-3">${data.blocked_reason}</p>` : ''}
                        <form onsubmit="unblockDay(event, '${dateStr}')">
                            <button type="submit" class="btn-secondary text-sm">
                                <i class="fas fa-check mr-1"></i>Unblock Day
                            </button>
                        </form>
                    </div>
                `;
            } else {
                html += `
                    <form onsubmit="blockDay(event, '${dateStr}')" class="mb-4">
                        <div class="flex gap-2">
                            <input type="text" name="reason" placeholder="Reason (optional)" class="flex-1">
                            <button type="submit" class="btn-secondary text-sm">Block Day</button>
                        </div>
                    </form>
                `;
            }
            
            // Curriculum days
            if (data.curriculum_days && data.curriculum_days.length > 0) {
                html += '<div class="space-y-4">';
                data.curriculum_days.forEach(cd => {
                    html += `
                        <div class="p-4 rounded-lg border" style="border-left: 4px solid var(--accent); background: var(--bg-tertiary);">
                            <h4 class="font-semibold mb-2 text-primary">
                                Phase ${cd.phase + 1}, Week ${cd.week}, Day ${cd.day}
                            </h4>
                            <p class="text-sm mb-3 text-secondary">
                                ${cd.completed_count}/${cd.resource_count} complete
                            </p>
                    `;
                    if (cd.resources && cd.resources.length > 0) {
                        html += '<ul class="space-y-2">';
                        cd.resources.forEach(r => {
                            const statusIcon = r.status === 'complete' 
                                ? '<i class="fas fa-check-circle text-success"></i>' 
                                : r.status === 'in_progress' 
                                    ? '<i class="fas fa-circle-notch text-warning"></i>' 
                                    : '<i class="far fa-circle text-muted"></i>';
                            html += `
                                <li class="flex items-center gap-2 p-2 rounded bg-secondary">
                                    ${statusIcon}
                                    ${r.url 
                                        ? `<a href="${r.url}" target="_blank" class="flex-1 hover:underline text-accent">${r.title}</a>`
                                        : `<span class="flex-1 text-primary">${r.title}</span>`
                                    }
                                </li>
                            `;
                        });
                        html += '</ul>';
                    }
                    html += '</div>';
                });
                html += '</div>';
            }
            
            // Hours logged
            if (data.hours > 0) {
                html += `
                    <div class="mt-4 pt-4" style="border-top: 1px solid var(--border);">
                        <p class="text-sm text-secondary">
                            <i class="fas fa-clock mr-2"></i>Hours logged: 
                            <span class="font-semibold text-primary">${data.hours}h</span>
                        </p>
                    </div>
                `;
            }
            
            // Quick log time form
            html += `
                <div class="mt-4 p-3 bg-tertiary rounded-lg">
                    <h4 class="font-semibold text-primary mb-2">Quick Log Time</h4>
                    <form onsubmit="quickLogTime(event, '${dateStr}')">
                        <div class="flex gap-2">
                            <input type="number" step="0.25" min="0.25" max="24" 
                                   name="hours" placeholder="Hours" required 
                                   class="flex-1 px-3 py-2 rounded">
                            <input type="text" name="notes" placeholder="Notes (optional)" 
                                   class="flex-1 px-3 py-2 rounded">
                            <button type="submit" class="btn-primary px-4">Log</button>
                        </div>
                    </form>
                </div>
            `;
            
            // Journal entry form
            html += `
                <div class="mt-4 p-3 bg-tertiary rounded-lg">
                    <h4 class="font-semibold text-primary mb-2">Journal Entry</h4>
                    <form onsubmit="quickJournalEntry(event, '${dateStr}')">
                        <textarea name="content" rows="3" placeholder="Reflect on this day..." 
                                  class="w-full px-3 py-2 rounded mb-2"></textarea>
                        <div class="flex items-center justify-between">
                            <div class="flex gap-2 text-2xl">
                                <label class="cursor-pointer">
                                    <input type="radio" name="mood" value="great" class="hidden peer">
                                    <i class="fas fa-smile opacity-40 peer-checked:opacity-100"></i>
                                </label>
                                <label class="cursor-pointer">
                                    <input type="radio" name="mood" value="okay" class="hidden peer">
                                    <i class="fas fa-meh opacity-40 peer-checked:opacity-100"></i>
                                </label>
                                <label class="cursor-pointer">
                                    <input type="radio" name="mood" value="struggling" class="hidden peer">
                                    <i class="fas fa-tired opacity-40 peer-checked:opacity-100"></i>
                                </label>
                                <label class="cursor-pointer">
                                    <input type="radio" name="mood" value="fire" class="hidden peer">
                                    <i class="fas fa-fire-alt opacity-40 peer-checked:opacity-100"></i>
                                </label>
                            </div>
                            <button type="submit" class="btn-primary px-4">Save</button>
                        </div>
                    </form>
                </div>
            `;
            
            modalContent.innerHTML = html;
            modal.innerHTML = '';
            modal.appendChild(modalContent);
            modal.classList.remove('hidden');
        })
        .catch(err => {
            console.error('Error loading day details:', err);
            if (typeof showToast === 'function') {
                showToast('Failed to load day details', 'error');
            }
        });
}

function closeDayModal() {
    const modal = document.getElementById('day-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function quickLogTime(event, dateStr) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    formData.append('date', dateStr);
    
    fetch('/log', {
        method: 'POST',
        body: formData
    })
    .then(r => {
        if (r.ok) {
            if (typeof showToast === 'function') {
                showToast('Time logged successfully!', 'success');
            }
            closeDayModal();
            renderWeekCalendar();
        } else {
            if (typeof showToast === 'function') {
                showToast('Error logging time', 'error');
            }
        }
    })
    .catch(err => {
        console.error('Error:', err);
        if (typeof showToast === 'function') {
            showToast('Failed to log time', 'error');
        }
    });
}

function quickJournalEntry(event, dateStr) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    formData.append('date', dateStr);
    
    fetch('/journal', {
        method: 'POST',
        body: formData
    })
    .then(r => {
        if (r.ok) {
            if (typeof showToast === 'function') {
                showToast('Journal entry saved!', 'success');
            }
            closeDayModal();
        } else {
            if (typeof showToast === 'function') {
                showToast('Error saving entry', 'error');
            }
        }
    })
    .catch(err => {
        console.error('Error:', err);
        if (typeof showToast === 'function') {
            showToast('Failed to save entry', 'error');
        }
    });
}

function blockDay(event, dateStr) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    formData.append('date', dateStr);
    
    fetch('/schedule/block', {
        method: 'POST',
        body: formData
    })
    .then(r => {
        if (r.ok) {
            if (typeof showToast === 'function') {
                showToast('Day blocked successfully!', 'success');
            }
            closeDayModal();
            renderWeekCalendar();
        } else {
            if (typeof showToast === 'function') {
                showToast('Error blocking day', 'error');
            }
        }
    })
    .catch(err => {
        console.error('Error:', err);
        if (typeof showToast === 'function') {
            showToast('Failed to block day', 'error');
        }
    });
}

function unblockDay(event, dateStr) {
    event.preventDefault();
    const formData = new FormData();
    formData.append('date', dateStr);
    
    fetch('/schedule/unblock', {
        method: 'POST',
        body: formData
    })
    .then(r => {
        if (r.ok) {
            if (typeof showToast === 'function') {
                showToast('Day unblocked successfully!', 'success');
            }
            closeDayModal();
            renderWeekCalendar();
        } else {
            if (typeof showToast === 'function') {
                showToast('Error unblocking day', 'error');
            }
        }
    })
    .catch(err => {
        console.error('Error:', err);
        if (typeof showToast === 'function') {
            showToast('Failed to unblock day', 'error');
        }
    });
}

// Block Days Range Modal
function openBlockDaysModal() {
    let modal = document.getElementById('block-days-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'block-days-modal';
        modal.className = 'hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.onclick = closeBlockDaysModal;
        document.body.appendChild(modal);
    }
    
    const modalContent = document.createElement('div');
    modalContent.className = 'card p-6 max-w-md w-full mx-4';
    modalContent.onclick = (e) => e.stopPropagation();
    modalContent.innerHTML = `
        <h3 class="text-xl font-bold text-primary mb-4">Block Days</h3>
        <form onsubmit="blockDaysRange(event)">
            <div class="mb-4">
                <label class="block text-sm text-secondary mb-1">Start Date</label>
                <input type="date" name="start_date" required class="w-full">
            </div>
            <div class="mb-4">
                <label class="block text-sm text-secondary mb-1">End Date</label>
                <input type="date" name="end_date" required class="w-full">
            </div>
            <div class="mb-4">
                <label class="block text-sm text-secondary mb-1">Reason (optional)</label>
                <input type="text" name="reason" placeholder="e.g., Vacation" class="w-full">
            </div>
            <div class="flex gap-3">
                <button type="submit" class="btn-primary flex-1">Block Days</button>
                <button type="button" onclick="closeBlockDaysModal()" class="btn-secondary flex-1">Cancel</button>
            </div>
        </form>
    `;
    modal.innerHTML = '';
    modal.appendChild(modalContent);
    modal.classList.remove('hidden');
}

function closeBlockDaysModal() {
    const modal = document.getElementById('block-days-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function blockDaysRange(event) {
    event.preventDefault();
    const form = event.target;
    const startDate = new Date(form.start_date.value);
    const endDate = new Date(form.end_date.value);
    const reason = form.reason.value;
    
    // Block each day in range
    const currentDate = new Date(startDate);
    const promises = [];
    
    while (currentDate <= endDate) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const formData = new FormData();
        formData.append('date', dateStr);
        formData.append('reason', reason);
        
        promises.push(
            fetch('/schedule/block', {
                method: 'POST',
                body: formData
            })
        );
        
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    Promise.all(promises)
        .then(() => {
            if (typeof showToast === 'function') {
                showToast('Days blocked successfully!', 'success');
            }
            closeBlockDaysModal();
            renderWeekCalendar();
            form.reset();
        })
        .catch(err => {
            console.error('Error:', err);
            if (typeof showToast === 'function') {
                showToast('Failed to block days', 'error');
            }
        });
}

// Initialize calendar on page load
document.addEventListener('DOMContentLoaded', function() {
    renderWeekCalendar();
});


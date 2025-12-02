/**
 * Advanced Table Component
 * Handles sorting, filtering, and responsive card view
 */

class AdvancedTable {
    constructor(tableId, options = {}) {
        this.table = document.getElementById(tableId);
        if (!this.table) return;
        
        this.options = {
            sortable: options.sortable !== false,
            filterable: options.filterable !== false,
            responsive: options.responsive !== false,
            ...options
        };
        
        this.data = [];
        this.currentSort = { column: null, direction: 'asc' };
        this.currentFilters = {};
        
        this.init();
    }
    
    init() {
        // Extract data from table
        this.extractData();
        
        // Add sortable headers
        if (this.options.sortable) {
            this.addSortableHeaders();
        }
        
        // Add filter inputs
        if (this.options.filterable) {
            this.addFilters();
        }
        
        // Add responsive wrapper
        if (this.options.responsive) {
            this.addResponsiveWrapper();
        }
    }
    
    extractData() {
        const rows = this.table.querySelectorAll('tbody tr');
        this.data = Array.from(rows).map(row => {
            const cells = row.querySelectorAll('td');
            const rowData = {};
            cells.forEach((cell, index) => {
                const header = this.table.querySelectorAll('thead th')[index];
                const key = header.dataset.key || header.textContent.trim().toLowerCase().replace(/\s+/g, '_');
                rowData[key] = cell.textContent.trim();
                rowData._element = row;
            });
            return rowData;
        });
    }
    
    addSortableHeaders() {
        const headers = this.table.querySelectorAll('thead th[data-sortable]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.classList.add('sortable-header');
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-sort sort-icon';
            icon.style.marginLeft = '8px';
            icon.style.opacity = '0.3';
            header.appendChild(icon);
            
            header.addEventListener('click', () => {
                const column = header.dataset.key || header.textContent.trim().toLowerCase().replace(/\s+/g, '_');
                this.sort(column);
            });
        });
    }
    
    sort(column) {
        // Toggle direction if same column
        if (this.currentSort.column === column) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.column = column;
            this.currentSort.direction = 'asc';
        }
        
        // Sort data
        this.data.sort((a, b) => {
            let aVal = a[column] || '';
            let bVal = b[column] || '';
            
            // Try numeric comparison
            const aNum = parseFloat(aVal);
            const bNum = parseFloat(bVal);
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.currentSort.direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            aVal = aVal.toString().toLowerCase();
            bVal = bVal.toString().toLowerCase();
            
            if (this.currentSort.direction === 'asc') {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });
        
        // Update table
        this.render();
        this.updateSortIcons();
    }
    
    updateSortIcons() {
        const headers = this.table.querySelectorAll('thead th');
        headers.forEach(header => {
            const icon = header.querySelector('.sort-icon');
            if (icon) {
                const column = header.dataset.key || header.textContent.trim().toLowerCase().replace(/\s+/g, '_');
                if (this.currentSort.column === column) {
                    icon.className = `fas fa-sort-${this.currentSort.direction === 'asc' ? 'up' : 'down'} sort-icon active`;
                    icon.style.opacity = '1';
                } else {
                    icon.className = 'fas fa-sort sort-icon';
                    icon.style.opacity = '0.3';
                }
            }
        });
    }
    
    addFilters() {
        const thead = this.table.querySelector('thead');
        if (!thead) return;
        
        const filterRow = document.createElement('tr');
        filterRow.className = 'filter-row';
        
        const headers = thead.querySelectorAll('th');
        headers.forEach(header => {
            const filterCell = document.createElement('td');
            const column = header.dataset.key || header.textContent.trim().toLowerCase().replace(/\s+/g, '_');
            
            if (header.dataset.filterable !== 'false') {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'table-filter-input';
                input.placeholder = 'Filter...';
                input.dataset.column = column;
                input.addEventListener('input', (e) => {
                    this.filter(column, e.target.value);
                });
                filterCell.appendChild(input);
            }
            
            filterRow.appendChild(filterCell);
        });
        
        thead.appendChild(filterRow);
    }
    
    filter(column, value) {
        this.currentFilters[column] = value.toLowerCase();
        this.applyFilters();
    }
    
    applyFilters() {
        const filtered = this.data.filter(row => {
            return Object.keys(this.currentFilters).every(column => {
                const filterValue = this.currentFilters[column];
                if (!filterValue) return true;
                const cellValue = (row[column] || '').toLowerCase();
                return cellValue.includes(filterValue);
            });
        });
        
        this.render(filtered);
    }
    
    render(data = null) {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;
        
        const rowsToRender = data || this.data;
        
        // Clear existing rows
        tbody.innerHTML = '';
        
        // Render rows
        rowsToRender.forEach(rowData => {
            const row = rowData._element.cloneNode(true);
            tbody.appendChild(row);
        });
        
        // Update row count
        this.updateRowCount(rowsToRender.length);
    }
    
    updateRowCount(count) {
        let countElement = document.getElementById('table-row-count');
        if (!countElement) {
            countElement = document.createElement('div');
            countElement.id = 'table-row-count';
            countElement.className = 'table-row-count';
            this.table.parentNode.insertBefore(countElement, this.table);
        }
        countElement.textContent = `Showing ${count} of ${this.data.length} rows`;
    }
    
    addResponsiveWrapper() {
        // Check if already wrapped
        if (this.table.parentElement.classList.contains('table-responsive-wrapper')) {
            return;
        }
        
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive-wrapper';
        
        // Move table into wrapper
        this.table.parentNode.insertBefore(wrapper, this.table);
        wrapper.appendChild(this.table);
        
        // Add mobile card view
        this.createMobileCardView();
    }
    
    createMobileCardView() {
        const wrapper = this.table.parentElement;
        const cardView = document.createElement('div');
        cardView.className = 'table-card-view';
        cardView.id = `${this.table.id}-card-view`;
        wrapper.appendChild(cardView);
        
        // Show/hide based on screen size
        this.updateView();
        window.addEventListener('resize', () => this.updateView());
    }
    
    updateView() {
        const isMobile = window.innerWidth < 768;
        const cardView = document.getElementById(`${this.table.id}-card-view`);
        
        if (isMobile && cardView) {
            this.table.style.display = 'none';
            cardView.style.display = 'block';
            this.renderCards();
        } else {
            this.table.style.display = '';
            if (cardView) cardView.style.display = 'none';
        }
    }
    
    renderCards() {
        const cardView = document.getElementById(`${this.table.id}-card-view`);
        if (!cardView) return;
        
        const headers = Array.from(this.table.querySelectorAll('thead th')).map(th => ({
            key: th.dataset.key || th.textContent.trim().toLowerCase().replace(/\s+/g, '_'),
            label: th.textContent.trim()
        }));
        
        const rowsToRender = this.data.filter(row => {
            return Object.keys(this.currentFilters).every(column => {
                const filterValue = this.currentFilters[column];
                if (!filterValue) return true;
                const cellValue = (row[column] || '').toLowerCase();
                return cellValue.includes(filterValue);
            });
        });
        
        cardView.innerHTML = rowsToRender.map(rowData => {
            const card = document.createElement('div');
            card.className = 'table-card';
            card.innerHTML = headers.map(header => {
                const value = rowData[header.key] || '';
                return `
                    <div class="table-card-row">
                        <div class="table-card-label">${escapeHtml(header.label)}:</div>
                        <div class="table-card-value">${escapeHtml(value)}</div>
                    </div>
                `;
            }).join('');
            return card.outerHTML;
        }).join('');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-initialize tables with data-advanced-table attribute
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('table[data-advanced-table]').forEach(table => {
        new AdvancedTable(table.id, {
            sortable: table.dataset.sortable !== 'false',
            filterable: table.dataset.filterable !== 'false',
            responsive: table.dataset.responsive !== 'false'
        });
    });
});

// Export for global access
window.AdvancedTable = AdvancedTable;


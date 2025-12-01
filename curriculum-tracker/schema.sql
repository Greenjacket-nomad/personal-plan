-- PostgreSQL Schema for Curriculum Tracker
-- Converted from SQLite schema

-- Config table
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Progress table
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY,
    current_phase INTEGER DEFAULT 0,
    current_week INTEGER DEFAULT 1,
    started_at TIMESTAMP,
    last_activity_at TIMESTAMP
);

-- Time logs table
CREATE TABLE IF NOT EXISTS time_logs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    hours REAL NOT NULL,
    notes TEXT,
    phase_index INTEGER,
    week INTEGER,
    day INTEGER,
    resource_id INTEGER
);

-- Completed metrics table
CREATE TABLE IF NOT EXISTS completed_metrics (
    id SERIAL PRIMARY KEY,
    phase_index INTEGER NOT NULL,
    metric_text TEXT NOT NULL,
    completed_date DATE NOT NULL,
    resource_id INTEGER,
    UNIQUE(phase_index, metric_text)
);

-- Resources table
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    phase_index INTEGER,
    week INTEGER,
    day INTEGER,
    title TEXT NOT NULL,
    url TEXT,
    resource_type TEXT DEFAULT 'link',
    notes TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'user',
    topic TEXT,
    status TEXT DEFAULT 'not_started',
    completed_at TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    estimated_minutes INTEGER,
    difficulty TEXT,
    user_modified BOOLEAN DEFAULT FALSE,
    scheduled_date DATE,
    original_date DATE
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#6366f1'
);

-- Resource tags junction table
CREATE TABLE IF NOT EXISTS resource_tags (
    resource_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (resource_id, tag_id),
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Activity log table
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Journal entries table
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    content TEXT,
    mood TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    phase_index INTEGER,
    week INTEGER,
    day INTEGER
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Attachments table
CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    resource_id INTEGER,
    journal_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE
);

-- Blocked days table
CREATE TABLE IF NOT EXISTS blocked_days (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_resources_phase_week_day ON resources(phase_index, week, day);
CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status);
CREATE INDEX IF NOT EXISTS idx_time_logs_date ON time_logs(date);
CREATE INDEX IF NOT EXISTS idx_time_logs_resource_id ON time_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(date);
CREATE INDEX IF NOT EXISTS idx_completed_metrics_phase ON completed_metrics(phase_index);


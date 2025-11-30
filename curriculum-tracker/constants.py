"""
Application constants for Curriculum Tracker.
Centralizes magic numbers and configuration values.
"""

# Curriculum structure
TOTAL_PHASES = 4
TOTAL_WEEKS = 17
DAYS_PER_WEEK = 6
TOTAL_CURRICULUM_HOURS = 408
HOURS_PER_WEEK = 24

# UI defaults
FLASH_DISMISS_SECONDS = 5
RECENT_LOGS_LIMIT = 7
DEFAULT_PAGE_SIZE = 20
ACTIVITY_LOG_LIMIT = 100

# Status values
STATUS_NOT_STARTED = 'not_started'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_COMPLETE = 'complete'
STATUS_SKIPPED = 'skipped'

VALID_STATUSES = [STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_COMPLETE, STATUS_SKIPPED]

# Status cycle (for toggle)
STATUS_CYCLE = {
    STATUS_NOT_STARTED: STATUS_IN_PROGRESS,
    STATUS_IN_PROGRESS: STATUS_COMPLETE,
    STATUS_COMPLETE: STATUS_NOT_STARTED,
    STATUS_SKIPPED: STATUS_NOT_STARTED
}

# Resource types
RESOURCE_TYPES = [
    'Course', 'Docs', 'Article', 'Video', 'Project', 
    'Lab', 'Tutorial', 'Action', 'Note', 'Deliverable', 'Link'
]

# Mood options for journal
MOOD_OPTIONS = {
    'great': '😊',
    'okay': '😐',
    'struggling': '😫',
    'fire': '🔥'
}

# Default time estimates by resource type (minutes, difficulty)
DEFAULT_ESTIMATES = {
    'Article': (20, 'easy'),
    'Docs': (45, 'medium'),
    'Tutorial': (90, 'medium'),
    'Course': (240, 'hard'),
    'Video': (30, 'easy'),
    'Project': (180, 'hard'),
    'Lab': (120, 'medium'),
    'Action': (15, 'easy'),
    'Note': (5, 'easy'),
    'Deliverable': (240, 'hard'),
    'Link': (30, 'easy')
}

# Tag colors
TYPE_COLORS = {
    "course": "#3b82f6",
    "docs": "#22c55e",
    "project": "#f97316",
    "article": "#8b5cf6",
    "video": "#ef4444",
    "note": "#6b7280",
    "lab": "#14b8a6",
    "tutorial": "#84cc16",
    "action": "#f59e0b",
    "deliverable": "#ec4899",
    "link": "#06b6d4"
}


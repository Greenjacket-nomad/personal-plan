# Changelog

All notable changes to the Curriculum Tracker project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [6.0.0] - 2025-01-02

### Added
- **Connection Pooling**: ThreadedConnectionPool implementation for efficient database connections
- **Security Hardening**: CSRF protection, XSS prevention, secure file uploads with MIME validation
- **Accessibility**: Full keyboard navigation support for Kanban board (Space, Arrow keys, Enter)
- **Component Architecture**: Extracted burndown chart and JavaScript logic into separate files
- **Implementation Status Documentation**: Comprehensive status report of all improvements

### Changed
- **Single Source of Truth**: Dashboard now reads from PostgreSQL database instead of YAML
- **Database Driver**: Upgraded from `psycopg2-binary` to `psycopg2` for production stability
- **Dashboard Template**: Reduced from 1,186 lines to 995 lines through component extraction
- **Progress Metrics**: Unified progress calculation (Tasks Completed vs Hours Logged)

### Fixed
- **Performance**: Eliminated N+1 queries in structure service (100+ queries → 1-2 queries)
- **Memory**: Streaming export prevents memory bombs on large datasets
- **Race Conditions**: SERIALIZABLE transaction isolation prevents duplicate order_index values
- **Data Integrity**: Strict FK enforcement, orphaned resources auto-moved to Inbox
- **Global Search**: Dashboard search now searches entire curriculum, not just current week
- **Dead Buttons**: Toggle complete and edit resource now fully functional

### Security
- **CSRF Protection**: Flask-WTF CSRFProtect initialized, all AJAX requests secured
- **XSS Prevention**: Removed unsafe template filters, server-side sanitization
- **Data Leak**: Activity logs filtered by user_id, proper access control
- **File Uploads**: MIME type validation using python-magic prevents malicious uploads
- **Backdoor Removal**: Default admin account disabled via migration

### Removed
- Removed obsolete SQLite database file (`tracker.db`)
- Removed build artifacts (`__pycache__`, `.egg-info` directories)
- Removed obsolete SQLite-related files (already completed in previous versions)

### Updated
- Updated `.gitignore` to prevent tracking build artifacts
- Updated README with comprehensive documentation of all improvements
- Updated requirements.txt with production-ready database driver
- Updated documentation to reflect connection pooling and security features

## [5.0.0] - 2025-01-01

### Added
- Modular architecture with separated concerns
- `database.py`: Centralized database connection and schema management
- `utils.py`: Helper functions and path constants
- `services/` directory: Business logic layer
  - `services/resources.py`: Resource-related database queries
  - `services/progress.py`: Progress tracking and metrics
  - `services/reporting.py`: Analytics and reporting queries
- `routes/` directory: Route handlers organized by functionality
  - `routes/main.py`: HTML rendering routes (dashboard, journal, resources, reports)
  - `routes/api.py`: JSON API endpoints and form handlers
- Flask Blueprint pattern for route organization
- Application factory pattern in `app.py`

### Changed
- Refactored monolithic `app.py` (2,754 lines) into modular structure
- Separated database logic from route handlers
- Separated business logic from presentation layer
- Improved code organization and maintainability
- Enhanced error handling for `.env` file access

### Improved
- Code maintainability: Each module has a single, well-defined responsibility
- Testability: Services can be tested independently from routes
- Scalability: Easy to add new features without modifying multiple sections
- Code readability: Clear separation of concerns

### Technical Details
- Zero functionality lost - all existing features preserved
- All imports verified and working
- Blueprints properly registered
- Teardown handlers correctly configured
- No breaking changes to API or user interface

## [4.1] - Previous Release

### Added
- File attachment support (PDFs, images, videos, documents)
- Status dropdown menus (4-state system)
- Enhanced reporting with theme support
- Improved error handling
- PostgreSQL datetime compatibility fixes

## [4.0] - UX Overhaul

### Fixed
- Continue button scroll and highlight functionality
- Search bar on Resources page
- Reports page dark mode for Chart.js
- Success Metrics dropdown to show actual linked resources
- Continue link navigation to course

### Added
- Global navigation consistency
- Dashboard restructure with merged calendar
- Toast notifications (replaced flash messages)
- Mobile-responsive menu
- Enhanced burndown chart with dates and completion line

### Improved
- Batch resource hours queries (N+1 fix)
- Performance optimizations
- Upload size limits (16MB)
- STATUS_CYCLE constant usage

## [3.0] - PostgreSQL Migration

### Changed
- Migrated from SQLite to PostgreSQL
- Implemented proper connection pooling
- Added RealDictCursor for dictionary-based access
- Updated all queries to use `%s` placeholders
- Changed `AUTOINCREMENT` to `SERIAL PRIMARY KEY`
- Converted `DATETIME` to `TIMESTAMP`
- Implemented `RETURNING id` for INSERT statements

### Benefits
- Multi-user ready
- Better performance at scale
- Visual database management tools
- Production deployment ready
- Foreign key constraints enforced

## [2.0] - Feature Expansion

### Added
- Journal entries
- Tag system implementation
- Resource filtering and search
- Activity logging
- Progress tracking improvements

## [1.0] - Initial Release

### Added
- Basic Flask application with SQLite
- Simple dashboard with resource listing
- Time logging functionality
- CSV import for curriculum data

---

[5.0.0]: https://github.com/yourusername/curriculum-tracker/compare/v4.1...v5.0.0
[4.1]: https://github.com/yourusername/curriculum-tracker/compare/v4.0...v4.1
[4.0]: https://github.com/yourusername/curriculum-tracker/compare/v3.0...v4.0
[3.0]: https://github.com/yourusername/curriculum-tracker/compare/v2.0...v3.0
[2.0]: https://github.com/yourusername/curriculum-tracker/compare/v1.0...v2.0
[1.0]: https://github.com/yourusername/curriculum-tracker/releases/tag/v1.0


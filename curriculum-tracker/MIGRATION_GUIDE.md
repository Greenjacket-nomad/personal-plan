# Migration Guide: v4.1 → v5.0

> **⚠️ NOTE: This guide is outdated.** This document describes the migration from monolithic to modular architecture (v5.0). The application has since evolved to support dynamic curriculum structures with database-driven phases, weeks, and days (replacing the static YAML configuration). For current migration information, see `CHANGELOG.md` and the Alembic migration files in `migrations/versions/`.

This guide helps developers understand the architectural changes in version 5.0.

## Overview

The application has been refactored from a monolithic `app.py` file (2,754 lines) into a modular structure with clear separation of concerns. **No functionality has been lost** - all features work exactly as before.

## What Changed

### File Structure

**Before (v4.1):**
```
curriculum-tracker/
├── app.py (2,754 lines - everything in one file)
├── constants.py
└── ...
```

**After (v5.0):**
```
curriculum-tracker/
├── app.py (clean entry point)
├── database.py (database logic)
├── utils.py (helper functions)
├── services/
│   ├── resources.py
│   ├── progress.py
│   └── reporting.py
├── routes/
│   ├── main.py
│   └── api.py
└── ...
```

## Import Changes

### For New Code

**Database Operations:**
```python
from database import get_db, get_db_cursor, init_db, run_migrations
```

**Utilities:**
```python
from utils import load_curriculum, get_week_dates, allowed_file, UPLOAD_FOLDER
```

**Services:**
```python
from services.resources import get_resources, get_all_resources
from services.progress import get_progress, update_progress, log_activity
from services.reporting import get_burndown_data, get_time_reports
```

**Routes (if creating new routes):**
```python
from routes.main import main_bp
from routes.api import api_bp
```

## Route URL Changes

**No URL changes!** All routes work exactly as before:
- `/` → Dashboard
- `/resources` → Resources page
- `/api/resource/<id>` → API endpoints
- etc.

The only internal change is that routes are now organized in Blueprints, but the URLs remain the same.

## Database Changes

**No database schema changes!** The database structure is identical. All existing data will work without migration.

## Configuration Changes

**No configuration changes!** The `.env` file format and all environment variables remain the same.

## Running the Application

**No changes to startup!** The application still runs the same way:

```bash
python3 app.py
```

The database will still auto-initialize on first run, and migrations will run automatically.

## For Developers

### Adding New Features

**Adding a new route:**
1. Determine if it's an HTML route or API route
2. Add to `routes/main.py` (HTML) or `routes/api.py` (API)
3. Use the existing Blueprint: `@main_bp.route(...)` or `@api_bp.route(...)`

**Adding a new database query:**
1. Determine which service it belongs to (resources, progress, or reporting)
2. Add the function to the appropriate service file
3. Import and use in your route handler

**Adding a new utility function:**
1. Add to `utils.py`
2. Import where needed: `from utils import your_function`

### Testing

The modular structure makes testing easier:

```python
# Test a service function independently
from services.progress import get_progress

# Test without Flask context
# (Note: database functions handle Flask context automatically)
```

## Breaking Changes

**None!** This is a pure refactoring with zero breaking changes:
- ✅ All URLs work the same
- ✅ All API endpoints work the same
- ✅ All database queries work the same
- ✅ All features work the same
- ✅ No data migration needed

## Benefits

1. **Maintainability**: Each file has a clear, single responsibility
2. **Testability**: Services can be tested independently
3. **Scalability**: Easy to add features without touching existing code
4. **Readability**: Clear organization makes code easier to understand
5. **Collaboration**: Multiple developers can work on different modules simultaneously

## Questions?

If you encounter any issues or have questions about the new structure, please refer to:
- `README.md` - Full architecture documentation
- `CHANGELOG.md` - Detailed change log
- Code comments in each module

---

**Version**: 5.0.0  
**Date**: January 2025  
**Type**: Refactoring (no breaking changes)


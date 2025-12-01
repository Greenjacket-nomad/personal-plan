#!/usr/bin/env python3
"""
Curriculum Tracker - Web Dashboard with PostgreSQL
Entry point for the Flask application.
"""

import os
from pathlib import Path
from flask import Flask

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, PermissionError, OSError):
    pass  # python-dotenv not installed or .env not accessible, use environment variables directly

# Import from new modular structure
from database import close_db, init_db, run_migrations
from routes.main import main_bp
from routes.api import api_bp

APP_DIR = Path(__file__).parent


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
    
    # Register teardown handler
    app.teardown_appcontext(close_db)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    print("\nCurriculum Tracker")
    print("=" * 40)
    print("Initializing database...")
    init_db()
    print("✓ Database ready!")
    print("Running migrations...")
    try:
        run_migrations()
    except Exception as e:
        print(f"Note: Some migrations may have already been applied: {e}")
    print("✓ Migrations complete!")
    print("\nOpen: http://localhost:5000")
    print("Ctrl+C to stop\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

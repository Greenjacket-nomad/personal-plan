#!/usr/bin/env python3
"""
Pytest configuration and fixtures for Curriculum Tracker tests.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_db():
    """
    Test database fixture.
    
    CRITICAL: Do NOT use SQLite - app uses PostgreSQL-specific syntax.
    This fixture checks for TEST_DATABASE_URL environment variable.
    If missing, the test will be skipped.
    """
    test_db_url = os.getenv('TEST_DATABASE_URL')
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL environment variable not set. Skipping database tests.")
    
    # If TEST_DATABASE_URL is set, assume it's a valid PostgreSQL connection string
    # Tests can use this to connect to a test database
    return test_db_url


@pytest.fixture
def mock_get_progress():
    """Mock get_progress service function."""
    with patch('services.progress.get_progress') as mock:
        mock.return_value = {
            'current_phase': 0,
            'current_week': 1,
            'started_at': '2024-01-01',
            'last_activity_at': None
        }
        yield mock


@pytest.fixture
def mock_get_resources():
    """Mock get_resources service function."""
    with patch('services.resources.get_resources') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_current_user():
    """Mock current_user for Flask-Login."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = 'testuser'
    mock_user.is_authenticated = True
    
    with patch('flask_login.current_user', mock_user):
        yield mock_user


@pytest.fixture
def authenticated_client(client, mock_current_user):
    """Create authenticated test client."""
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
    return client


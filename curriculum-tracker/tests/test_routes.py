#!/usr/bin/env python3
"""
Unit tests for routes/main.py
Tests route handlers using mocked service layer.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestDashboardRoute:
    """Test dashboard route."""
    
    def test_dashboard_loads_authenticated(self, client, mock_current_user, mock_get_progress, mock_get_resources):
        """Test dashboard loads with 200 OK when authenticated."""
        with patch('routes.main.get_progress') as mock_progress, \
             patch('routes.main.get_resources') as mock_resources, \
             patch('routes.main.load_curriculum') as mock_curriculum:
            
            mock_progress.return_value = {
                'current_phase': 0,
                'current_week': 1,
                'started_at': '2024-01-01',
                'last_activity_at': None
            }
            mock_resources.return_value = []
            mock_curriculum.return_value = {'phases': []}
            
            # Mock login
            with client.session_transaction() as sess:
                sess['_user_id'] = '1'
            
            response = client.get('/')
            assert response.status_code == 200
    
    def test_dashboard_redirects_when_not_authenticated(self, client):
        """Test dashboard redirects to login when not authenticated."""
        response = client.get('/')
        assert response.status_code == 302  # Redirect to login
        assert '/login' in response.location


class TestLoginRoute:
    """Test login route."""
    
    def test_login_page_loads(self, client):
        """Test login page loads."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data
    
    def test_login_success(self, client):
        """Test successful login redirects to dashboard."""
        from services.auth import authenticate_user
        
        with patch('routes.main.authenticate_user') as mock_auth:
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.username = 'testuser'
            mock_auth.return_value = mock_user
            
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'password'
            }, follow_redirects=False)
            
            assert response.status_code == 302  # Redirect
            assert '/' in response.location or '/dashboard' in response.location
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials shows error."""
        with patch('routes.main.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            
            assert response.status_code == 200
            assert b'Invalid' in response.data or b'error' in response.data.lower()


class TestLogoutRoute:
    """Test logout route."""
    
    def test_logout_clears_session(self, client, mock_current_user):
        """Test logout clears session."""
        with patch('flask_login.logout_user') as mock_logout:
            with client.session_transaction() as sess:
                sess['_user_id'] = '1'
            
            response = client.get('/logout', follow_redirects=False)
            assert response.status_code == 302  # Redirect to login
            mock_logout.assert_called_once()


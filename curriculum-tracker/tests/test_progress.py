#!/usr/bin/env python3
"""
Unit tests for services/progress.py
Tests streak calculation logic and other progress functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestStreakCalculation:
    """Test streak calculation logic."""
    
    def test_get_current_streak_no_logs(self):
        """Test current streak with no time logs."""
        from services.progress import get_current_streak
        
        with patch('services.progress.get_db') as mock_db, \
             patch('services.progress.get_db_cursor') as mock_cursor, \
             patch('flask_login.current_user') as mock_user:
            
            mock_user.id = 1
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_db.return_value = mock_conn
            mock_cursor.return_value = mock_cur
            mock_cur.fetchall.return_value = []
            
            streak = get_current_streak()
            assert streak == 0
    
    def test_get_current_streak_consecutive_days(self):
        """Test current streak with consecutive days."""
        from services.progress import get_current_streak
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        
        with patch('services.progress.get_db') as mock_db, \
             patch('services.progress.get_db_cursor') as mock_cursor, \
             patch('flask_login.current_user') as mock_user:
            
            mock_user.id = 1
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_db.return_value = mock_conn
            mock_cursor.return_value = mock_cur
            mock_cur.fetchall.return_value = [
                {'date': today.strftime('%Y-%m-%d')},
                {'date': yesterday.strftime('%Y-%m-%d')},
                {'date': two_days_ago.strftime('%Y-%m-%d')}
            ]
            
            streak = get_current_streak()
            assert streak == 3
    
    def test_get_longest_streak(self):
        """Test longest streak calculation."""
        from services.progress import get_longest_streak
        
        with patch('services.progress.get_db') as mock_db, \
             patch('services.progress.get_db_cursor') as mock_cursor, \
             patch('flask_login.current_user') as mock_user:
            
            mock_user.id = 1
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_db.return_value = mock_conn
            mock_cursor.return_value = mock_cur
            
            # Create dates with a gap
            dates = [
                datetime(2024, 1, 1).date(),
                datetime(2024, 1, 2).date(),
                datetime(2024, 1, 3).date(),
                datetime(2024, 1, 5).date(),  # Gap here
                datetime(2024, 1, 6).date(),
            ]
            
            mock_cur.fetchall.return_value = [
                {'date': d.strftime('%Y-%m-%d')} for d in dates
            ]
            
            longest = get_longest_streak()
            assert longest == 3  # First 3 consecutive days


#!/usr/bin/env python3
"""
Unit tests for utils.py
Tests date scheduling logic and other utility functions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestDateScheduling:
    """Test date scheduling logic."""
    
    def test_calculate_schedule_basic(self):
        """Test basic schedule calculation."""
        from utils import calculate_schedule
        
        start_date = datetime(2024, 1, 1).date()
        schedule = calculate_schedule(start_date)
        
        assert schedule is not None
        assert isinstance(schedule, dict)
    
    def test_get_start_date(self):
        """Test getting start date from config."""
        from utils import get_start_date
        
        with patch('utils.get_db') as mock_db, \
             patch('utils.get_db_cursor') as mock_cursor:
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_db.return_value = mock_conn
            mock_cursor.return_value = mock_cur
            mock_cur.fetchone.return_value = {'value': '2024-01-01'}
            
            start_date = get_start_date()
            assert start_date == '2024-01-01'
    
    def test_recalculate_schedule_from(self):
        """Test recalculating schedule from a specific date."""
        from utils import recalculate_schedule_from
        
        from_date = datetime(2024, 1, 15).date()
        
        with patch('utils.get_db') as mock_db, \
             patch('utils.get_db_cursor') as mock_cursor, \
             patch('utils.calculate_schedule') as mock_calc:
            
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_db.return_value = mock_conn
            mock_cursor.return_value = mock_cur
            mock_calc.return_value = {}
            
            recalculate_schedule_from(from_date)
            mock_calc.assert_called_once()


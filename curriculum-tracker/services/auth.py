#!/usr/bin/env python3
"""
Authentication service for Curriculum Tracker.
Handles user authentication, password hashing, and user management.
"""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db, get_db_cursor


class User(UserMixin):
    """User class for Flask-Login."""
    
    def __init__(self, user_id, username, password_hash):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
    
    def check_password(self, password):
        """Check if provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_user(user_id):
        """Get user by ID."""
        conn = get_db()
        cur = get_db_cursor(conn)
        cur.execute("SELECT id, username, password_hash FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        
        if row:
            return User(row['id'], row['username'], row['password_hash'])
        return None
    
    @staticmethod
    def get_user_by_username(username):
        """Get user by username."""
        conn = get_db()
        cur = get_db_cursor(conn)
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        
        if row:
            return User(row['id'], row['username'], row['password_hash'])
        return None


def authenticate_user(username, password):
    """Authenticate a user with username and password."""
    user = User.get_user_by_username(username)
    if user and user.check_password(password):
        return user
    return None


def create_user(username, password):
    """Create a new user."""
    conn = get_db()
    cur = get_db_cursor(conn)
    password_hash = generate_password_hash(password)
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (username, password_hash)
        )
        user_id = cur.fetchone()['id']
        cur.close()
        conn.commit()
        return User(user_id, username, password_hash)
    except Exception as e:
        cur.close()
        conn.rollback()
        raise e


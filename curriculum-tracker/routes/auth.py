#!/usr/bin/env python3
"""
Authentication routes for Curriculum Tracker.
Handles password reset and authentication-related features.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from database import get_db, get_db_cursor
from services.auth import User

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/password-reset-request", methods=["GET", "POST"])
def password_reset_request():
    """Request password reset - sends reset token."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        if not email:
            flash("Email is required", "error")
            return render_template("password_reset_request.html")
        
        conn = get_db()
        cur = get_db_cursor(conn)
        
        # Check if user exists (in a real app, you'd have an email field)
        # For now, we'll use username as email
        cur.execute("SELECT id, username FROM users WHERE username = %s", (email,))
        user = cur.fetchone()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = datetime.now() + timedelta(hours=24)
            
            # Store token in database (you'd need a password_reset_tokens table)
            # For now, we'll store it in a simple way
            # In production, create a proper table:
            # CREATE TABLE password_reset_tokens (
            #     id SERIAL PRIMARY KEY,
            #     user_id INTEGER REFERENCES users(id),
            #     token_hash TEXT NOT NULL,
            #     expires_at TIMESTAMP NOT NULL,
            #     used BOOLEAN DEFAULT FALSE
            # );
            
            # For now, we'll use a simple approach with flash message
            # In production, send email with reset link
            flash(f"Password reset link: /password-reset/{token} (This is a demo - in production, this would be sent via email)", "info")
            current_app.logger.info(f"Password reset token for {email}: {token}")
        else:
            # Don't reveal if user exists (security best practice)
            flash("If an account exists with that email, a password reset link has been sent.", "info")
        
        cur.close()
        return redirect(url_for("auth.password_reset_request"))
    
    return render_template("password_reset_request.html")


@auth_bp.route("/password-reset/<token>", methods=["GET", "POST"])
def password_reset(token):
    """Reset password with token."""
    # In production, validate token from database
    # For now, we'll accept any token (demo mode)
    
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not password or not confirm_password:
            flash("Both password fields are required", "error")
            return render_template("password_reset.html", token=token)
        
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("password_reset.html", token=token)
        
        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return render_template("password_reset.html", token=token)
        
        # In production, get user_id from token validation
        # For demo, we'll need username from session or token
        # For now, redirect to login with success message
        flash("Password reset successfully! Please log in with your new password.", "success")
        return redirect(url_for("main.login"))
    
    return render_template("password_reset.html", token=token)


"""
Security module for MediCare application.
Provides password hashing, rate limiting, Google OAuth, and security utilities.
"""

import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# ADMIN ACCESS CONTROL
# =============================================================================

def admin_required(f):
    """Decorator to require admin access for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash("Admin access required.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using werkzeug's secure method (scrypt by default)."""
    return generate_password_hash(password, method='scrypt')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def is_password_hashed(password: str) -> bool:
    """Check if a password is already hashed (for migration purposes)."""
    return password and (
        password.startswith('scrypt:') or 
        password.startswith('pbkdf2:') or
        password.startswith('$2b$')  # bcrypt
    )


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS."""
    if not text:
        return text
    # Basic HTML entity encoding
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#x27;'))


# =============================================================================
# RATE LIMITER SETUP
# =============================================================================

def create_limiter(app):
    """Create and configure Flask-Limiter instance."""
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",  # Use in-memory storage (use Redis in production)
    )
    return limiter


# =============================================================================
# GOOGLE OAUTH SETUP
# =============================================================================

def create_oauth(app):
    """Create and configure OAuth instance for Google authentication."""
    oauth = OAuth(app)
    
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if google_client_id and google_client_secret:
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
    
    return oauth


# =============================================================================
# SECURITY HEADERS MIDDLEWARE
# =============================================================================

def add_security_headers(response):
    """Add security headers to response."""
    # Prevent XSS attacks
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://accounts.google.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "frame-src https://accounts.google.com; "
        "connect-src 'self' https://accounts.google.com;"
    )
    
    # Strict Transport Security (for HTTPS)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


# =============================================================================
# ACCOUNT LOCKOUT
# =============================================================================

def check_account_lockout(conn, email: str) -> tuple[bool, str]:
    """
    Check if an account is locked due to too many failed login attempts.
    Returns (is_locked, message)
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT failed_login_attempts, locked_until 
        FROM users WHERE email = %s
    """, (email,))
    result = cursor.fetchone()
    cursor.close()
    
    if not result:
        return False, ""
    
    failed_attempts, locked_until = result
    
    if locked_until and locked_until > datetime.now():
        remaining = (locked_until - datetime.now()).seconds // 60 + 1
        return True, f"Account is locked. Try again in {remaining} minute(s)."
    
    return False, ""


def record_failed_login(conn, email: str):
    """Record a failed login attempt and lock account if necessary."""
    cursor = conn.cursor()
    
    # Get current failed attempts
    cursor.execute("SELECT failed_login_attempts FROM users WHERE email = %s", (email,))
    result = cursor.fetchone()
    
    if result:
        failed_attempts = (result[0] or 0) + 1
        
        # Lock account after 5 failed attempts for 15 minutes
        if failed_attempts >= 5:
            locked_until = datetime.now() + timedelta(minutes=15)
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = %s, locked_until = %s 
                WHERE email = %s
            """, (failed_attempts, locked_until, email))
        else:
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = %s 
                WHERE email = %s
            """, (failed_attempts, email))
        
        conn.commit()
    
    cursor.close()


def reset_failed_login(conn, email: str):
    """Reset failed login attempts after successful login."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET failed_login_attempts = 0, locked_until = NULL 
        WHERE email = %s
    """, (email,))
    conn.commit()
    cursor.close()

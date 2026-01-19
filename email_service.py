"""
Email Service Module for MediCare Application
Uses Resend API for sending emails (works on Render free tier).
"""

import os
import random
import string
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Try to import resend, fall back gracefully
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


# =============================================================================
# ASYNC EMAIL SENDING WRAPPER
# =============================================================================

def send_email_async(email_func, *args, **kwargs):
    """
    Wrapper to send emails in a background thread.
    Prevents blocking the main request.
    """
    thread = threading.Thread(target=email_func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return True


# =============================================================================
# OTP GENERATION
# =============================================================================

def generate_otp(length=6):
    """Generate a random numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


def create_otp_record(conn, email: str, otp: str, expires_minutes: int = 10):
    """
    Store OTP in database for verification.
    Returns True if successful, False otherwise.
    """
    cursor = conn.cursor()
    expires_at = datetime.now() + timedelta(minutes=expires_minutes)
    
    try:
        # Delete any existing OTP for this email
        cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
        
        # Insert new OTP
        cursor.execute("""
            INSERT INTO email_verifications (email, otp, expires_at, created_at)
            VALUES (%s, %s, %s, %s)
        """, (email, otp, expires_at, datetime.now()))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error creating OTP record: {e}")
        conn.rollback()
        cursor.close()
        return False


def verify_otp(conn, email: str, otp: str) -> tuple[bool, str]:
    """
    Verify OTP for an email.
    Returns (is_valid, message)
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT otp, expires_at FROM email_verifications 
            WHERE email = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (email,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            return False, "No OTP found. Please request a new one."
        
        stored_otp, expires_at = result
        
        if datetime.now() > expires_at:
            return False, "OTP has expired. Please request a new one."
        
        if stored_otp != otp:
            return False, "Invalid OTP. Please try again."
        
        return True, "OTP verified successfully!"
        
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        cursor.close()
        return False, "Error verifying OTP. Please try again."


def mark_email_verified(conn, email: str) -> bool:
    """Mark user's email as verified."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE users SET email_verified = TRUE WHERE email = %s
        """, (email,))
        
        # Clean up OTP records
        cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error marking email verified: {e}")
        conn.rollback()
        cursor.close()
        return False


# =============================================================================
# EMAIL SENDING (Resend API - Works on Render Free Tier!)
# =============================================================================

def get_resend_config():
    """Get Resend API configuration."""
    api_key = os.getenv('RESEND_API_KEY')
    # Use verified domain email or fall back to resend.dev for testing
    from_email = os.getenv('RESEND_FROM_EMAIL', 'MediCare <noreply@doclynk.nithilan.tech>')
    return api_key, from_email


def send_otp_email(to_email: str, otp: str, name: str = "User") -> tuple[bool, str]:
    """
    Send OTP email using Resend API (HTTP-based, works on Render free tier).
    Returns (success, message)
    """
    if not RESEND_AVAILABLE:
        print("Resend module not available")
        return False, "Email service not installed"
    
    api_key, from_email = get_resend_config()
    
    if not api_key:
        print("Resend API key not configured")
        return False, "Email service not configured"
    
    # Configure Resend
    resend.api_key = api_key
    
    # Create email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #0ea5e9, #10b981); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; }}
            .content {{ padding: 40px 30px; text-align: center; }}
            .otp-box {{ background: linear-gradient(135deg, #f0f9ff, #ecfdf5); border: 2px dashed #0ea5e9; border-radius: 12px; padding: 25px; margin: 25px 0; }}
            .otp-code {{ font-size: 42px; font-weight: bold; color: #0369a1; letter-spacing: 8px; font-family: monospace; }}
            .timer {{ color: #6b7280; font-size: 14px; margin-top: 15px; }}
            .footer {{ background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
            .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0; text-align: left; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 MediCare</h1>
            </div>
            <div class="content">
                <h2 style="color: #1f2937; margin-bottom: 10px;">Hello, {name}!</h2>
                <p style="color: #4b5563;">Please use the following OTP to verify your email address:</p>
                
                <div class="otp-box">
                    <div class="otp-code">{otp}</div>
                    <div class="timer">⏱️ Valid for 10 minutes</div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Security Note:</strong> Never share this code with anyone. MediCare staff will never ask for your OTP.
                </div>
            </div>
            <div class="footer">
                <p>This email was sent by MediCare Healthcare System</p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": "🔐 MediCare - Verify Your Email",
            "html": html_content,
        }
        
        email_response = resend.Emails.send(params)
        print(f"Resend response: {email_response}")
        
        if email_response and email_response.get('id'):
            return True, "OTP sent successfully!"
        else:
            return False, "Failed to send email"
            
    except Exception as e:
        print(f"Resend Error: {e}")
        return False, f"Email service error: {str(e)}"


def send_welcome_email(to_email: str, name: str) -> bool:
    """Send welcome email after successful registration."""
    if not RESEND_AVAILABLE:
        return False
    
    api_key, from_email = get_resend_config()
    
    if not api_key:
        return False
    
    resend.api_key = api_key
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #10b981, #0ea5e9); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; }}
            .content {{ padding: 30px; text-align: center; }}
            .btn {{ display: inline-block; background: #0ea5e9; color: white; padding: 12px 30px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏥 Welcome to MediCare!</h1>
            </div>
            <div class="content">
                <h2>Hello, {name}! 👋</h2>
                <p>Your email has been verified and your account is now active.</p>
                <p>You can now book appointments, manage your healthcare, and more!</p>
                <a href="https://doclynk.nithilan.tech/login" class="btn">Login to MediCare</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": "🎉 Welcome to MediCare!",
            "html": html_content,
        }
        
        resend.Emails.send(params)
        return True
    except:
        return False


def send_password_reset_email(to_email: str, otp: str, name: str = "User") -> tuple[bool, str]:
    """
    Send password reset OTP email.
    Returns (success, message)
    """
    if not RESEND_AVAILABLE:
        return False, "Email service not installed"
    
    api_key, from_email = get_resend_config()
    
    if not api_key:
        return False, "Email service not configured"
    
    resend.api_key = api_key
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #f59e0b, #ef4444); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; }}
            .content {{ padding: 40px 30px; text-align: center; }}
            .otp-box {{ background: linear-gradient(135deg, #fef3c7, #fecaca); border: 2px dashed #f59e0b; border-radius: 12px; padding: 25px; margin: 25px 0; }}
            .otp-code {{ font-size: 42px; font-weight: bold; color: #b45309; letter-spacing: 8px; font-family: monospace; }}
            .timer {{ color: #6b7280; font-size: 14px; margin-top: 15px; }}
            .footer {{ background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
            .warning {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; margin: 20px 0; text-align: left; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Password Reset</h1>
            </div>
            <div class="content">
                <h2 style="color: #1f2937; margin-bottom: 10px;">Hello, {name}!</h2>
                <p style="color: #4b5563;">You requested to reset your password. Use this code:</p>
                
                <div class="otp-box">
                    <div class="otp-code">{otp}</div>
                    <div class="timer">⏱️ Valid for 10 minutes</div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Didn't request this?</strong> If you didn't request a password reset, please ignore this email. Your password won't be changed.
                </div>
            </div>
            <div class="footer">
                <p>This email was sent by MediCare Healthcare System</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": "🔐 MediCare - Password Reset Code",
            "html": html_content,
        }
        
        email_response = resend.Emails.send(params)
        if email_response and email_response.get('id'):
            return True, "Reset code sent successfully!"
        return False, "Failed to send email"
    except Exception as e:
        print(f"Password reset email error: {e}")
        return False, f"Email error: {str(e)}"

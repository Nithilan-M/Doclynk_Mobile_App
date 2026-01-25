from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from datetime import datetime, time
from db_config import get_db_connection
from dotenv import load_dotenv
import os

from security import (
    hash_password, verify_password, is_password_hashed,
    validate_email, validate_password_strength, sanitize_input,
    create_limiter, create_oauth, add_security_headers,
    check_account_lockout, record_failed_login, reset_failed_login,
    admin_required
)

# Import email service for OTP
try:
    from email_service import (
        generate_otp, create_otp_record, verify_otp as verify_otp_code,
        mark_email_verified, send_otp_email, send_welcome_email, send_email_async,
        send_password_reset_email
    )
    EMAIL_SERVICE_AVAILABLE = True
except ImportError:
    EMAIL_SERVICE_AVAILABLE = False


# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")  # secret key is now from .env

# Configure session for security
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize Rate Limiter
limiter = create_limiter(app)

# Initialize Google OAuth
oauth = create_oauth(app)


# Helper function to get client IP (handles proxied requests like Render)
def get_client_ip():
    """Get the real client IP address, handling proxied requests."""
    # Check for forwarded IP (when behind a proxy like Render, Cloudflare, etc.)
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs; the first one is the client
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


# Security headers middleware
@app.after_request
def apply_security_headers(response):
    return add_security_headers(response)


# Generate time slots from 9:00 AM to 5:00 PM with 30-minute intervals
def generate_time_slots():
    slots = []
    start_hour = 9
    end_hour = 17  # 5 PM in 24-hour format
    
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            time_obj = time(hour, minute)
            formatted_time = time_obj.strftime("%I:%M %p")
            slots.append(formatted_time)
    
    return slots


# Health Check (for cron jobs to keep Render awake)
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "MediCare is running"}), 200


# Home
@app.route('/')
def home():
    return redirect(url_for('login'))


# Register
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        role = request.form['role']
        name = sanitize_input(request.form['name'])
        email = request.form['email'].lower().strip()
        password = request.form['password']

        # Validate email
        if not validate_email(email):
            flash("Please enter a valid email address", "error")
            return render_template('register.html')

        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, "error")
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("An account with this email already exists", "error")
            cursor.close()
            conn.close()
            return render_template('register.html')
        
        cursor.close()
        
        # Email OTP verification using Resend API (works on Render free tier!)
        resend_api_key = os.getenv('RESEND_API_KEY')
        if EMAIL_SERVICE_AVAILABLE and resend_api_key:
            # Store registration data in session temporarily
            session['pending_registration'] = {
                'name': name,
                'email': email,
                'password': hash_password(password),
                'role': role
            }
            
            # Generate OTP and store in database
            otp = generate_otp()
            if create_otp_record(conn, email, otp):
                conn.close()
                
                # Send email in background thread (non-blocking)
                def send_email_background():
                    try:
                        success, msg = send_otp_email(email, otp, name)
                        print(f"OTP email result: {success} - {msg}")
                    except Exception as e:
                        print(f"Background email error: {e}")
                
                send_email_async(send_email_background)
                
                flash("A verification code has been sent to your email. Please check your inbox.", "success")
                return redirect(url_for('verify_email_page', email=email))
            else:
                flash("Failed to generate verification code. Please try again.", "error")
            
            conn.close()
            return render_template('register.html')
        
        # If email service not available, register directly
        hashed_password = hash_password(password)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role, auth_provider, email_verified) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, email, hashed_password, role, 'email', True),
            )
        except Exception:
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, password, role, auth_provider) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, hashed_password, role, 'email'),
                )
            except Exception:
                cursor.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    (name, email, hashed_password, role),
                )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# OTP Verification Page
@app.route('/verify-email')
def verify_email_page():
    email = request.args.get('email', '')
    if not email:
        return redirect(url_for('register'))
    return render_template('verify_otp.html', email=email)


# Verify OTP
@app.route('/verify-otp', methods=['POST'])
@limiter.limit("10 per minute")
def verify_otp():
    email = request.form.get('email', '').lower().strip()
    otp = request.form.get('otp', '')
    
    if not email or not otp:
        flash("Please enter the verification code.", "error")
        return redirect(url_for('verify_email_page', email=email))
    
    conn = get_db_connection()
    
    # Verify OTP
    is_valid, message = verify_otp_code(conn, email, otp)
    
    if not is_valid:
        conn.close()
        flash(message, "error")
        return redirect(url_for('verify_email_page', email=email))
    
    # Get pending registration data
    pending = session.get('pending_registration')
    
    if not pending or pending.get('email') != email:
        conn.close()
        flash("Registration session expired. Please register again.", "error")
        return redirect(url_for('register'))
    
    # Create the user account
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role, auth_provider, email_verified) VALUES (%s, %s, %s, %s, %s, %s)",
            (pending['name'], pending['email'], pending['password'], pending['role'], 'email', True),
        )
    except Exception:
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role, auth_provider) VALUES (%s, %s, %s, %s, %s)",
                (pending['name'], pending['email'], pending['password'], pending['role'], 'email'),
            )
        except Exception:
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (pending['name'], pending['email'], pending['password'], pending['role']),
            )
    
    conn.commit()
    
    # Clean up
    cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Clear pending registration
    session.pop('pending_registration', None)
    
    # Send welcome email (non-blocking)
    try:
        send_welcome_email(email, pending['name'])
    except:
        pass
    
    flash("Email verified successfully! Your account is now active. Please log in.", "success")
    return redirect(url_for('login'))


# Resend OTP
@app.route('/resend-otp', methods=['POST'])
@limiter.limit("3 per minute")
def resend_otp():
    email = request.form.get('email', '').lower().strip()
    
    if not email:
        return redirect(url_for('register'))
    
    pending = session.get('pending_registration')
    
    if not pending or pending.get('email') != email:
        flash("Session expired. Please register again.", "error")
        return redirect(url_for('register'))
    
    conn = get_db_connection()
    
    # Generate new OTP
    otp = generate_otp()
    if create_otp_record(conn, email, otp):
        success, message = send_otp_email(email, otp, pending['name'])
        if success:
            flash("A new verification code has been sent.", "success")
        else:
            flash(f"Failed to send email: {message}", "error")
    else:
        flash("Failed to generate new code. Please try again.", "error")
    
    conn.close()
    return redirect(url_for('verify_email_page', email=email))


# ============================================================================
# FORGOT PASSWORD ROUTES
# ============================================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """Handle forgot password request."""
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        
        if not email:
            flash("Please enter your email address.", "error")
            return render_template('forgot_password.html')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            # Don't reveal if email exists or not (security)
            flash("If an account with that email exists, we've sent a reset code.", "success")
            conn.close()
            return redirect(url_for('reset_password_page', email=email))
        
        name = user[0]
        
        # Generate OTP
        otp = generate_otp()
        if create_otp_record(conn, email, otp):
            conn.close()
            
            # Send email in background
            def send_reset_email_bg():
                try:
                    send_password_reset_email(email, otp, name)
                except Exception as e:
                    print(f"Reset email error: {e}")
            
            send_email_async(send_reset_email_bg)
            
            flash("A reset code has been sent to your email.", "success")
            return redirect(url_for('reset_password_page', email=email))
        
        conn.close()
        flash("Failed to generate reset code. Please try again.", "error")
    
    return render_template('forgot_password.html')


@app.route('/reset-password')
def reset_password_page():
    """Show reset password form."""
    email = request.args.get('email', '')
    if not email:
        return redirect(url_for('forgot_password'))
    return render_template('reset_password.html', email=email)


@app.route('/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    """Reset password with OTP verification."""
    email = request.form.get('email', '').lower().strip()
    otp = request.form.get('otp', '')
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not all([email, otp, password, confirm_password]):
        flash("Please fill in all fields.", "error")
        return redirect(url_for('reset_password_page', email=email))
    
    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for('reset_password_page', email=email))
    
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for('reset_password_page', email=email))
    
    conn = get_db_connection()
    
    # Verify OTP
    is_valid, message = verify_otp_code(conn, email, otp)
    
    if not is_valid:
        conn.close()
        flash(message, "error")
        return redirect(url_for('reset_password_page', email=email))
    
    # Update password
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    
    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
    cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("Password reset successfully! Please log in with your new password.", "success")
    return redirect(url_for('login'))


@app.route('/resend-reset-otp', methods=['POST'])
@limiter.limit("3 per minute")
def resend_reset_otp():
    """Resend password reset OTP."""
    email = request.form.get('email', '').lower().strip()
    
    if not email:
        return redirect(url_for('forgot_password'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        name = user[0]
        otp = generate_otp()
        if create_otp_record(conn, email, otp):
            def send_bg():
                send_password_reset_email(email, otp, name)
            send_email_async(send_bg)
            flash("A new reset code has been sent.", "success")
        else:
            flash("Failed to generate code. Please try again.", "error")
    else:
        flash("A new reset code has been sent.", "success")  # Don't reveal if email exists
    
    conn.close()
    return redirect(url_for('reset_password_page', email=email))


# Login
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    # Redirect already logged-in users to their dashboard
    if 'user_id' in session and 'role' in session:
        if session.get('is_admin'):
            return redirect('/admin/dashboard')
        elif session['role'] == 'doctor':
            return redirect('/doctor/dashboard')
        else:
            return redirect('/patient/dashboard')
    
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']

        conn = get_db_connection()
        
        # Check for account lockout (gracefully handle if columns don't exist)
        try:
            is_locked, lock_message = check_account_lockout(conn, email)
            if is_locked:
                flash(lock_message, "error")
                conn.close()
                return redirect('/login')
        except Exception:
            pass  # Account lockout columns not available yet

        cursor = conn.cursor()
        
        # Try new schema with is_admin, fall back to older schemas
        try:
            cursor.execute(
                "SELECT id, role, name, password, auth_provider, is_admin FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            has_auth_provider = True
            has_is_admin = True
        except Exception:
            try:
                cursor.execute(
                    "SELECT id, role, name, password, auth_provider FROM users WHERE email = %s",
                    (email,)
                )
                user = cursor.fetchone()
                has_auth_provider = True
                has_is_admin = False
            except Exception:
                cursor.execute(
                    "SELECT id, role, name, password FROM users WHERE email = %s",
                    (email,)
                )
                user = cursor.fetchone()
                has_auth_provider = False
                has_is_admin = False
        cursor.close()

        if user is None:
            flash("Invalid email or password", "error")
            conn.close()
            return redirect('/login')

        if has_is_admin:
            user_id, role, name, stored_password, auth_provider, is_admin = user
            # Check if user signed up with Google only
            if auth_provider == 'google' and not stored_password:
                flash("This account uses Google Sign-In. Please use the 'Sign in with Google' button.", "error")
                conn.close()
                return redirect('/login')
        elif has_auth_provider:
            user_id, role, name, stored_password, auth_provider = user
            is_admin = False
            # Check if user signed up with Google only
            if auth_provider == 'google' and not stored_password:
                flash("This account uses Google Sign-In. Please use the 'Sign in with Google' button.", "error")
                conn.close()
                return redirect('/login')
        else:
            user_id, role, name, stored_password = user
            auth_provider = 'email'
            is_admin = False

        # Verify password (handle both hashed and legacy plaintext passwords)
        password_valid = False
        if is_password_hashed(stored_password):
            password_valid = verify_password(password, stored_password)
        else:
            # Legacy plaintext password - verify and migrate
            password_valid = (stored_password == password)
            if password_valid:
                # Migrate to hashed password
                new_hash = hash_password(password)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, user_id))
                conn.commit()
                cursor.close()

        if not password_valid:
            try:
                record_failed_login(conn, email)
            except Exception:
                pass  # Failed login tracking columns not available
            flash("Invalid email or password", "error")
            conn.close()
            return redirect('/login')

        # Reset failed login attempts on successful login
        try:
            reset_failed_login(conn, email)
        except Exception:
            pass  # Failed login tracking columns not available
        
        # Track login IP and timestamp
        try:
            client_ip = get_client_ip()
            print(f"[IP TRACKING] User {user_id} login from IP: {client_ip}")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login_ip = %s, last_login_at = %s WHERE id = %s",
                (client_ip, datetime.now(), user_id)
            )
            conn.commit()
            cursor.close()
            print(f"[IP TRACKING] Successfully stored IP for user {user_id}")
        except Exception as e:
            print(f"[IP TRACKING ERROR] Failed to store IP for user {user_id}: {e}")
        
        conn.close()

        session['user_id'] = user_id
        session['role'] = role
        session['name'] = name
        session['is_admin'] = is_admin
        session.permanent = True

        # Redirect admin users to admin dashboard
        if is_admin:
            return redirect('/admin/dashboard')
        elif role == 'doctor':
            return redirect('/doctor/dashboard')
        else:
            return redirect('/patient/dashboard')

    return render_template('login.html')


# ============================================================================
# GOOGLE OAUTH ROUTES
# ============================================================================

@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth flow."""
    if not oauth.google:
        flash("Google Sign-In is not configured", "error")
        return redirect(url_for('login'))
    
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    if not oauth.google:
        flash("Google Sign-In is not configured", "error")
        return redirect(url_for('login'))
    
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash("Could not get user info from Google", "error")
            return redirect(url_for('login'))
        
        google_id = user_info.get('sub')
        email = user_info.get('email', '').lower()
        name = user_info.get('name', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists by Google ID
        cursor.execute("SELECT id, role, name FROM users WHERE google_id = %s", (google_id,))
        user = cursor.fetchone()
        
        if not user:
            # Check if user exists by email (account linking)
            cursor.execute("SELECT id, role, name FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                # Link Google account to existing user
                cursor.execute(
                    "UPDATE users SET google_id = %s, auth_provider = CASE WHEN auth_provider = 'email' THEN 'email,google' ELSE auth_provider END WHERE id = %s",
                    (google_id, user[0])
                )
                conn.commit()
            else:
                # NEW USER: Redirect to role selection page
                cursor.close()
                conn.close()
                
                # Store OAuth data in session for role selection
                session['pending_oauth'] = {
                    'google_id': google_id,
                    'email': email,
                    'name': name
                }
                
                return redirect(url_for('select_role_page'))
        
        cursor.close()
        
        # Track login IP and timestamp for Google OAuth
        try:
            client_ip = get_client_ip()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login_ip = %s, last_login_at = %s WHERE id = %s",
                (client_ip, datetime.now(), user[0])
            )
            conn.commit()
            cursor.close()
        except Exception:
            pass  # IP tracking columns not available yet
        
        conn.close()
        
        session['user_id'] = user[0]
        session['role'] = user[1]
        session['name'] = user[2]
        session.permanent = True
        
        if user[1] == 'doctor':
            return redirect('/doctor/dashboard')
        else:
            return redirect('/patient/dashboard')
            
    except Exception as e:
        print(f"Google OAuth Error: {e}")  # Log the actual error
        flash(f"Google sign-in failed. Please try again.", "error")
        return redirect(url_for('login'))


# Role Selection Page for OAuth users
@app.route('/select-role')
def select_role_page():
    """Show role selection page for new OAuth users."""
    pending = session.get('pending_oauth')
    if not pending:
        return redirect(url_for('login'))
    return render_template('select_role.html', name=pending['name'])


# Complete OAuth Registration with selected role
@app.route('/complete-oauth-registration', methods=['POST'])
def complete_oauth_registration():
    """Complete OAuth user registration with selected role."""
    pending = session.get('pending_oauth')
    if not pending:
        flash("Session expired. Please try signing in again.", "error")
        return redirect(url_for('login'))
    
    role = request.form.get('role')
    if role not in ['doctor', 'patient']:
        flash("Please select a valid role.", "error")
        return redirect(url_for('select_role_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create new user with selected role
        cursor.execute(
            "INSERT INTO users (name, email, google_id, role, auth_provider, email_verified) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, role, name",
            (pending['name'], pending['email'], pending['google_id'], role, 'google', True)
        )
        user = cursor.fetchone()
        conn.commit()
    except Exception:
        # Fall back to old schema
        try:
            cursor.execute(
                "INSERT INTO users (name, email, google_id, role, auth_provider) VALUES (%s, %s, %s, %s, %s) RETURNING id, role, name",
                (pending['name'], pending['email'], pending['google_id'], role, 'google')
            )
            user = cursor.fetchone()
            conn.commit()
        except Exception:
            cursor.execute(
                "INSERT INTO users (name, email, role) VALUES (%s, %s, %s) RETURNING id, role, name",
                (pending['name'], pending['email'], role)
            )
            user = cursor.fetchone()
            conn.commit()
    
    cursor.close()
    
    # Track login IP and timestamp for new OAuth user
    try:
        client_ip = get_client_ip()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login_ip = %s, last_login_at = %s WHERE id = %s",
            (client_ip, datetime.now(), user[0])
        )
        conn.commit()
        cursor.close()
    except Exception:
        pass  # IP tracking columns not available yet
    
    conn.close()
    
    # Clear pending OAuth data
    session.pop('pending_oauth', None)
    
    # Set session
    session['user_id'] = user[0]
    session['role'] = user[1]
    session['name'] = user[2]
    session.permanent = True
    
    flash(f"Welcome to MediCare! You've been registered as a {role}.", "success")
    
    if role == 'doctor':
        return redirect('/doctor/dashboard')
    else:
        return redirect('/patient/dashboard')


# Doctor Dashboard
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.name AS patient_name 
        FROM appointments a 
        JOIN users u ON a.patient_id = u.id 
        WHERE a.doctor_id = %s
        ORDER BY a.date ASC, a.time_slot ASC
    """, (session['user_id'],))
    colnames = [desc[0] for desc in cursor.description]
    appointments = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('doctor_dashboard.html', name=session['name'], appointments=appointments)


# Patient Dashboard
@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.name AS doctor_name 
        FROM appointments a 
        JOIN users u ON a.doctor_id = u.id 
        WHERE a.patient_id = %s
        ORDER BY a.date ASC, a.time_slot ASC
    """, (session['user_id'],))
    colnames = [desc[0] for desc in cursor.description]
    appointments = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('patient_dashboard.html', name=session['name'], appointments=appointments)


# Check available time slots for a specific doctor and date
@app.route('/check_availability')
@limiter.limit("30 per minute")
def check_availability():
    doctor_id = request.args.get('doctor_id')
    date = request.args.get('date')
    
    if not doctor_id or not date:
        return jsonify({'available_slots': []})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time_slot FROM appointments 
        WHERE doctor_id = %s AND date = %s AND status != 'Rejected'
    """, (doctor_id, date))
    booked_slots = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    all_slots = generate_time_slots()
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return jsonify({'available_slots': available_slots})


# Book Appointment
@app.route('/appointment/book', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def book_appointment():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role='doctor'")
    colnames = [desc[0] for desc in cursor.description]
    doctors = [dict(zip(colnames, row)) for row in cursor.fetchall()]

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time_slot = request.form['time_slot']
        reason = sanitize_input(request.form['reason'])

        cursor.execute("""
            SELECT id FROM appointments 
            WHERE doctor_id = %s AND date = %s AND time_slot = %s AND status != 'Rejected'
        """, (doctor_id, date, time_slot))
        existing_appointment = cursor.fetchone()
        
        if existing_appointment:
            flash('Sorry, this time slot is already booked. Please select another time.', 'error')
            cursor.close()
            conn.close()
            return render_template('book_appointment.html', doctors=doctors, time_slots=generate_time_slots())
        
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, date, time_slot, reason, status) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session['user_id'], doctor_id, date, time_slot, reason, 'Pending'))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    cursor.close()
    conn.close()
    return render_template('book_appointment.html', doctors=doctors, time_slots=generate_time_slots())


# Update Appointment Status
@app.route('/appointment/status/<int:appointment_id>/<status>')
def update_status(appointment_id, status):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    
    # Validate status
    if status not in ['Approved', 'Rejected', 'Completed']:
        flash('Invalid status', 'error')
        return redirect(url_for('doctor_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE appointments SET status = %s WHERE id = %s AND doctor_id = %s",
        (status, appointment_id, session['user_id'])
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('doctor_dashboard'))


# Delete Appointment
@app.route('/appointment/delete/<int:appointment_id>')
def delete_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if session['role'] == 'patient':
        cursor.execute(
            "DELETE FROM appointments WHERE id = %s AND patient_id = %s",
            (appointment_id, session['user_id'])
        )
    elif session['role'] == 'doctor':
        cursor.execute(
            "DELETE FROM appointments WHERE id = %s AND doctor_id = %s",
            (appointment_id, session['user_id'])
        )

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for(session['role'] + '_dashboard'))


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user statistics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'doctor'")
    total_doctors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'")
    total_patients = cursor.fetchone()[0]
    
    # Get admin count
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        total_admins = cursor.fetchone()[0]
    except Exception:
        total_admins = 0
    
    # Get appointment statistics
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending'")
    pending_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Approved'")
    approved_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Rejected'")
    rejected_appointments = cursor.fetchone()[0]
    
    # Get recent users (last 5)
    try:
        cursor.execute("""
            SELECT id, name, email, role, is_admin 
            FROM users 
            ORDER BY id DESC 
            LIMIT 5
        """)
        colnames = [desc[0] for desc in cursor.description]
        recent_users = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    except Exception:
        cursor.execute("""
            SELECT id, name, email, role 
            FROM users 
            ORDER BY id DESC 
            LIMIT 5
        """)
        colnames = [desc[0] for desc in cursor.description]
        recent_users = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        for user in recent_users:
            user['is_admin'] = False
    
    # Get recent appointments (last 5)
    cursor.execute("""
        SELECT a.id, a.date, a.time_slot, a.status, a.reason,
               p.name AS patient_name, d.name AS doctor_name
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        ORDER BY a.id DESC
        LIMIT 5
    """)
    colnames = [desc[0] for desc in cursor.description]
    recent_appointments = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    stats = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_admins': total_admins,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'approved_appointments': approved_appointments,
        'rejected_appointments': rejected_appointments
    }
    
    return render_template('admin_dashboard.html', 
                           name=session['name'], 
                           stats=stats,
                           recent_users=recent_users,
                           recent_appointments=recent_appointments)


@app.route('/admin/users')
@admin_required
def admin_users():
    """List all users with search/filter capabilities."""
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query based on filters
    query = "SELECT id, name, email, role, auth_provider, email_verified, is_admin FROM users WHERE 1=1"
    params = []
    
    if search:
        query += " AND (name ILIKE %s OR email ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    if role_filter:
        query += " AND role = %s"
        params.append(role_filter)
    
    query += " ORDER BY id DESC"
    
    try:
        cursor.execute(query, params)
        colnames = [desc[0] for desc in cursor.description]
        users = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    except Exception:
        # Fallback for older schema
        query = "SELECT id, name, email, role FROM users WHERE 1=1"
        params = []
        if search:
            query += " AND (name ILIKE %s OR email ILIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        if role_filter:
            query += " AND role = %s"
            params.append(role_filter)
        query += " ORDER BY id DESC"
        
        cursor.execute(query, params)
        colnames = [desc[0] for desc in cursor.description]
        users = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        for user in users:
            user['auth_provider'] = 'email'
            user['email_verified'] = True
            user['is_admin'] = False
    
    cursor.close()
    conn.close()
    
    return render_template('admin_users.html', 
                           name=session['name'], 
                           users=users,
                           search=search,
                           role_filter=role_filter)


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Edit user details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', ''))
        email = request.form.get('email', '').lower().strip()
        role = request.form.get('role', '')
        
        if not all([name, email, role]):
            flash("All fields are required.", "error")
            return redirect(url_for('admin_edit_user', user_id=user_id))
        
        if role not in ['doctor', 'patient']:
            flash("Invalid role.", "error")
            return redirect(url_for('admin_edit_user', user_id=user_id))
        
        cursor.execute(
            "UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s",
            (name, email, role, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("User updated successfully.", "success")
        return redirect(url_for('admin_users'))
    
    # GET request - show edit form
    try:
        cursor.execute(
            "SELECT id, name, email, role, auth_provider, is_admin FROM users WHERE id = %s",
            (user_id,)
        )
    except Exception:
        cursor.execute(
            "SELECT id, name, email, role FROM users WHERE id = %s",
            (user_id,)
        )
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('admin_users'))
    
    colnames = ['id', 'name', 'email', 'role'] if len(user) == 4 else ['id', 'name', 'email', 'role', 'auth_provider', 'is_admin']
    user_dict = dict(zip(colnames, user))
    
    return render_template('admin_edit_user.html', name=session['name'], user=user_dict)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user."""
    # Prevent self-deletion
    if user_id == session['user_id']:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete user's appointments first
    cursor.execute("DELETE FROM appointments WHERE patient_id = %s OR doctor_id = %s", (user_id, user_id))
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("User deleted successfully.", "success")
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_admin(user_id):
    """Toggle admin status for a user."""
    # Prevent self-demotion
    if user_id == session['user_id']:
        flash("You cannot modify your own admin status.", "error")
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current admin status
        cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            new_status = not result[0]
            cursor.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_status, user_id))
            conn.commit()
            flash(f"Admin status {'granted' if new_status else 'revoked'} successfully.", "success")
        else:
            flash("User not found.", "error")
    except Exception as e:
        flash("Failed to update admin status. Make sure the database has the is_admin column.", "error")
    
    cursor.close()
    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    """List all appointments with filters."""
    status_filter = request.args.get('status', '')
    doctor_filter = request.args.get('doctor', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all doctors for filter dropdown
    cursor.execute("SELECT id, name FROM users WHERE role = 'doctor' ORDER BY name")
    doctors = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    
    # Build query
    query = """
        SELECT a.id, a.date, a.time_slot, a.status, a.reason,
               a.patient_id, a.doctor_id,
               p.name AS patient_name, p.email AS patient_email,
               d.name AS doctor_name, d.email AS doctor_email
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        WHERE 1=1
    """
    params = []
    
    if status_filter:
        query += " AND a.status = %s"
        params.append(status_filter)
    
    if doctor_filter:
        query += " AND a.doctor_id = %s"
        params.append(doctor_filter)
    
    query += " ORDER BY a.date DESC, a.time_slot DESC"
    
    cursor.execute(query, params)
    colnames = [desc[0] for desc in cursor.description]
    appointments = [dict(zip(colnames, row)) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return render_template('admin_appointments.html',
                           name=session['name'],
                           appointments=appointments,
                           doctors=doctors,
                           status_filter=status_filter,
                           doctor_filter=doctor_filter)


@app.route('/admin/appointments/<int:appointment_id>/status/<status>', methods=['POST'])
@admin_required
def admin_update_appointment_status(appointment_id, status):
    """Update appointment status as admin."""
    if status not in ['Pending', 'Approved', 'Rejected', 'Completed']:
        flash("Invalid status.", "error")
        return redirect(url_for('admin_appointments'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", (status, appointment_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash(f"Appointment status updated to {status}.", "success")
    return redirect(url_for('admin_appointments'))


@app.route('/admin/appointments/<int:appointment_id>/delete', methods=['POST'])
@admin_required
def admin_delete_appointment(appointment_id):
    """Delete an appointment as admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for('admin_appointments'))


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Rate Limit Exceeded Handler
@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Too many requests. Please wait a moment before trying again.", "error")
    return redirect(request.referrer or url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

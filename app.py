from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from datetime import datetime, time
from db_config import get_db_connection
from dotenv import load_dotenv
import os

from security import (
    hash_password, verify_password, is_password_hashed,
    validate_email, validate_password_strength, sanitize_input,
    create_limiter, create_oauth, add_security_headers,
    check_account_lockout, record_failed_login, reset_failed_login
)

# Import email service for OTP
try:
    from email_service import (
        generate_otp, create_otp_record, verify_otp as verify_otp_code,
        mark_email_verified, send_otp_email, send_welcome_email, send_email_async
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
        
        # If email service is available, send OTP first
        if EMAIL_SERVICE_AVAILABLE and os.getenv('MAIL_USERNAME'):
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
                # This prevents Gunicorn worker timeout on slow SMTP
                def send_email_background():
                    try:
                        send_otp_email(email, otp, name)
                    except Exception as e:
                        print(f"Background email error: {e}")
                
                send_email_async(send_email_background)
                
                flash("A verification code has been sent to your email. Please check your inbox.", "success")
                return redirect(url_for('verify_email_page', email=email))
            else:
                flash("Failed to generate verification code. Please try again.", "error")
            
            conn.close()
            return render_template('register.html')
        
        # If email service not available, register directly (legacy flow)
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


# Login
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
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
        
        # Try new schema first, fall back to old schema
        try:
            cursor.execute(
                "SELECT id, role, name, password, auth_provider FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            has_auth_provider = True
        except Exception:
            cursor.execute(
                "SELECT id, role, name, password FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()
            has_auth_provider = False
        cursor.close()

        if user is None:
            flash("Invalid email or password", "error")
            conn.close()
            return redirect('/login')

        if has_auth_provider:
            user_id, role, name, stored_password, auth_provider = user
            # Check if user signed up with Google only
            if auth_provider == 'google' and not stored_password:
                flash("This account uses Google Sign-In. Please use the 'Sign in with Google' button.", "error")
                conn.close()
                return redirect('/login')
        else:
            user_id, role, name, stored_password = user
            auth_provider = 'email'

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
        conn.close()

        session['user_id'] = user_id
        session['role'] = role
        session['name'] = name
        session.permanent = True

        if role == 'doctor':
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
                # Create new user - default to patient role
                cursor.execute(
                    "INSERT INTO users (name, email, google_id, role, auth_provider) VALUES (%s, %s, %s, %s, %s) RETURNING id, role, name",
                    (name, email, google_id, 'patient', 'google')
                )
                user = cursor.fetchone()
                conn.commit()
                flash("Account created! You've been registered as a patient. Contact support to change your role.", "info")
        
        cursor.close()
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
        flash(f"Google sign-in failed. Please try again.", "error")
        return redirect(url_for('login'))


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

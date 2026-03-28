from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from datetime import datetime, timedelta
from db_config import get_db_connection
from security import hash_password, verify_password, is_password_hashed
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from email_service import (
    generate_otp,
    create_otp_record,
    verify_otp as verify_email_otp,
    send_otp_email,
    send_password_reset_email,
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def generate_registration_token(name, email, password_hash, role):
    s = URLSafeTimedSerializer(current_app.secret_key)
    return s.dumps({
        'name': name,
        'email': email,
        'password_hash': password_hash,
        'role': role
    })


def verify_registration_token(token, max_age_seconds=3600):
    s = URLSafeTimedSerializer(current_app.secret_key)
    try:
        return s.loads(token, max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return None


def ensure_email_verification_table(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            otp VARCHAR(10) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()

def generate_token(user_id, role):
    s = URLSafeTimedSerializer(current_app.secret_key)
    return s.dumps({'user_id': user_id, 'role': role})

def verify_token(token):
    s = URLSafeTimedSerializer(current_app.secret_key)
    try:
        data = s.loads(token, max_age=86400 * 30) # 30 days valid
    except (SignatureExpired, BadSignature):
        return None
    return data

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        data = verify_token(token)
        if not data:
            return jsonify({'message': 'Token is invalid or expired!'}), 401

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, role, name, email FROM users WHERE id = %s", (data['user_id'],))
        current_user = cur.fetchone()
        cur.close()
        conn.close()

        if not current_user:
            return jsonify({'message': 'User not found!'}), 401
            
        user_obj = {
            'id': current_user[0],
            'role': (current_user[1] or '').lower(),
            'name': current_user[2],
            'email': current_user[3]
        }
        return f(user_obj, *args, **kwargs)
    return decorated


def admin_token_required(f):
    @token_required
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        conn = get_db_connection()
        cur = conn.cursor()
        is_admin = False
        try:
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (current_user['id'],))
            row = cur.fetchone()
            is_admin = bool(row and row[0])
        except Exception:
            is_admin = (current_user.get('role', '').lower() == 'admin')
        finally:
            cur.close()
            conn.close()

        if not is_admin and current_user.get('role', '').lower() != 'admin':
            return jsonify({'message': 'Admin access required'}), 403

        return f(current_user, *args, **kwargs)

    return decorated

@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400

    email = data.get('email').lower().strip()
    password = data.get('password')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, role, name, email, password, is_admin FROM users WHERE email = %s",
            (email,)
        )
        user = cur.fetchone()
    except Exception:
        cur.execute("SELECT id, role, name, email, password FROM users WHERE email = %s", (email,))
        base_user = cur.fetchone()
        user = (*base_user, False) if base_user else None
    cur.close()
    conn.close()

    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    user_id, role, name, u_email, stored_password, is_admin = user
    normalized_role = (role or '').lower()
    
    password_valid = False
    if is_password_hashed(stored_password):
        password_valid = verify_password(password, stored_password)
    else:
        password_valid = (stored_password == password)

    if not password_valid:
        return jsonify({'message': 'Invalid credentials'}), 401
        
    effective_role = 'admin' if is_admin else normalized_role
    token = generate_token(user_id, effective_role)
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user_id,
            'name': name,
            'email': u_email,
            'role': effective_role,
            'token': token
        }
    }), 200

@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'email', 'password', 'role')):
        return jsonify({'message': 'Missing fields'}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (data['email'].lower(),))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'message': 'Email already exists'}), 409
        
    hashed_password = hash_password(data['password'])
    cur.execute(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id",
        (data['name'], data['email'].lower(), hashed_password, data['role'])
    )
    new_user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    token = generate_token(new_user_id, data['role'])
    
    return jsonify({
        'message': 'Registration successful',
        'user': {
            'id': new_user_id,
            'name': data['name'],
            'email': data['email'].lower(),
            'role': data['role'],
            'token': token
        }
    }), 201


@api_bp.route('/register/send_otp', methods=['POST'])
def register_send_otp():
    data = request.get_json() or {}
    required = ('name', 'email', 'password', 'role')
    if not all(k in data and str(data.get(k)).strip() for k in required):
        return jsonify({'message': 'Missing fields'}), 400

    name = str(data.get('name')).strip()
    email = str(data.get('email')).strip().lower()
    password = str(data.get('password'))
    role = str(data.get('role')).strip().lower()

    if role not in ('patient', 'doctor'):
        return jsonify({'message': 'Invalid role'}), 400
    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'message': 'Email already exists'}), 409

    try:
        ensure_email_verification_table(conn)
        otp = generate_otp()
        if not create_otp_record(conn, email, otp):
            cur.close()
            conn.close()
            return jsonify({'message': 'Could not generate OTP. Try again.'}), 500

        sent, email_message = send_otp_email(email, otp, name)
        if not sent:
            cur.close()
            conn.close()
            return jsonify({'message': f'Failed to send OTP email: {email_message}'}), 500

        password_hash = hash_password(password)
        verification_token = generate_registration_token(name, email, password_hash, role)

        cur.close()
        conn.close()
        return jsonify({
            'message': 'OTP sent to your email address',
            'email': email,
            'verification_token': verification_token
        }), 200
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({'message': f'Could not send OTP: {str(e)}'}), 500


@api_bp.route('/register/resend_otp', methods=['POST'])
def register_resend_otp():
    data = request.get_json() or {}
    verification_token = data.get('verification_token')
    if not verification_token:
        return jsonify({'message': 'Missing verification_token'}), 400

    token_data = verify_registration_token(verification_token)
    if not token_data:
        return jsonify({'message': 'Verification session expired. Please register again.'}), 401

    email = token_data.get('email', '').strip().lower()
    name = token_data.get('name', 'User').strip() or 'User'
    if not email:
        return jsonify({'message': 'Invalid verification token'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'message': 'Email already exists. Please login.'}), 409

    try:
        ensure_email_verification_table(conn)
        otp = generate_otp()
        if not create_otp_record(conn, email, otp):
            cur.close()
            conn.close()
            return jsonify({'message': 'Could not generate OTP. Try again.'}), 500

        sent, email_message = send_otp_email(email, otp, name)
        if not sent:
            cur.close()
            conn.close()
            return jsonify({'message': f'Failed to send OTP email: {email_message}'}), 500

        cur.close()
        conn.close()
        return jsonify({'message': 'OTP resent successfully'}), 200
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({'message': f'Could not resend OTP: {str(e)}'}), 500


@api_bp.route('/register/verify_otp', methods=['POST'])
def register_verify_otp():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    otp = str(data.get('otp', '')).strip()
    verification_token = data.get('verification_token')

    if not email or not otp or not verification_token:
        return jsonify({'message': 'Missing fields'}), 400

    token_data = verify_registration_token(verification_token)
    if not token_data:
        return jsonify({'message': 'Verification session expired. Please register again.'}), 401

    token_email = str(token_data.get('email', '')).strip().lower()
    if token_email != email:
        return jsonify({'message': 'Email mismatch for verification'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'message': 'Email already exists. Please login.'}), 409

    try:
        ensure_email_verification_table(conn)
        is_valid, verify_message = verify_email_otp(conn, email, otp)
        if not is_valid:
            cur.close()
            conn.close()
            return jsonify({'message': verify_message}), 400

        name = str(token_data.get('name', '')).strip()
        role = str(token_data.get('role', '')).strip().lower()
        password_hash = str(token_data.get('password_hash', '')).strip()

        if not name or not role or not password_hash:
            cur.close()
            conn.close()
            return jsonify({'message': 'Invalid verification token payload'}), 400

        if role not in ('patient', 'doctor'):
            cur.close()
            conn.close()
            return jsonify({'message': 'Invalid role in verification token'}), 400

        try:
            cur.execute(
                """
                INSERT INTO users (name, email, password, role, email_verified, auth_provider)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, email, password_hash, role, True, 'email')
            )
        except Exception:
            conn.rollback()
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, email, password_hash, role)
            )

        new_user_id = cur.fetchone()[0]
        cur.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
        conn.commit()

        token = generate_token(new_user_id, role)
        cur.close()
        conn.close()
        return jsonify({
            'message': 'Email verified and registration successful',
            'user': {
                'id': new_user_id,
                'name': name,
                'email': email,
                'role': role,
                'token': token
            }
        }), 201
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'message': f'Could not complete verification: {str(e)}'}), 500


@api_bp.route('/password/forgot', methods=['POST'])
def password_forgot():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    if not email:
        return jsonify({'message': 'Missing email'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name FROM users WHERE email = %s", (email,))
        user_row = cur.fetchone()
        if not user_row:
            cur.close()
            conn.close()
            return jsonify({'message': 'No account found with this email'}), 404

        user_name = user_row[1] or 'User'

        ensure_email_verification_table(conn)
        otp = generate_otp()
        if not create_otp_record(conn, email, otp):
            cur.close()
            conn.close()
            return jsonify({'message': 'Could not generate reset OTP. Try again.'}), 500

        sent, email_message = send_password_reset_email(email, otp, user_name)
        if not sent:
            cur.close()
            conn.close()
            return jsonify({'message': f'Failed to send reset code: {email_message}'}), 500

        cur.close()
        conn.close()
        return jsonify({'message': 'Password reset OTP sent to your email'}), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'message': f'Could not process forgot password: {str(e)}'}), 500


@api_bp.route('/password/reset', methods=['POST'])
def password_reset():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    otp = str(data.get('otp', '')).strip()
    new_password = str(data.get('new_password', '')).strip()

    if not email or not otp or not new_password:
        return jsonify({'message': 'Missing fields'}), 400
    if len(new_password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_row = cur.fetchone()
        if not user_row:
            cur.close()
            conn.close()
            return jsonify({'message': 'No account found with this email'}), 404

        ensure_email_verification_table(conn)
        is_valid, verify_message = verify_email_otp(conn, email, otp)
        if not is_valid:
            cur.close()
            conn.close()
            return jsonify({'message': verify_message}), 400

        hashed_password = hash_password(new_password)
        cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        cur.execute("DELETE FROM email_verifications WHERE email = %s", (email,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Password reset successful. Please login with your new password.'}), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'message': f'Could not reset password: {str(e)}'}), 500

# APPOINTMENTS Endpoints
@api_bp.route('/patient/appointments', methods=['GET'])
@token_required
def get_patient_appointments(current_user):
    if (current_user.get('role') or '').lower() != 'patient':
        return jsonify({'message': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if appointments table exists
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'appointments')")
    exists = cur.fetchone()[0]
    if not exists:
        cur.close()
        conn.close()
        return jsonify([]), 200

    cur.execute("""
        SELECT a.id, a.doctor_id, d.name as doctor_name, a.patient_id, p.name as patient_name, a.date, a.time_slot, a.status, a.reason 
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        JOIN users p ON a.patient_id = p.id
        WHERE a.patient_id = %s
        ORDER BY a.date DESC, a.time_slot DESC
    """, (current_user['id'],))
    
    appointments = []
    for row in cur.fetchall():
        appointments.append({
            'id': row[0],
            'doctor_id': row[1],
            'doctor_name': row[2],
            'patient_id': row[3],
            'patient_name': row[4],
            'date': str(row[5]),
            'time_slot': row[6],
            'status': row[7],
            'reason': row[8]
        })
    cur.close()
    conn.close()
    return jsonify(appointments), 200

@api_bp.route('/doctor/appointments', methods=['GET'])
@token_required
def get_doctor_appointments(current_user):
    if (current_user.get('role') or '').lower() != 'doctor':
        return jsonify({'message': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'appointments')")
    exists = cur.fetchone()[0]
    if not exists:
        cur.close()
        conn.close()
        return jsonify([]), 200

    cur.execute("""
        SELECT a.id, a.doctor_id, d.name as doctor_name, a.patient_id, p.name as patient_name, a.date, a.time_slot, a.status, a.reason 
        FROM appointments a
        JOIN users d ON a.doctor_id = d.id
        JOIN users p ON a.patient_id = p.id
        WHERE a.doctor_id = %s
        ORDER BY a.date DESC, a.time_slot DESC
    """, (current_user['id'],))
    
    appointments = []
    for row in cur.fetchall():
        appointments.append({
            'id': row[0],
            'doctor_id': row[1],
            'doctor_name': row[2],
            'patient_id': row[3],
            'patient_name': row[4],
            'date': str(row[5]),
            'time_slot': row[6],
            'status': row[7],
            'reason': row[8]
        })
    cur.close()
    conn.close()
    return jsonify(appointments), 200

@api_bp.route('/doctors', methods=['GET'])
@token_required
def get_doctors(current_user):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE LOWER(role) = 'doctor'")
    doctors = []
    for row in cur.fetchall():
        doctors.append({
            'id': row[0],
            'name': row[1],
            'specialty': 'General' # Mock specialty since schema doesn't have it
        })
    cur.close()
    conn.close()
    return jsonify(doctors), 200

@api_bp.route('/check_availability', methods=['GET'])
@token_required
def check_availability(current_user):
    doctor_id = request.args.get('doctor_id')
    date = request.args.get('date')
    
    if not doctor_id or not date:
        return jsonify({'message': 'Missing doctor_id or date'}), 400
        
    # Generate all possible slots (9 AM to 5 PM, 30 min)
    all_slots = []
    for hour in range(9, 17):
        for minute in ['00', '30']:
            # Format as 09:00 AM, etc.
            h = hour if hour <= 12 else hour - 12
            if h == 0: h = 12
            ampm = 'AM' if hour < 12 else 'PM'
            all_slots.append(f"{h:02d}:{minute} {ampm}")
            
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'appointments')")
    exists = cur.fetchone()[0]
    if not exists:
        cur.close()
        conn.close()
        return jsonify({'available_slots': all_slots}), 200

    cur.execute("SELECT time_slot FROM appointments WHERE doctor_id = %s AND date = %s AND status != 'Cancelled'", (doctor_id, date))
    booked = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    available = [s for s in all_slots if s not in booked]
    return jsonify({'available_slots': available}), 200

@api_bp.route('/appointment/book', methods=['POST'])
@token_required
def book_appointment(current_user):
    data = request.get_json()
    if not data or not all(k in data for k in ('doctor_id', 'date', 'time_slot', 'reason')):
        return jsonify({'message': 'Missing fields'}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create appointments table if it doesn't exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES users(id),
        doctor_id INTEGER REFERENCES users(id),
        date DATE NOT NULL,
        time_slot VARCHAR(20) NOT NULL,
        status VARCHAR(20) DEFAULT 'Pending',
        reason TEXT
    )
    """)
    conn.commit()
    
    # Check if slot is already booked
    cur.execute("SELECT id FROM appointments WHERE doctor_id = %s AND date = %s AND time_slot = %s AND status != 'Cancelled'", 
                (data['doctor_id'], data['date'], data['time_slot']))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({'message': 'Slot is no longer available'}), 409
        
    cur.execute("""
        INSERT INTO appointments (patient_id, doctor_id, date, time_slot, status, reason)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (current_user['id'], data['doctor_id'], data['date'], data['time_slot'], 'Pending', data['reason']))
    
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'Appointment booked successfully'}), 201

@api_bp.route('/appointment/update_status', methods=['POST'])
@token_required
def update_status(current_user):
    data = request.get_json()
    if not data or not all(k in data for k in ('appointment_id', 'status')):
        return jsonify({'message': 'Missing fields'}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET status = %s WHERE id = %s AND doctor_id = %s", 
                (data['status'], data['appointment_id'], current_user['id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'Status updated successfully'}), 200

@api_bp.route('/appointment/delete', methods=['DELETE'])
@token_required
def delete_appointment(current_user):
    appointment_id = request.args.get('appointment_id')
    if not appointment_id:
        return jsonify({'message': 'Missing appointment_id'}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    # allow patient or doctor to delete
    cur.execute("DELETE FROM appointments WHERE id = %s AND (patient_id = %s OR doctor_id = %s)", 
                (appointment_id, current_user['id'], current_user['id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'Appointment deleted successfully'}), 200


# ADMIN Endpoints
@api_bp.route('/admin/dashboard', methods=['GET'])
@admin_token_required
def admin_dashboard(current_user):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(role) = 'doctor'")
    total_doctors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE LOWER(role) = 'patient'")
    total_patients = cur.fetchone()[0]

    try:
        cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
        total_admins = cur.fetchone()[0]
    except Exception:
        total_admins = 0

    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'appointments')")
    has_appointments = cur.fetchone()[0]

    if has_appointments:
        cur.execute("SELECT COUNT(*) FROM appointments")
        total_appointments = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending'")
        pending_appointments = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Approved'")
        approved_appointments = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Rejected'")
        rejected_appointments = cur.fetchone()[0]
    else:
        total_appointments = 0
        pending_appointments = 0
        approved_appointments = 0
        rejected_appointments = 0

    recent_users = []
    try:
        cur.execute("SELECT id, name, email, role, is_admin FROM users ORDER BY id DESC LIMIT 5")
        for row in cur.fetchall():
            recent_users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'is_admin': bool(row[4])
            })
    except Exception:
        cur.execute("SELECT id, name, email, role FROM users ORDER BY id DESC LIMIT 5")
        for row in cur.fetchall():
            recent_users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'is_admin': False
            })

    recent_appointments = []
    if has_appointments:
        cur.execute("""
            SELECT a.id, a.patient_id, a.doctor_id, p.name, d.name, p.email, d.email, a.date, a.time_slot, a.reason, a.status
            FROM appointments a
            JOIN users p ON a.patient_id = p.id
            JOIN users d ON a.doctor_id = d.id
            ORDER BY a.id DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            recent_appointments.append({
                'id': row[0],
                'patient_id': row[1],
                'doctor_id': row[2],
                'patient_name': row[3],
                'doctor_name': row[4],
                'patient_email': row[5],
                'doctor_email': row[6],
                'date': str(row[7]),
                'time_slot': row[8],
                'reason': row[9],
                'status': row[10]
            })

    cur.close()
    conn.close()

    return jsonify({
        'stats': {
            'total_users': total_users,
            'total_doctors': total_doctors,
            'total_patients': total_patients,
            'total_admins': total_admins,
            'total_appointments': total_appointments,
            'pending_appointments': pending_appointments,
            'approved_appointments': approved_appointments,
            'rejected_appointments': rejected_appointments
        },
        'recent_users': recent_users,
        'recent_appointments': recent_appointments
    }), 200


@api_bp.route('/admin/users', methods=['GET'])
@admin_token_required
def admin_users(current_user):
    conn = get_db_connection()
    cur = conn.cursor()

    users = []
    try:
        cur.execute("SELECT id, name, email, role, is_admin, email_verified, auth_provider FROM users ORDER BY id DESC")
        for row in cur.fetchall():
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'is_admin': bool(row[4]),
                'email_verified': bool(row[5]) if row[5] is not None else True,
                'auth_provider': row[6] or 'email'
            })
    except Exception:
        cur.execute("SELECT id, name, email, role FROM users ORDER BY id DESC")
        for row in cur.fetchall():
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'is_admin': False,
                'email_verified': True,
                'auth_provider': 'email'
            })

    cur.close()
    conn.close()
    return jsonify(users), 200


@api_bp.route('/admin/seed_doctor_appointments', methods=['POST'])
@admin_token_required
def admin_seed_doctor_appointments(current_user):
    conn = get_db_connection()
    cur = conn.cursor()

    # Ensure appointments table exists.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES users(id),
        doctor_id INTEGER REFERENCES users(id),
        date DATE NOT NULL,
        time_slot VARCHAR(20) NOT NULL,
        status VARCHAR(20) DEFAULT 'Pending',
        reason TEXT
    )
    """)
    conn.commit()

    cur.execute("SELECT id FROM users WHERE LOWER(role) = 'patient' ORDER BY id LIMIT 1")
    patient_row = cur.fetchone()
    if not patient_row:
        cur.close()
        conn.close()
        return jsonify({'message': 'No patient user found. Create at least one patient first.'}), 400

    patient_id = patient_row[0]

    cur.execute("SELECT id, name FROM users WHERE LOWER(role) = 'doctor' ORDER BY id")
    doctors = cur.fetchall()
    if not doctors:
        cur.close()
        conn.close()
        return jsonify({'message': 'No doctor users found.'}), 400

    seeded = 0
    skipped = 0
    base_date = datetime.utcnow().date() + timedelta(days=1)
    slot_choices = ['10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM']

    for index, (doctor_id, doctor_name) in enumerate(doctors):
        cur.execute("SELECT COUNT(*) FROM appointments WHERE doctor_id = %s", (doctor_id,))
        existing_count = cur.fetchone()[0]
        if existing_count > 0:
            skipped += 1
            continue

        appt_date = base_date + timedelta(days=index)
        time_slot = slot_choices[index % len(slot_choices)]
        cur.execute(
            """
            INSERT INTO appointments (patient_id, doctor_id, date, time_slot, status, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (patient_id, doctor_id, appt_date, time_slot, 'Pending', f'Seeded appointment for Dr. {doctor_name}')
        )
        seeded += 1

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': f'Seed complete. Added {seeded} appointments, skipped {skipped} doctors with existing records.'}), 200


@api_bp.route('/admin/users/toggle_admin', methods=['POST'])
@admin_token_required
def admin_toggle_admin(current_user):
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'message': 'Missing user_id'}), 400

    user_id = int(data['user_id'])
    if user_id == current_user['id']:
        return jsonify({'message': 'You cannot modify your own admin status'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404

        new_status = not bool(row[0])
        cur.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_status, user_id))
        conn.commit()
        message = 'Admin status granted successfully' if new_status else 'Admin status revoked successfully'
        cur.close()
        conn.close()
        return jsonify({'message': message}), 200
    except Exception:
        cur.close()
        conn.close()
        return jsonify({'message': 'is_admin column is missing in users table'}), 500


@api_bp.route('/admin/users/delete', methods=['DELETE'])
@admin_token_required
def admin_delete_user(current_user):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'message': 'Missing user_id'}), 400

    user_id = int(user_id)
    if user_id == current_user['id']:
        return jsonify({'message': 'You cannot delete your own account'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE patient_id = %s OR doctor_id = %s", (user_id, user_id))
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'User deleted successfully'}), 200


@api_bp.route('/admin/appointments', methods=['GET'])
@admin_token_required
def admin_appointments(current_user):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'appointments')")
    has_appointments = cur.fetchone()[0]
    if not has_appointments:
        cur.close()
        conn.close()
        return jsonify([]), 200

    cur.execute("""
        SELECT a.id, a.patient_id, a.doctor_id,
               p.name AS patient_name, d.name AS doctor_name,
               p.email AS patient_email, d.email AS doctor_email,
               a.date, a.time_slot, a.reason, a.status
        FROM appointments a
        JOIN users p ON a.patient_id = p.id
        JOIN users d ON a.doctor_id = d.id
        ORDER BY a.date DESC, a.time_slot DESC
    """)

    appointments = []
    for row in cur.fetchall():
        appointments.append({
            'id': row[0],
            'patient_id': row[1],
            'doctor_id': row[2],
            'patient_name': row[3],
            'doctor_name': row[4],
            'patient_email': row[5],
            'doctor_email': row[6],
            'date': str(row[7]),
            'time_slot': row[8],
            'reason': row[9],
            'status': row[10]
        })

    cur.close()
    conn.close()
    return jsonify(appointments), 200


@api_bp.route('/admin/appointments/update_status', methods=['POST'])
@admin_token_required
def admin_update_appointment_status(current_user):
    data = request.get_json()
    if not data or not all(k in data for k in ('appointment_id', 'status')):
        return jsonify({'message': 'Missing fields'}), 400

    status = str(data['status']).strip().capitalize()
    if status not in ['Pending', 'Approved', 'Rejected', 'Completed']:
        return jsonify({'message': 'Invalid status'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET status = %s WHERE id = %s", (status, data['appointment_id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': f'Appointment status updated to {status}'}), 200


@api_bp.route('/admin/appointments/delete', methods=['DELETE'])
@admin_token_required
def admin_delete_appointment(current_user):
    appointment_id = request.args.get('appointment_id')
    if not appointment_id:
        return jsonify({'message': 'Missing appointment_id'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'Appointment deleted successfully'}), 200

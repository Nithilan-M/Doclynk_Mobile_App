from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from datetime import datetime, time
from db_config import get_db_connection
from dotenv import load_dotenv
import os

app.config["DEBUG"] = True

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")   # secret key is now from .env


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
def register():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password, role),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s AND password = %s",
            (email, password)
        )
        user = cursor.fetchone()
        colnames = [desc[0] for desc in cursor.description]  # get column names
        cursor.close()
        conn.close()

        if user:
            user_dict = dict(zip(colnames, user))
            session['user_id'] = user_dict['id']
            session['role'] = user_dict['role']
            session['name'] = user_dict['name']

            if user_dict['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            return "Invalid credentials"

    return render_template('login.html')


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
        reason = request.form['reason']

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


if __name__ == '__main__':
    app.run(debug=True)

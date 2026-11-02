from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import (
    Flask, render_template, request,
    redirect, url_for, session
)

import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

# Local development settings
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=1800
)


DATABASE = "barber_bookings.db"

# Demo admin credentials.
# Change these before making the website public.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

ALLOWED_STATUSES = [
    "Pending",
    "Approved",
    "Rejected",
    "Completed",
    "Cancelled"
]


# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# CREATE DATABASE
def create_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            price INTEGER DEFAULT 0,
            Branch TEXT DEFAULT 'Branch 1'
        )
    """)

    # Add price column if missing
    columns = conn.execute(
        "PRAGMA table_info(bookings)"
    ).fetchall()

    column_names = [column['name'] for column in columns]

    if 'price' not in column_names:
        conn.execute(
            "ALTER TABLE bookings ADD COLUMN price INTEGER DEFAULT 0"
        )

    if 'branch' not in column_names:
         conn.execute(
        "ALTER TABLE bookings ADD COLUMN branch TEXT DEFAULT 'Branch 1'"
         )

    # Create customer reviews table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            review TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()



# CUSTOMER HOMEPAGE

@app.route('/')
def home():
    conn = get_db()

    reviews = conn.execute("""
        SELECT * FROM reviews
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template('index.html', reviews=reviews)


@app.route('/submit-review', methods=['POST'])
def submit_review():

    customer_name = request.form.get('customer_name', '').strip()
    review = request.form.get('review', '').strip()

    if not customer_name or not review:
        return "Please complete all review fields.", 400

    if len(customer_name) > 100 or len(review) > 1000:
        return "Your review is too long.", 400

    conn = get_db()

    conn.execute("""
        INSERT INTO reviews (customer_name, review)
        VALUES (?, ?)
    """, (customer_name, review))

    conn.commit()
    conn.close()

    return redirect(url_for('home'))




# CUSTOMER BOOKING

@app.route('/booking', methods=['GET', 'POST'])
def booking():

    error = None

    if request.method == 'POST':

        name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        branch = request.form.get('branch', '').strip()
        service = request.form.get('service', '').strip()
        date = request.form.get('date', '')
        time = request.form.get('time', '')

        prices = {
            "Low Cut": 30,
            "Skin Fade": 40,
            "Low Fade": 35,
            "Mid Fade": 40,
            "High Fade": 40,
            "Burst Fade": 45,
            "Taper Fade": 35,
            "Afro": 40,
            "Waves": 40,
            "Mohawk": 45,
            "Buzz Cut": 30,
            "Crew Cut": 30,
            "Beard Trim": 15,
            "Haircut and Beard": 50
        }

        price = prices.get(service, 0)

        if not all([name, phone, branch, service, date, time]):
            error = "Please complete all fields."

        else:
            try:
                appointment = datetime.strptime(
                    date + " " + time,
                    "%Y-%m-%d %H:%M"
                )

                if appointment <= datetime.now():
                    error = "Please choose a future date and time."

                elif appointment.hour < 8 or appointment.hour >= 20:
                    error = "Appointments are only available between 8:00 AM and 8:00 PM."

            except ValueError:
                error = "Invalid appointment date or time."

        if error is None:

            conn = get_db()
            conn.execute("BEGIN IMMEDIATE")

            existing = conn.execute("""
                SELECT id FROM bookings
                WHERE appointment_date = ?
                AND appointment_time = ?
                AND status != 'Cancelled'
            """, (date, time)).fetchone()

            if existing:
                conn.rollback()
                conn.close()
                error = "This appointment time is already booked."

            else:
                cursor = conn.execute("""
                    INSERT INTO bookings
                    (full_name, phone, branch, service,
                    appointment_date, appointment_time, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, phone, branch, service, date, time, price))

                booking_id = cursor.lastrowid

                conn.commit()
                conn.close()

                return redirect(
                    url_for('booking_success',
                            booking_id=booking_id)
                )

    return render_template('booking.html', error=error)

    
# BOOKING SUCCESS PAGE

@app.route('/booking/success/<int:booking_id>')
def booking_success(booking_id):

    conn = get_db()

    booking = conn.execute("""
        SELECT * FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    conn.close()

    if booking is None:
        return "Booking not found.", 404

    return render_template(
        'success.html',
        booking=booking
    )


# CUSTOMER APPOINTMENT LOOKUP

@app.route('/my-booking', methods=['GET', 'POST'])
def my_booking():

    booking = None
    error = None

    if request.method == 'POST':

        booking_id = request.form.get('booking_id', '').strip()
        phone = request.form.get('phone', '').strip()

        if not booking_id.isdigit() or not phone:
            error = "Please enter a valid booking reference and phone number."

        else:
            conn = get_db()

            booking = conn.execute("""
                SELECT * FROM bookings
                WHERE id = ? AND phone = ?
            """, (int(booking_id), phone)).fetchone()

            conn.close()

            if booking is None:
                error = "No matching appointment found."

    return render_template(
        'my_booking.html',
        booking=booking,
        error=error
    )

# CUSTOMER CANCELLATION
@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):

    phone = request.form.get('phone', '').strip()

    conn = get_db()

    booking = conn.execute("""
        SELECT * FROM bookings
        WHERE id = ? AND phone = ?
    """, (booking_id, phone)).fetchone()

    if booking is None:
        conn.close()
        return "Appointment not found.", 404

    if booking['status'] not in ['Pending', 'Approved']:
        conn.close()
        return "This appointment can no longer be cancelled.", 400

    conn.execute("""
        UPDATE bookings
        SET status = 'Cancelled'
        WHERE id = ?
    """, (booking_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('my_booking_result',
                            booking_id=booking_id,
                            phone=phone))



# SHOW UPDATED BOOKING AFTER CANCELLATION
@app.route('/my-booking/result/<int:booking_id>')
def my_booking_result(booking_id):

    phone = request.args.get('phone', '')

    conn = get_db()

    booking = conn.execute("""
        SELECT * FROM bookings
        WHERE id = ? AND phone = ?
    """, (booking_id, phone)).fetchone()

    conn.close()

    if booking is None:
        return "Appointment not found.", 404

    return render_template(
        'my_booking.html',
        booking=booking,
        error=None
    )


# ADMIN LOGIN
@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes")
def admin_login():

    error = None

    if request.method == 'POST':

        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if (username == ADMIN_USERNAME and
                password == ADMIN_PASSWORD):

            session['admin_logged_in'] = True

            return redirect(url_for('admin_dashboard'))

        error = "Incorrect username or password."

    return render_template(
        'admin_login.html',
        error=error
    )


# ADMIN DASHBOARD



@app.route('/admin/dashboard')
def admin_dashboard():

    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()

    # Branch filter
    branch_filter = request.args.get('branch', 'All')

    if branch_filter not in ['All', 'Branch 1', 'Branch 2']:
        branch_filter = 'All'

    if branch_filter == 'All':
        bookings = conn.execute("""
            SELECT * FROM bookings
            ORDER BY appointment_date DESC,
                     appointment_time DESC
        """).fetchall()
    else:
        bookings = conn.execute("""
            SELECT * FROM bookings
            WHERE branch = ?
            ORDER BY appointment_date DESC,
                     appointment_time DESC
        """, (branch_filter,)).fetchall()

    # Get customer reviews
    reviews = conn.execute("""
        SELECT * FROM reviews
        ORDER BY id DESC
    """).fetchall()

    # Business statistics
    stats = conn.execute("""
        SELECT
            COUNT(*) AS total_bookings,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN status = 'Completed' THEN price ELSE 0 END) AS revenue
        FROM bookings
    """).fetchone()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        bookings=bookings,
        reviews=reviews,
        stats=stats,
        branch_filter=branch_filter
    )

# UPDATE BOOKING STATUS
@app.route(
    '/admin/update/<int:booking_id>',
    methods=['POST']
)
def update_booking(booking_id):

    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    status = request.form.get('status')

    if status not in ALLOWED_STATUSES:
        return "Invalid booking status", 400

    conn = get_db()

    conn.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (status, booking_id))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))


# ADMIN LOGOUT
@app.route('/admin/delete-review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()

    conn.execute(
        "DELETE FROM reviews WHERE id = ?",
        (review_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))
@app.route('/admin/logout')
def admin_logout():

    session.clear()

    return redirect(url_for('admin_login'))


# START APPLICATION
if __name__ == '__main__':
    create_database()
    app.run(debug=False)


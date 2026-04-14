import os
import random
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "bca_super_secret_key"

# Database Connection
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="Final_project", 
        user="postgres",         
        password="free" 
    )
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch Vehicles for Section 1 & 2
    cur.execute("SELECT * FROM Vehicles")
    vehicles = cur.fetchall()
    
    # Fetch Drivers for Section 2 & 3
    cur.execute("SELECT * FROM Drivers")
    drivers = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # We pass 'vehicles' and 'drivers' to the HTML
    return render_template('index.html', vehicles=vehicles, drivers=drivers)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['full_name'] # Get the name from the form
        email = request.form['email']
        phone = request.form['phone']
        pwd = request.form['password']
        
        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        # Add 'name' to the temporary session data
        session['reg_data'] = {'name': name, 'email': email, 'phone': phone, 'pwd': pwd}
        
        print(f"DEBUG OTP: {otp}")
        return redirect(url_for('verify'))
    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == session.get('otp'):
            data = session.get('reg_data')
            conn = get_db_connection()
            cur = conn.cursor()
            # Update the INSERT to include full_name
            cur.execute("INSERT INTO Users (full_name, email, phone_number, password_hash, is_verified) VALUES (%s, %s, %s, %s, %s)",
                        (data['name'], data['email'], data['phone'], data['pwd'], True))
            conn.commit()
            # ... rest of your code ...
            cur.close()
            conn.close()
            flash("Registration Successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid OTP!", "danger")
    return render_template('verify.html')

@app.route('/book/<service_type>/<int:item_id>')
def book_form(service_type, item_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    item = None
    if service_type in ['self', 'chauffeur']:
        cur.execute("SELECT * FROM Vehicles WHERE vehicle_id = %s", (item_id,))
        item = cur.fetchone()
    elif service_type == 'driver-only':
        cur.execute("SELECT * FROM Drivers WHERE driver_id = %s", (item_id,))
        item = cur.fetchone()
        
    cur.close()
    conn.close()
    return render_template('booking.html', item=item, service_type=service_type)

@app.route('/confirm-booking', methods=['POST'])
def confirm_booking():
    # 1. Check if user is logged in
    if 'user_id' not in session:
        flash("Please login to book a ride", "warning")
        return redirect(url_for('login'))

    # 2. Get the ACTUAL user_id from the session
    current_user_id = session['user_id']
    
    service_type = request.form['service_type']
    item_id = request.form['item_id']
    duration = int(request.form['duration'])
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    total_price = 0
    booking_otp = str(random.randint(1000, 9999))
    
    # 3. Use current_user_id in all your INSERT queries below
    if service_type == 'self':
        cur.execute("SELECT price_per_day FROM Vehicles WHERE vehicle_id = %s", (item_id,))
        price = cur.fetchone()[0]
        total_price = price * duration
        cur.execute("""INSERT INTO Bookings (user_id, vehicle_id, booking_type, total_price, booking_otp, status) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (current_user_id, item_id, 'Self_Drive', total_price, booking_otp, 'Pending'))

    elif service_type == 'chauffeur':
        cur.execute("SELECT price_per_day FROM Vehicles WHERE vehicle_id = %s", (item_id,))
        v_price = cur.fetchone()[0]
        total_price = (v_price + 15) * duration
        cur.execute("""INSERT INTO Bookings (user_id, vehicle_id, driver_id, booking_type, total_price, booking_otp, status) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (current_user_id, item_id, 1, 'Chauffeur_Driven', total_price, booking_otp, 'Pending'))

    elif service_type == 'driver-only':
        cur.execute("SELECT hourly_rate FROM Drivers WHERE driver_id = %s", (item_id,))
        rate = cur.fetchone()[0]
        total_price = (rate * duration) + 55
        cur.execute("""INSERT INTO Bookings (user_id, driver_id, booking_type, total_price, booking_otp, status) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (current_user_id, item_id, 'Driver_Only', total_price, booking_otp, 'Pending'))

    conn.commit()
    cur.close()
    conn.close()
    return render_template('success.html', price=total_price, otp=booking_otp)

@app.route('/admin')
def admin_dashboard():
    # ... security check ...
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT b.booking_id,    -- Index 0
        u.full_name,     -- Index 1
        v.name,          -- Index 2
        d.name,          -- Index 3
        b.booking_type,  -- Index 4
        b.total_price,   -- Index 5
        b.status,        -- Index 6
        b.booking_otp    -- Index 7
    FROM Bookings b
        JOIN Users u ON b.user_id = u.user_id
        LEFT JOIN Vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN Drivers d ON b.driver_id = d.driver_id
        ORDER BY b.booking_id DESC
    """)
    
    all_bookings = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('admin.html', bookings=all_bookings)

@app.route('/admin/add-vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if request.method == 'POST':
        name = request.form['name']
        v_type = request.form['type']
        trans = request.form['transmission']
        price = request.form['price']
        img = request.form['image_name'] # Just the filename, e.g., 'car3.jpg'

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Vehicles (name, type, transmission, price_per_day, image_name) VALUES (%s, %s, %s, %s, %s)",
            (name, v_type, trans, price, img)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("New vehicle added to the fleet!", "success")
        return redirect(url_for('admin_dashboard'))
        
    return render_template('add_vehicle.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Look for the user in the database
        cur.execute("SELECT user_id, password_hash, full_name FROM Users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()

        if user and user[1] == password:
            session['user_id'] = user[0] # This will now be 1, 2, or whatever the DB assigned
            
            # Check if this person is the Admin
            if email == "manishyadavsci@gmail.com":
                session['is_admin'] = True
                flash(f"Welcome back, Boss!", "success")
            else:
                session['is_admin'] = False
                flash(f"Logged in as {user[2]}", "success")
                
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        flash("Please login to view your bookings", "warning")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch user's bookings with vehicle and driver names
    cur.execute("""
        SELECT b.booking_id, COALESCE(v.name, 'N/A'), COALESCE(d.name, 'N/A'), 
               b.booking_type, b.total_price, b.status, b.booking_otp, b.start_time
        FROM Bookings b
        LEFT JOIN Vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN Drivers d ON b.driver_id = d.driver_id
        WHERE b.user_id = %s
        ORDER BY b.start_time DESC
    """, (session['user_id'],))
    
    user_bookings = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('bookings_user.html', bookings=user_bookings)

@app.route('/admin/update-status/<int:booking_id>/<status>')
def update_status(booking_id, status):
    # Security check: only admins allowed
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Valid statuses: 'Confirmed', 'Completed', 'Cancelled'
    cur.execute("UPDATE Bookings SET status = %s WHERE booking_id = %s", (status, booking_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"Booking #{booking_id} updated to {status}", "success")
    return redirect(url_for('admin_dashboard'))
@app.route('/driver/register', methods=['GET', 'POST'])
def driver_register():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. CHECK IF EMAIL ALREADY EXISTS
        cur.execute("SELECT email FROM Drivers WHERE email = %s", (email,))
        existing_driver = cur.fetchone()

        if existing_driver:
            cur.close()
            conn.close()
            flash("This email is already registered as a partner! Please use a different email.", "danger")
            return redirect(url_for('driver_register'))

        # 2. IF NOT EXISTS, PROCEED WITH INSERT
        try:
            name = request.form['name']
            pwd = request.form['password']
            license = request.form['license']
            exp = request.form['experience']
            skills = ", ".join(request.form.getlist('skills'))
            v_types = ", ".join(request.form.getlist('v_types'))

            cur.execute("""
                INSERT INTO Drivers (name, email, password_hash, license_no, experience_years, skills, vehicle_types, hourly_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, email, pwd, license, exp, skills, v_types, 150))
            
            conn.commit()
            flash("Application submitted successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash("An error occurred. Please try again.", "danger")
            print(f"Error: {e}")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('login'))
        
    return render_template('driver_register.html')

@app.route('/report/<int:booking_id>', methods=['GET', 'POST'])
def report_issue(booking_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        subject = request.form['subject']
        desc = request.form['description']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Complaints (user_id, booking_id, subject, description) VALUES (%s, %s, %s, %s)",
                    (session['user_id'], booking_id, subject, desc))
        conn.commit()
        cur.close()
        conn.close()
        flash("Complaint filed. Our team will contact you.", "info")
        return redirect(url_for('my_bookings'))
        
    return render_template('report.html', booking_id=booking_id)

if __name__ == '__main__':
    app.run(debug=True)
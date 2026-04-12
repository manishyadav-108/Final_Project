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
        email = request.form['email']
        phone = request.form['phone']
        # For simplicity in demo, we store plain text or simple hash
        pwd = request.form['password']
        
        # Offline OTP Simulation
        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['reg_data'] = {'email': email, 'phone': phone, 'pwd': pwd}
        
        print("\n" + "="*30)
        print(f"DEBUG OTP FOR EXAMINER: {otp}")
        print("="*30 + "\n")
        
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
            cur.execute("INSERT INTO Users (email, phone_number, password_hash, is_verified) VALUES (%s, %s, %s, %s)",
                        (data['email'], data['phone'], data['pwd'], True))
            conn.commit()
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
    # Capture data from the form
    service_type = request.form['service_type']
    user_id = 1 # Temporary for demo (in real app, use session['user_id'])
    duration = int(request.form['duration']) # Days for vehicle, Hours for driver
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    total_price = 0
    booking_otp = str(random.randint(1000, 9999)) # Short OTP for starting the ride
    
    if service_type == 'self':
        v_id = request.form['item_id']
        cur.execute("SELECT price_per_day FROM Vehicles WHERE vehicle_id = %s", (v_id,))
        price = cur.fetchone()[0]
        total_price = price * duration
        cur.execute("INSERT INTO Bookings (user_id, vehicle_id, booking_type, total_price, booking_otp, start_time, end_time) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
                    (user_id, v_id, 'Self_Drive', total_price, booking_otp))
        
    elif service_type == 'driver-only':
        d_id = request.form['item_id']
        cur.execute("SELECT hourly_rate FROM Drivers WHERE driver_id = %s", (d_id,))
        rate = cur.fetchone()[0]
        # Our formula: (Rate * Hours) + $5 Base Fee
        total_price = (rate * duration) + 5 
        cur.execute("INSERT INTO Bookings (user_id, driver_id, booking_type, total_price, booking_otp, start_time, end_time) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
                    (user_id, d_id, 'Driver_Only', total_price, booking_otp))

    conn.commit()
    cur.close()
    conn.close()
    
    return render_template('success.html', price=total_price, otp=booking_otp)




if __name__ == '__main__':
    app.run(debug=True)
import csv
import math
import random
from datetime import datetime

import barcode
import mysql.connector
import qrcode
from barcode.writer import ImageWriter
from flask_mail import Mail, Message
from flask import Flask, redirect, render_template, request, session, flash

app = Flask(__name__)
app.secret_key = 'secret123'

# =========================
# MAIL CONFIG
# =========================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# YOUR GMAIL

app.config['MAIL_USERNAME'] = 'shaikshmarika786@gmail.com'

# APP PASSWORD

app.config['MAIL_PASSWORD'] = 'fltb cnld htnt dfxa'

mail = Mail(app)

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="logistics"
)
cursor = db.cursor(dictionary=True)

# Load Pincode Data
pincode_data = {}
try:
    with open("pincodes.csv", "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                pincode = row['Pincode'].strip()
                pincode_data[pincode] = {
                    "district": row['District'],
                    "state": row['StateName'],
                    "region": row['RegionName'],
                    "division": row['DivisionName'],
                    "latitude": float(row['Latitude']),
                    "longitude": float(row['Longitude'])
                }
            except (ValueError, KeyError):
                pass
except FileNotFoundError:
    print("Warning: pincodes.csv not found.")

# CREATE DEFAULT HUBS
cursor.execute("""
CREATE TABLE IF NOT EXISTS hubs(
    id INT AUTO_INCREMENT PRIMARY KEY,
    hub_name VARCHAR(100),
    location VARCHAR(200)
)
""")
db.commit()

# =========================
# SEND LOGIN MAIL
# =========================

def send_login_mail(name, email, password, role):

    try:

        msg = Message(

            subject="Welcome To Logistics Management System",

            sender=app.config['MAIL_USERNAME'],

            recipients=[email]

        )

        msg.html = f"""

        <div
        style="
        font-family:Arial;
        padding:30px;
        ">

            <h2
            style="
            color:#2563eb;
            ">

                Welcome {name} 🎉

            </h2>

            <p>

                Your request has been approved successfully.

            </p>

            <h3>

                Login Details

            </h3>

            <table
            style="
            border-collapse:collapse;
            width:100%;
            ">

                <tr>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        Role

                    </td>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        {role}

                    </td>

                </tr>

                <tr>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        Email

                    </td>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        {email}

                    </td>

                </tr>

                <tr>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        Password

                    </td>

                    <td
                    style="
                    padding:12px;
                    border:1px solid #ddd;
                    ">

                        {password}

                    </td>

                </tr>

            </table>

            <br>

            <p>

                You can now login to the Logistics System Dashboard.

            </p>

            <h3
            style="
            color:#16a34a;
            ">

                Thank You 🚚

            </h3>

        </div>

        """

        mail.send(msg)

        return True

    except Exception as e:

        print("MAIL ERROR :", e)

        return False
    

def send_rejection_mail(name, email, role):

    try:

        msg = Message(

            subject="Request Rejected - Logistics Management",

            sender=app.config['MAIL_USERNAME'],

            recipients=[email]

        )

        msg.html = f"""

        <div
        style="
        font-family:Arial;
        padding:30px;
        ">

            <h2
            style="
            color:#dc2626;
            ">

                Hello {name}

            </h2>

            <p>

                We regret to inform you that your

                <b>{role}</b>

                request has been rejected by admin.

            </p>

            <p>

                Possible Reasons:

            </p>

            <ul>

                <li>
                    Duplicate Email
                </li>

                <li>
                    Invalid Details
                </li>

                <li>
                    Verification Failed
                </li>

            </ul>

            <p>

                Please contact admin for more details.

            </p>

            <br>

            <h3
            style="
            color:#2563eb;
            ">

                Logistics Management System 🚚

            </h3>

        </div>

        """

        mail.send(msg)

    except Exception as e:

        print("MAIL ERROR :", e)


# --- ROUTES ---

@app.route('/')
def home():
    return render_template("index.html", user=session.get('user'))


@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']

    # CHECK EMAIL EXISTS
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        return "exists"

    # USER ID
    user_id = "USR" + str(random.randint(1000, 9999))

    # INSERT USER
    cursor.execute("""
        INSERT INTO users(user_id, name, email, phone, password)
        VALUES(%s, %s, %s, %s, %s)
    """, (user_id, name, email, phone, password))
    
    db.commit()
    return "success"


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email'].strip()
    password = request.form['password'].strip()

    # CUSTOMER LOGIN
    cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
    user = cursor.fetchone()

    if user:
        session['user'] = user['name']
        session['user_email'] = user['email']
        session['user_id'] = user['user_id']
        return "success"

    # STAFF LOGIN
    cursor.execute("SELECT * FROM staff_users WHERE email=%s AND password=%s", (email, password))
    staff = cursor.fetchone()

    if staff:
        session['staff'] = staff['name'] if staff['name'] else staff['email']
        session['staff_role'] = staff['role']
        session['staff_id'] = staff['id']

        if staff['role'] == 'admin':
            return "admin"
        elif staff['role'] == 'vendor':
            session['vendor'] = staff['name']
            session['vendor_email'] = staff['email']
            return "vendor"
        elif staff['role'] == 'hub_staff':
            return "hub"
        elif staff['role'] == 'delivery_boy':
            return "delivery"

    return "fail"


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('staff', None)
    session.pop('staff_role', None)
    session.pop('staff_id', None)
    session.pop('vendor', None)
    session.pop('vendor_email', None)
    return redirect('/')


@app.route('/create', methods=['GET', 'POST'])
def create():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        data = request.form
        tracking_id = "TRK" + str(random.randint(100000, 999999))
        timestamp = datetime.now()

        sender_pin = data['sender_pincode'].strip()
        receiver_pin = data['receiver_pincode'].strip()

        sender_info = pincode_data.get(sender_pin, {"district": "Unknown", "state": "Unknown"})
        receiver_info = pincode_data.get(receiver_pin, {"district": "Unknown", "state": "Unknown"})

        dist = calculate_distance(sender_pin, receiver_pin)
        price = calculate_price(data['weight'], dist, data['transport'])

        # QR GENERATE
        qr = qrcode.make(tracking_id)
        qr_filename = "qr_" + tracking_id + ".png"
        qr.save("static/" + qr_filename)

        # BARCODE GENERATE
        barcode_class = barcode.get_barcode_class('code128')
        barcode_filename = "barcode_" + tracking_id
        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.18,
            "module_height": 10,
            "font_size": 9,
            "text_distance": 2,
            "quiet_zone": 1
        })
        barcode_obj = barcode_class(tracking_id, writer=writer)
        barcode_obj.save("static/" + barcode_filename)
        barcode_path = barcode_filename + ".png"

        # SAVE DATABASE
        cursor.execute("""
            INSERT INTO parcels (
                tracking_id, user_email, sender_name, receiver_name, sender_pincode, receiver_pincode,
                weight, transport, sender_district, sender_state, receiver_district, receiver_state,
                distance, price, status, created_at, current_hub
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            tracking_id, session['user_email'], data['sender_name'], data['receiver_name'],
            sender_pin, receiver_pin, data['weight'], data['transport'],
            sender_info['district'], sender_info['state'],
            receiver_info['district'], receiver_info['state'],
            dist, price, "Booked", timestamp, sender_info['district'] + " Hub"
        ))

        # INSERT FIRST TRACKING STATUS
        cursor.execute("""
            INSERT INTO tracking_history (tracking_id, location, status)
            VALUES (%s,%s,%s)
        """, (tracking_id, sender_info['district'], "Booked"))
        
        db.commit()

        return render_template(
            "receipt.html", tracking_id=tracking_id, data=data,
            sender_info=sender_info, receiver_info=receiver_info,
            distance=dist, price=price, timestamp=timestamp,
            qr_path=qr_filename, barcode_path=barcode_path,
        )

    return render_template("create.html")


@app.route('/update', methods=['POST'])
def update():
    tracking_id = request.form['tracking_id']
    status = request.form['status']
    location = request.form['location']

    cursor.execute("UPDATE parcels SET status=%s, current_hub=%s WHERE tracking_id=%s", (status, location, tracking_id))
    cursor.execute("INSERT INTO tracking_history (tracking_id, location, status) VALUES (%s,%s,%s)", (tracking_id, location, status))
    db.commit()

    return "Updated Successfully"


def calculate_price(weight, distance, transport):
    weight = float(weight)
    base = 50
    if transport == "Express (Air)":
        per_km = 6
    elif transport == "Heavy Cargo":
        per_km = 10
    else:
        per_km = 4
    per_kg = 12
    total = base + (weight * per_kg) + (distance * per_km)
    return round(total, 2)


def calculate_distance(pin1, pin2):
    if pin1 not in pincode_data or pin2 not in pincode_data:
        return 500

    lat1 = pincode_data[pin1]['latitude']
    lon1 = pincode_data[pin1]['longitude']
    lat2 = pincode_data[pin2]['latitude']
    lon2 = pincode_data[pin2]['longitude']

    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return round(R * c, 2)


@app.route('/track', methods=['GET', 'POST'])
def track():
    data = None
    history = []
    current_lat = 20.5937
    current_lon = 78.9629

    # Combine GET and POST tracking id retrieval
    tracking_id = request.args.get('tracking_id') if request.method == 'GET' else request.form.get('tracking_id')

    if tracking_id:
        # PARCEL DETAILS
        cursor.execute("SELECT * FROM parcels WHERE tracking_id=%s", (tracking_id,))
        data = cursor.fetchone()

        # HISTORY
        cursor.execute("SELECT location, status, timestamp FROM tracking_history WHERE tracking_id=%s ORDER BY timestamp ASC", (tracking_id,))
        history = cursor.fetchall()

        # MAP LOCATION
        if data:
            receiver_pin = data['receiver_pincode']
            if receiver_pin in pincode_data:
                current_lat = pincode_data[receiver_pin]['latitude']
                current_lon = pincode_data[receiver_pin]['longitude']

    all_status = ["Booked", "Picked Up", "In Transit", "Reached Hub", "Out For Delivery", "Delivered"]
    current_status = data['status'] if data else None

    return render_template(
        "track.html", data=data, history=history,
        all_status=all_status, current_status=current_status,
        current_lat=current_lat, current_lon=current_lon
    )


@app.route('/my-orders')
def my_orders():
    if 'user' not in session:
        return redirect('/')

    cursor.execute("SELECT * FROM parcels WHERE user_email=%s ORDER BY id DESC", (session['user_email'],))
    orders = cursor.fetchall()

    return render_template("my_orders.html", orders=orders)


@app.route('/cancel-order/<tracking_id>', methods=['POST'])
def cancel_order(tracking_id):
    if 'user' not in session:
        return redirect('/')

    reason = request.form['reason']
    cursor.execute("SELECT status FROM parcels WHERE tracking_id=%s", (tracking_id,))
    parcel = cursor.fetchone()

    if not parcel:
        return "Parcel Not Found"

    current_status = parcel['status']

    if current_status in ["Booked", "Pickup Requested"]:
        cursor.execute("UPDATE parcels SET status=%s WHERE tracking_id=%s", ("Cancelled", tracking_id))
        request_type = "Cancellation"
        tracking_status = "Cancelled"
    else:
        request_type = "Return Request"
        tracking_status = "Return Requested"
        cursor.execute("UPDATE parcels SET status=%s WHERE tracking_id=%s", ("Return Requested", tracking_id))

    cursor.execute("""
        INSERT INTO return_requests (tracking_id, customer_email, reason, request_type, status)
        VALUES (%s,%s,%s,%s,%s)
    """, (tracking_id, session['user_email'], reason, request_type, "Pending"))

    cursor.execute("""
        INSERT INTO tracking_history (tracking_id, location, status)
        VALUES (%s,%s,%s)
    """, (tracking_id, "Customer Request", tracking_status))

    db.commit()
    return redirect('/my-orders')


@app.route('/receipt/<tracking_id>')
def view_receipt(tracking_id):
    if 'user' not in session:
        return redirect('/')

    cursor.execute("SELECT * FROM parcels WHERE tracking_id=%s AND user_email=%s", (tracking_id, session['user_email']))
    data = cursor.fetchone()

    if not data:
        return "Receipt Not Found"

    sender_info = {"district": data['sender_district'], "state": data['sender_state']}
    receiver_info = {"district": data['receiver_district'], "state": data['receiver_state']}
    qr_filename = "qr_" + tracking_id + ".png"
    barcode_filename = "barcode_" + tracking_id + ".png"

    return render_template(
        "receipt.html", tracking_id=tracking_id, data=data,
        sender_info=sender_info, receiver_info=receiver_info,
        distance=data['distance'], price=data['price'],
        timestamp=data['created_at'], qr_path=qr_filename, barcode_path=barcode_filename
    )


@app.route('/updates', methods=['GET', 'POST'])
def update_shipment():
    success = False

    if request.method == 'POST':
        tracking_id = request.form['tracking_id']
        location = request.form['location']
        status = request.form['status']

        cursor.execute("UPDATE parcels SET status=%s WHERE tracking_id=%s", (status, tracking_id))
        cursor.execute("INSERT INTO tracking_history (tracking_id, location, status) VALUES (%s,%s,%s)", (tracking_id, location, status))
        
        db.commit()
        success = True

    return render_template("updates.html", success=success)


@app.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    error = None

    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        cursor.execute("SELECT * FROM staff_users WHERE email=%s AND password=%s", (email, password))
        staff = cursor.fetchone()

        if staff:
            session['staff'] = staff['email']
            return redirect('/updates')
        else:
            error = "Invalid credentials"

    return render_template('staff_login.html', error=error)


@app.route('/get-parcel/<tracking_id>')
def get_parcel(tracking_id):
    cursor.execute("SELECT * FROM parcels WHERE tracking_id=%s", (tracking_id,))
    parcel = cursor.fetchone()

    if parcel:
        return {
            "tracking_id": parcel['tracking_id'],
            "receiver": parcel['receiver_name'],
            "destination": parcel['receiver_district'],
            "weight": str(parcel['weight']) + " KG",
            "transport": parcel['transport'],
            "price": "₹" + str(parcel['price']),
            "status": parcel['status']
        }
    return {}


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'staff_role' not in session or session['staff_role'] != 'admin':
        return redirect('/')

    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        email = request.form['email']
        hub_id = request.form['hub_id']
        staff_id = "STF" + str(random.randint(1000, 9999))
        password = "staff123"

        cursor.execute("""
            INSERT INTO staff_users(staff_id, role, name, email, password, hub_id)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (staff_id, role, name, email, password, hub_id))
        db.commit()

    cursor.execute("SELECT COUNT(*) AS total FROM parcels")
    total = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS delivered FROM parcels WHERE status='Delivered'")
    delivered = cursor.fetchone()['delivered']

    cursor.execute("SELECT COUNT(*) AS transit FROM parcels WHERE status='In Transit'")
    transit = cursor.fetchone()['transit']

    cursor.execute("SELECT SUM(price) AS revenue FROM parcels")
    revenue = cursor.fetchone()['revenue'] or 0

    cursor.execute("SELECT * FROM parcels ORDER BY id DESC")
    parcels = cursor.fetchall()

    cursor.execute("SELECT * FROM staff_users ORDER BY id DESC")
    staffs = cursor.fetchall()

    cursor.execute("SELECT * FROM return_requests ORDER BY requested_at DESC")
    return_requests = cursor.fetchall()

    cursor.execute("SELECT * FROM vendor_requests ORDER BY id DESC")
    vendor_requests = cursor.fetchall()

    cursor.execute("SELECT * FROM hub_staff_requests ORDER BY id DESC")
    hub_requests = cursor.fetchall()

    cursor.execute("SELECT * FROM delivery_requests ORDER BY id DESC")
    delivery_requests = cursor.fetchall()

    cursor.execute("SELECT * FROM hubs")
    hubs = cursor.fetchall()

    return render_template(
        'admin.html', total=total, delivered=delivered, transit=transit, revenue=revenue,
        parcels=parcels, staffs=staffs, return_requests=return_requests,
        vendor_requests=vendor_requests, hubs=hubs, hub_requests=hub_requests,
        delivery_requests=delivery_requests
    )


@app.route('/reject-return/<int:id>')
def reject_return(id):
    cursor.execute("UPDATE return_requests SET status='Rejected' WHERE id=%s", (id,))
    db.commit()
    return redirect('/admin')


@app.route('/delete-staff/<int:id>')
def delete_staff(id):
    if 'staff_role' not in session or session['staff_role'] != 'admin':
        return redirect('/')

    cursor.execute("DELETE FROM staff_users WHERE id=%s", (id,))
    db.commit()
    return redirect('/admin')

@app.route('/book-parcel', methods=['POST'])
def book_parcel():

    if 'staff_role' not in session or session['staff_role'] != 'vendor':
        return redirect('/')

    data = request.form

    tracking_id = "TRK" + \
    str(random.randint(100000,999999))

    transport = data['transport']

    weight = float(data['weight'])

    distance = 50

    price = calculate_price(
        weight,
        distance,
        transport
    )

    current_hub = "Nellore Hub"

    cursor.execute("""

        INSERT INTO parcels(

            tracking_id,
            user_email,

            sender_name,
            receiver_name,

            sender_pincode,
            receiver_pincode,

            weight,
            transport,

            sender_district,
            sender_state,

            receiver_district,
            receiver_state,

            distance,
            price,

            status,

            current_hub,

            created_at

        )

        VALUES(

            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s

        )

    """, (

        tracking_id,

        session['vendor_email'],

        session['vendor'],

        data['customer_name'],

        "524001",
        "500001",

        weight,
        transport,

        "Nellore",
        "Andhra Pradesh",

        "Hyderabad",
        "Telangana",

        distance,
        price,

        "Booked",

        current_hub,

        datetime.now()

    ))

    # TRACKING HISTORY

    cursor.execute("""

        INSERT INTO tracking_history(

            tracking_id,
            location,
            status

        )

        VALUES(%s,%s,%s)

    """, (

        tracking_id,

        current_hub,

        "Booked"

    ))

    db.commit()

    flash(

        f"Parcel Created Successfully | Tracking ID : {tracking_id}",

        "success"

    )

    return redirect('/vendor-dashboard')



@app.route('/vendor-dashboard')
def vendor_dashboard():

    if 'staff_role' not in session or session['staff_role'] != 'vendor':
        return redirect('/')

    cursor.execute("""

        SELECT * FROM vendor_requests

        WHERE email=%s

    """, (

        session['vendor_email'],

    ))

    vendor = cursor.fetchone()

    cursor.execute("""

        SELECT * FROM parcels

        WHERE user_email=%s

        ORDER BY id DESC

    """, (

        session['vendor_email'],

    ))

    parcels = cursor.fetchall()

    cursor.execute("""

        SELECT * FROM return_requests

        WHERE customer_email=%s

        ORDER BY id DESC

    """, (

        session['vendor_email'],

    ))

    return_requests = cursor.fetchall()

    total_orders = len(parcels)

    delivered = len([
        p for p in parcels
        if p['status'] == 'Delivered'
    ])

    pending = len([
        p for p in parcels
        if p['status'] != 'Delivered'
    ])

    returns = len(return_requests)

    earnings = sum([
        float(p['price'])
        for p in parcels
    ]) if parcels else 0

    return render_template(

        'vendor_dashboard.html',

        vendor=vendor,
        parcels=parcels,

        total_orders=total_orders,
        delivered=delivered,
        pending=pending,
        returns=returns,
        earnings=earnings,

        return_requests=return_requests

    )


@app.route('/delivery-dashboard', methods=['GET', 'POST'])
def delivery_dashboard():

    if 'staff_role' not in session or session['staff_role'] != 'delivery_boy':
        return redirect('/')

    success = False

    if request.method == 'POST':

        tracking_id = request.form['tracking_id']
        location = request.form['location']
        status = request.form['status']

        # UPDATE PARCEL STATUS

        cursor.execute("""

        UPDATE parcels

        SET status=%s,
        current_hub=%s

        WHERE tracking_id=%s

        """, (

            status,
            location,
            tracking_id

        ))

        # TRACKING HISTORY

        cursor.execute("""

        INSERT INTO tracking_history(

            tracking_id,
            location,
            status

        )

        VALUES(%s,%s,%s)

        """, (

            tracking_id,
            location,
            status

        ))

        db.commit()

        success = True

    # ASSIGNED PARCELS

    cursor.execute("""

    SELECT *

    FROM parcels

    WHERE assigned_delivery_staff=%s
    OR assigned_delivery_staff=%s

    ORDER BY id DESC

    """, (

        session['staff'],
        session['staff'].strip()

    ))

    parcels = cursor.fetchall()

    total_orders = len(parcels)

    delivered = len([

        p for p in parcels

        if p['status'] == 'Delivered'

    ])

    pending = len([

        p for p in parcels

        if p['status'] != 'Delivered'

    ])

    earnings = delivered * 50

    return render_template(

        'delivery_dashboard.html',

        parcels=parcels,

        total_orders=total_orders,
        delivered=delivered,
        pending=pending,
        earnings=earnings,

        success=success

    )


@app.route('/delivery-status/<tracking_id>/<status>')
def delivery_status(tracking_id, status):
    cursor.execute("UPDATE parcels SET status=%s WHERE tracking_id=%s", (status, tracking_id))
    db.commit()
    return redirect('/delivery-dashboard')


@app.route('/delivery-request', methods=['POST'])
def delivery_request():
    if 'user' not in session:
        return redirect('/')

    full_name = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone']
    vehicle_type = request.form['vehicle_type']
    license_number = request.form['license_number']
    preferred_hub = request.form['preferred_hub']
    request_id = "DEL" + str(random.randint(1000, 9999))

    cursor.execute("""
        INSERT INTO delivery_requests (request_id, full_name, email, phone, vehicle_type, license_number, preferred_hub, status)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    """, (request_id, full_name, email, phone, vehicle_type, license_number, preferred_hub, "Pending"))
    
    db.commit()
    return redirect('/')


@app.route('/vendor-request', methods=['POST'])
def vendor_request():
    business_name = request.form['business_name']
    owner_name = request.form['owner_name']
    phone = request.form['phone']
    email = request.form['email']
    address = request.form['address']
    vendor_id = "VND" + str(random.randint(1000, 9999))

    cursor.execute("""
        INSERT INTO vendor_requests(vendor_id, business_name, owner_name, phone, email, address, status)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
    """, (vendor_id, business_name, owner_name, phone, email, address, 'Pending'))
    
    db.commit()
    return redirect('/')


@app.route('/hub-staff-request', methods=['POST'])
def hub_staff_request():
    if 'user' not in session:
        return redirect('/')

    full_name = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone']
    preferred_hub = request.form['preferred_hub']
    address = request.form['address']
    experience = request.form['experience']
    request_id = "HUB" + str(random.randint(1000, 9999))

    cursor.execute("""
        INSERT INTO hub_staff_requests(staff_request_id, full_name, phone, email, address, preferred_hub, experience, status)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    """, (request_id, full_name, phone, email, address, preferred_hub, experience, "Pending"))
    
    db.commit()
    return redirect('/')


@app.route('/approve-return/<int:id>')
def approve_return(id):
    cursor.execute("UPDATE return_requests SET status='Approved' WHERE id=%s", (id,))
    db.commit()
    return redirect('/admin')


@app.route('/approve-vendor/<int:id>')
def approve_vendor(id):

    

    cursor.execute("""

    SELECT * FROM vendor_requests

    WHERE id=%s

    """, (id,))

    vendor = cursor.fetchone()

    if not vendor:

        flash(
            "Vendor Request Not Found",
            "danger"
        )

        return redirect('/admin')

    # ALREADY EXISTS

    cursor.execute("""

    SELECT * FROM staff_users

    WHERE email=%s

    """, (

        vendor['email'],

    ))

    existing = cursor.fetchone()

    if existing:

        flash(
            "Vendor Already Approved",
            "warning"
        )

        return redirect('/admin')

    # PASSWORD

    password = "VENDOR" + \
    str(random.randint(1000,9999))

    # CHECK EMAIL EXISTS

    cursor.execute("""

    SELECT *

    FROM staff_users

    WHERE email=%s

    """, (

        vendor['email'],

    ))

    existing = cursor.fetchone()

    if existing:

        flash(

            "Email Already Registered",

            "danger"

        )

        return redirect('/admin')

    # INSERT LOGIN

    cursor.execute("""

    INSERT INTO staff_users(

        name,
        email,
        password,
        role

    )

    VALUES(%s,%s,%s,%s)

    """, (

        vendor['business_name'],
        vendor['email'],
        password,
        'vendor'

    ))

    # UPDATE STATUS

    cursor.execute("""

    UPDATE vendor_requests

    SET status='Approved'

    WHERE id=%s

    """, (id,))

    db.commit()

    # SEND MAIL

    send_login_mail(

    vendor['business_name'],
    vendor['email'],
    password,
    "Vendor"

)

    flash(

        f"Vendor Approved Successfully",

        "success"

    )

    return redirect('/admin')

@app.route('/hub_dashboard')
def hub_dashboard():
    if 'staff_role' not in session or session['staff_role'] != 'hub_staff':
        return redirect('/')

    cursor.execute("""
        SELECT parcels.*, staff_users.name AS delivery_name, staff_users.email AS delivery_email,
               delivery_requests.phone AS delivery_phone, delivery_requests.preferred_hub AS delivery_hub
        FROM parcels
        LEFT JOIN staff_users ON parcels.assigned_delivery_id = staff_users.id
        LEFT JOIN delivery_requests ON staff_users.email = delivery_requests.email
        ORDER BY parcels.id DESC
    """)
    parcels = cursor.fetchall()

    cursor.execute("""
        SELECT staff_users.*, delivery_requests.phone, delivery_requests.preferred_hub
        FROM staff_users
        LEFT JOIN delivery_requests ON staff_users.email = delivery_requests.email
        WHERE staff_users.role='delivery_boy'
    """)
    delivery_staff = cursor.fetchall()

    total_parcels = len(parcels)
    delivered = len([p for p in parcels if p['status'] == 'Delivered'])
    pending = len([p for p in parcels if p['status'] != 'Delivered'])
    returned = len([p for p in parcels if p['status'] == 'Returned'])
    assigned = len([p for p in parcels if p['assigned_delivery_staff']])

    return render_template(
        'hub_dashboard.html', parcels=parcels, delivery_staff=delivery_staff,
        total_parcels=total_parcels, delivered=delivered, pending=pending,
        returned=returned, assigned=assigned
    )


@app.route('/approve-hub/<int:id>')
def approve_hub(id):

    

    cursor.execute("""

    SELECT * FROM hub_staff_requests

    WHERE id=%s

    """, (id,))

    data = cursor.fetchone()

    if not data:

        flash(
            "Request Not Found",
            "danger"
        )

        return redirect('/admin')

    cursor.execute("""

    SELECT * FROM staff_users

    WHERE email=%s

    """, (

        data['email'],

    ))

    if cursor.fetchone():

        flash(
            "Hub Staff Already Approved",
            "warning"
        )

        return redirect('/admin')

    staff_id = "HUB" + \
    str(random.randint(1000,9999))

    password = "hub" + \
    str(random.randint(1000,9999))

    cursor.execute("""

    INSERT INTO staff_users(

        staff_id,
        role,
        name,
        email,
        password

    )

    VALUES(%s,%s,%s,%s,%s)

    """, (

        staff_id,
        "hub_staff",
        data['full_name'],
        data['email'],
        password

    ))

    cursor.execute("""

    UPDATE hub_staff_requests

    SET status='Approved'

    WHERE id=%s

    """, (id,))

    db.commit()

    send_login_mail(

    data['full_name'],
    data['email'],
    password,
    "Hub Staff"

)

    flash(

        f"Hub Staff Approved | Password: {password}",

        "success"

    )

    return redirect('/admin')

@app.route('/approve-delivery/<int:id>')
def approve_delivery(id):

    cursor.execute("""

    SELECT * FROM delivery_requests

    WHERE id=%s

    """, (id,))

    data = cursor.fetchone()

    if not data:

        flash(
            "Request Not Found",
            "danger"
        )

        return redirect('/admin')

    cursor.execute("""

    SELECT * FROM staff_users

    WHERE email=%s

    """, (

        data['email'],

    ))

    if cursor.fetchone():

        flash(
            "Delivery Boy Already Approved",
            "warning"
        )

        return redirect('/admin')

    staff_id = "DEL" + \
    str(random.randint(1000,9999))

    password = "DEL" + \
    str(random.randint(1000,9999))

    cursor.execute("""

    INSERT INTO staff_users(

        staff_id,
        role,
        name,
        email,
        password

    )

    VALUES(%s,%s,%s,%s,%s)

    """, (

        staff_id,
        "delivery_boy",
        data['full_name'],
        data['email'],
        password

    ))

    cursor.execute("""

    UPDATE delivery_requests

    SET status='Approved'

    WHERE id=%s

    """, (id,))

    db.commit()

    send_login_mail(

    data['full_name'],
    data['email'],
    password,
    "Delivery Boy"

)

    flash(

        f"Delivery Boy Approved | Password: {password}",

        "success"

    )

    return redirect('/admin')


@app.route('/assign_delivery/<int:id>', methods=['POST'])
def assign_delivery(id):

    delivery_staff = request.form['delivery_staff']

    # GET DELIVERY BOY DETAILS

    cursor.execute("""

    SELECT *

    FROM staff_users

    WHERE id=%s

    """, (

        delivery_staff,

    ))

    boy = cursor.fetchone()

    if not boy:

        flash(
            "Delivery Boy Not Found",
            "danger"
        )

        return redirect('/hub_dashboard')

    # UPDATE PARCEL

    cursor.execute("""

    UPDATE parcels

    SET

    assigned_delivery_staff=%s,
    assigned_delivery_id=%s,

    status='Assigned'

    WHERE id=%s

    """, (

        boy['name'],
        boy['id'],

        id

    ))

    db.commit()

    flash(

        "Delivery Boy Assigned Successfully",

        "success"

    )

    return redirect('/hub_dashboard')


@app.route('/scan-update', methods=['POST'])
def scan_update():
    tracking_id = request.form['tracking_id']
    hub = request.form['hub']
    status = request.form['status']

    cursor.execute("UPDATE parcels SET current_hub=%s, status=%s WHERE tracking_id=%s", (hub, status, tracking_id))
    cursor.execute("INSERT INTO tracking_history(tracking_id, location, status) VALUES(%s,%s,%s)", (tracking_id, hub, status))
    
    db.commit()
    return redirect('/hub_dashboard')


@app.route('/reject-vendor/<int:id>')
def reject_vendor(id):

    cursor.execute("""

    SELECT *

    FROM vendor_requests

    WHERE id=%s

    """, (

        id,

    ))

    vendor = cursor.fetchone()

    if vendor:

        # SEND REJECT MAIL

        send_rejection_mail(

            vendor['business_name'],
            vendor['email'],
            "Vendor"

        )

        # DELETE REQUEST

        cursor.execute("""

        DELETE FROM vendor_requests

        WHERE id=%s

        """, (

            id,

        ))

        db.commit()

        flash(

            "Vendor Request Rejected",

            "warning"

        )

    return redirect('/admin')


@app.route('/reject-hub/<int:id>')
def reject_hub(id):

    cursor.execute("""

    SELECT *

    FROM hub_staff_requests

    WHERE id=%s

    """, (

        id,

    ))

    staff = cursor.fetchone()

    if staff:

        send_rejection_mail(

            staff['full_name'],
            staff['email'],
            "Hub Staff"

        )

        cursor.execute("""

        DELETE FROM hub_staff_requests

        WHERE id=%s

        """, (

            id,

        ))

        db.commit()

        flash(

            "Hub Staff Request Rejected",

            "warning"

        )

    return redirect('/admin')


@app.route('/reject-delivery/<int:id>')
def reject_delivery(id):

    cursor.execute("""

    SELECT *

    FROM delivery_requests

    WHERE id=%s

    """, (

        id,

    ))

    delivery = cursor.fetchone()

    if delivery:

        send_rejection_mail(

            delivery['full_name'],
            delivery['email'],
            "Delivery Boy"

        )

        cursor.execute("""

        DELETE FROM delivery_requests

        WHERE id=%s

        """, (

            id,

        ))

        db.commit()

        flash(

            "Delivery Boy Request Rejected",

            "warning"

        )

    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
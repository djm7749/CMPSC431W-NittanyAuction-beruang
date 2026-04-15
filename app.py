from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib
from init_db import init_db

app = Flask(__name__)
app.secret_key = "abc123"

DB_NAME = 'auction.db'
init_db()

def db_connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
  
@app.route('/')
def index():
    return render_template('index.html')

# Add a new patient
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = db_connect()
        cur = conn.cursor()

        # Find user (general)
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cur.fetchone()

        if user is None:
            conn.close()
            return render_template('login.html')

        # Check hashed password
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if user['password_hash'] != hashed_input:
            conn.close()
            return render_template('login.html')

        # Role detection
        cur.execute("SELECT * FROM Bidders WHERE email = ?", (email,))
        is_bidder = cur.fetchone()

        cur.execute("SELECT * FROM Sellers WHERE email = ?", (email,))
        is_seller = cur.fetchone()

        cur.execute("SELECT * FROM Helpdesk WHERE email = ?", (email,))
        is_helpdesk = cur.fetchone()

        conn.close()

        if is_bidder:
            session['user_email'] = email
            session['role'] = 'Bidder'
            return redirect(url_for('bidder_dashboard'))

        elif is_seller:
            session['user_email'] = email
            session['role'] = 'Seller'
            return redirect(url_for('seller_dashboard'))

        elif is_helpdesk:
            session['user_email'] = email
            session['role'] = 'Helpdesk'
            return redirect(url_for('helpdesk_dashboard'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        name = request.form['name'].strip()

        conn = db_connect()
        cur = conn.cursor()

        # Check for existing user
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error='Email already registered')

        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        cur.execute("INSERT INTO Users (email, password_hash) VALUES (?, ?)", (email, hashed_input))

        # We assume LSU email = Bidder
        if email.endswith('@lsu.edu'):
            parts = name.split()
            first_name = parts[0] if len(parts) > 0 else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

            cur.execute("""INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (email, first_name, last_name, None, None, None))

            conn.commit()
            conn.close()

            return redirect(url_for('bidder_dashboard'))

        # We assume non-LSU email = Sellers
        else:
            cur.execute("""INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
                        VALUES (?, ?, ?, ?)""",
                        (email, None, None, 0.00))

            conn.commit()
            conn.close()

            return redirect(url_for('seller_dashboard'))

    return render_template('signup.html')

@app.route('/bidder_dashboard')
def bidder_dashboard():
        # items = [
        #     {"name": "Laptop", "price": 500, "image": "default-auction.jpg"},
        #     {"name": "Phone", "price": 300, "image": None},
        #     {"name": "Headphones", "price": 150, "image": None},
        #     {"name": "Camera", "price": 800, "image": None},
        #     {"name": "Tablet", "price": 400, "image": None},
        #     {"name": "Monitor", "price": 600, "image": None}
        # ]

    conn = db_connect()
    cur = conn.cursor()

    cursor.execute("""
        SELECT 
            a.Listing_ID,
            a.Product_Name AS name,
            (   
                SELECT MAX(Bid_Price)
                FROM Bidders b
                WHERE b.Listing_ID = a.Listing_ID
            ) AS price,
        FROM Auction_Listings a
        WHERE a.status = 1
        ORDER BY a.Listing_ID
        LIMIT 10
    """)

    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append({
            "name": row["name"],
            "price": row["price"],
            "image": "default-auction.jpg"
        })

    return render_template('bidder.html', items=items)

@app.route('/seller_dashboard')
def seller_dashboard():
    items = [
        {"name": "Laptop", "price": 500, "image": "default-auction.jpg"},
        {"name": "Phone", "price": 300, "image": None},
        {"name": "Headphones", "price": 150, "image": None},
        {"name": "Monitor", "price": 600, "image": None}
    ]
    return render_template('seller.html', items=items)

@app.route('/helpdesk_dashboard')
def helpdesk_dashboard():
    return render_template('helpdesk.html')


@app.route('/create_auction', methods=['GET', 'POST'])
def create_auction():
    if request.method == 'POST':
        # to be implemented: form handling to create a new auction
        pass
    return render_template('create-auction.html')

@app.route('/user_account')
def user_account():
    return render_template('user-account.html')

if __name__ == '__main__':
    app.run(debug=True)         # Set debug=True for development to allow auto-reloading 


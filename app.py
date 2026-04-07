from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import hashlib
import os
import pandas as pd
import csv

app = Flask(__name__)
app.secret_key = "abc123"

DB_NAME = "auction.db"
DATASETPATH = "NittanyAuctionDataset_v1/"


# ---------------- HASH PASSWORD ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- DB CONNECT ----------------
def db_connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- INIT DATABASE ----------------
def init_db():
    print("Initializing database...")

    if os.path.exists(DB_NAME):
        print("Database already exists. Skipping initialization.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Users
    cursor.execute("""
        CREATE TABLE Users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );
    """)

    # Bidders
    cursor.execute("""
        CREATE TABLE Bidders (
            email TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            home_address_id INTEGER,
            major TEXT,
            FOREIGN KEY (email) REFERENCES Users (email)
        );
    """)

    # Sellers
    cursor.execute("""
        CREATE TABLE Sellers (
            email TEXT PRIMARY KEY,
            bank_routing_number TEXT,
            bank_account_number TEXT,
            balance REAL,
            FOREIGN KEY (email) REFERENCES Users (email)
        );
    """)

    # Helpdesk
    cursor.execute("""
        CREATE TABLE Helpdesk (
            email TEXT PRIMARY KEY,
            position TEXT,
            FOREIGN KEY (email) REFERENCES Users (email)
        );
    """)

    print("Tables created.")

    # Load Users
    try:
        users_df = pd.read_csv(DATASETPATH + "Users.csv")

        for _, row in users_df.iterrows():
            cursor.execute("""
                INSERT INTO Users (email, password_hash)
                VALUES (?, ?)
            """, (row["email"], hash_password(row["password"])))

        print("Users loaded.")
    except Exception as e:
        print("Error loading Users:", e)

    # Load Bidders
    try:
        bidders_df = pd.read_csv(DATASETPATH + "Bidders.csv")

        for _, row in bidders_df.iterrows():
            cursor.execute("""
                INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (row["email"], row["first_name"], row["last_name"],
                  row["age"], row["home_address_id"], row["major"]))

        print("Bidders loaded.")
    except Exception as e:
        print("Error loading Bidders:", e)

    # Load Sellers
    try:
        sellers_df = pd.read_csv(DATASETPATH + "Sellers.csv")

        for _, row in sellers_df.iterrows():
            cursor.execute("""
                INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
                VALUES (?, ?, ?, ?)
            """, (row["email"], row["bank_routing_number"],
                  row["bank_account_number"], row["balance"]))

        print("Sellers loaded.")
    except Exception as e:
        print("Error loading Sellers:", e)

    # Load Helpdesk
    try:
        helpdesk_df = pd.read_csv(DATASETPATH + "Helpdesk.csv")

        for _, row in helpdesk_df.iterrows():
            cursor.execute("""
                INSERT INTO Helpdesk (email, position)
                VALUES (?, ?)
            """, (row["email"], row["position"]))

        print("Helpdesk loaded.")
    except Exception as e:
        print("Error loading Helpdesk:", e)

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# Initialize DB
init_db()


# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template('index.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Normalize input
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = db_connect()
        cur = conn.cursor()

        # Fetch correct user (email is PRIMARY KEY)
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cur.fetchone()

        # User not found
        if not user:
            conn.close()
            return render_template('login.html', error="Invalid email or password.")

        # Hash input password
        hashed_input = hash_password(password)

        # Wrong password
        if user['password_hash'] != hashed_input:
            conn.close()
            return render_template('login.html', error="Invalid email or password.")

        # Role detection
        cur.execute("SELECT 1 FROM Bidders WHERE email = ?", (email,))
        is_bidder = cur.fetchone()

        cur.execute("SELECT 1 FROM Sellers WHERE email = ?", (email,))
        is_seller = cur.fetchone()

        cur.execute("SELECT 1 FROM Helpdesk WHERE email = ?", (email,))
        is_helpdesk = cur.fetchone()

        conn.close()

        # Store session
        session['user_email'] = email

        # Redirect based on role
        if is_bidder:
            session['role'] = 'Bidder'
            return redirect(url_for('bidder_dashboard'))

        elif is_seller:
            session['role'] = 'Seller'
            return redirect(url_for('seller_dashboard'))

        elif is_helpdesk:
            session['role'] = 'Helpdesk'
            return redirect(url_for('helpdesk_dashboard'))

        # fallback
        return render_template('login.html', error="User role not found.")

    return render_template('login.html')


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        name = request.form['name'].strip()

        conn = db_connect()
        cur = conn.cursor()

        # Check existing user
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error="Email already registered")

        hashed_input = hash_password(password)

        # ---------------- DB INSERT ----------------
        cur.execute("""
            INSERT INTO Users (email, password_hash)
            VALUES (?, ?)
        """, (email, hashed_input))

        # ---------------- CSV INSERT (Users) ----------------
        with open(DATASETPATH + "Users.csv", "a", newline='') as file:
            writer = csv.writer(file)
            writer.writerow([email, password])  # store original password (dataset format)

        # ---------------- ROLE LOGIC ----------------
        if email.endswith('@lsu.edu'):
            parts = name.split()
            first_name = parts[0] if len(parts) > 0 else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

            # DB insert
            cur.execute("""
                INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email, first_name, last_name, None, None, None))

            # CSV insert
            with open(DATASETPATH + "Bidders.csv", "a", newline='') as file:
                writer = csv.writer(file)
                writer.writerow([email, first_name, last_name, "", "", ""])

            conn.commit()
            conn.close()

            return redirect(url_for('bidder_dashboard'))

        else:
            # DB insert
            cur.execute("""
                INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
                VALUES (?, ?, ?, ?)
            """, (email, "", "", 0.0))

            # CSV insert
            with open(DATASETPATH + "Sellers.csv", "a", newline='') as file:
                writer = csv.writer(file)
                writer.writerow([email, "", "", 0.0])

            conn.commit()
            conn.close()

            return redirect(url_for('seller_dashboard'))

    return render_template('signup.html')

# ---------------- DASHBOARDS ----------------
@app.route('/bidder_dashboard')
def bidder_dashboard():
    return render_template('bidder.html')


@app.route('/seller_dashboard')
def seller_dashboard():
    return render_template('seller.html')


@app.route('/helpdesk_dashboard')
def helpdesk_dashboard():
    return render_template('helpdesk.html')


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)

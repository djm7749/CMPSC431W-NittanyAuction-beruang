from flask import Flask, render_template, request, session
import sqlite3 as sql
import hashlib

app = Flask(__name__)

DB_NAME = 'auction.db'
init_db()

def db_connect():
    conn = sql.connect(DB_NAME)
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
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

        if user is None:
            conn.close()
            return render_template('login.html')

        # Check hashed password
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if user['password'] != hashed_input:
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
            return render_template('bidder.html')

        elif is_seller:
            session['user_email'] = email
            session['role'] = 'Seller'
            return render_template('seller.html')

        elif is_helpdesk:
            session['user_email'] = email
            session['role'] = 'Helpdesk'
            return render_template('helpdesk.html')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template('signup.html')

if __name__ == '__main__':
    app.run()


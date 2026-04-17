from flask import Flask, render_template, request, session, redirect, url_for, flash
import sqlite3
import hashlib

from pandas.core.config_init import parquet_engine_doc

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
            return render_template('login.html', error="Email not found")

        # Check hashed password
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if user['password_hash'] != hashed_input:
            conn.close()
            return render_template('login.html', error="Password incorrect")

        # Role detection
        cur.execute("SELECT * FROM Bidders WHERE email = ?", (email,))
        is_bidder = cur.fetchone()

        cur.execute("SELECT * FROM Sellers WHERE email = ?", (email,))
        is_seller = cur.fetchone()

        cur.execute("SELECT * FROM Helpdesk WHERE email = ?", (email,))
        is_helpdesk = cur.fetchone()

        conn.close()

        if is_helpdesk:
            session['user_email'] = email
            session['role'] = 'Helpdesk'
            return redirect(url_for('helpdesk_dashboard'))

        elif is_seller:
            session['user_email'] = email
            session['role'] = 'Seller'
            return redirect(url_for('seller_dashboard'))

        elif is_bidder:
            session['user_email'] = email
            session['role'] = 'Bidder'
            return redirect(url_for('bidder_dashboard'))

        else:
            return render_template('login.html', error="Role not found")

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

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            a.Listing_ID,
            a.Product_Name AS name,
            (   
                SELECT MAX(Bid_Price)
                FROM Bids b
                WHERE b.Listing_ID = a.Listing_ID
            ) AS price
        FROM Auction_Listings a
        WHERE a.status = 1
        ORDER BY a.Listing_ID
        LIMIT 8
    """)

    auction_rows = cur.fetchall()

    # cur.execute("""SELECT *
    #                FROM Categories""")
    # category_rows = cur.fetchall()
    conn.close()

    items = []
    for row in auction_rows:
        items.append({
            "name": row["name"],
            "price": row["price"] if row["price"] is not None else 0,
            "image": "default-auction.jpg"
        })

    # categories = load_categories(category_rows)

    return render_template('bidder.html', items=items)

@app.route('/seller_dashboard')
def seller_dashboard():
    # items = [
    #     {"name": "Laptop", "price": 500, "image": "default-auction.jpg"},
    #     {"name": "Phone", "price": 300, "image": None},
    #     {"name": "Headphones", "price": 150, "image": None},
    #     {"name": "Monitor", "price": 600, "image": None}
    # ]

    seller_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                SELECT Product_Name, Reserve_Price
                FROM Auction_Listings
                WHERE Seller_Email = ?
                """, (seller_email,))

    rows = cur.fetchall()

    items = []

    for row in rows:
        items.append({
            "name": row[0],  # Product_Name
            "price": row[1],  # Reserve_Price (or current bid if you have it)
            "image": "default-auction.jpg"  # keep frontend unchanged
        })

    conn.close()
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

    # Get User Session Email
    user_email = session['user_email']
    if not user_email:
        return redirect(url_for('login'))

    # Get detail y fetching data in DB
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                SELECT email, first_name, last_name
                FROM Bidders
                WHERE email = ?
                """, (user_email,))
    user_row = cur.fetchone()
    conn.close()
    return render_template('user-account.html', user_data = user_row)

@app.route('/browse')
def browse():

    page = request.args.get('page', 1, type=int)
    per_page = 24
    offset = (page - 1) * per_page

    q = request.args.get('q','').strip()

    conn = db_connect()
    cur = conn.cursor()

    params = []

    # Add Keyword Filter
    if q:
        keyword = f"%{q}%"
        base_query = """
        FROM Auction_Listings a
        LEFT JOIN Local_Vendors lv
            ON a.Seller_Email = lv.Email
        LEFT JOIN Bidders bd
            ON a.Seller_Email = bd.Email
        WHERE a.status = 1
            AND (
                a.Product_Name LIKE ?
                OR a.Product_Description LIKE ?
                OR a.Category LIKE ?
                OR lv.Business_Name LIKE ?
                OR bd.first_name LIKE ?
                OR bd.last_name LIKE ?
                OR (bd.first_name || ' ' || bd.last_name) LIKE ?
                )
        """
        params.extend([keyword, keyword, keyword, keyword, keyword, keyword, keyword])

    else:
        base_query = """
        FROM Auction_Listings a
        LEFT JOIN Local_Vendors lv
            ON a.Seller_Email = lv.Email
        LEFT JOIN Bidders bd
            ON a.Seller_Email = bd.Email
        WHERE a.status = 1
        """

    # Count
    cur.execute(f"""
                SELECT COUNT(*) AS total
                {base_query}
                """, params)
    total_items = cur.fetchone()["total"]

    cur.execute(f"""
        SELECT 
            a.Listing_ID,
            a.Product_Name AS name,
            a.Product_Description AS description,
            a.Category as category,
            a.Seller_Email AS email,
            CASE
                WHEN lv.Business_Name IS NOT NULL THEN lv.Business_Name
                WHEN bd.first_name IS NOT NULL AND bd.last_name IS NOT NULL
                    THEN bd.first_name || ' ' || bd.last_name
                WHEN bd.first_name IS NOT NULL
                    THEN bd.first_name
                ELSE a.Seller_Email
            END AS seller_name,
            (   
                SELECT MAX(Bid_Price)
                FROM Bids b
                WHERE b.Listing_ID = a.Listing_ID
            ) AS price
        {base_query}
        ORDER BY a.Listing_ID
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    auction_rows = cur.fetchall()

    cur.execute("""SELECT *
                   FROM Categories""")
    category_rows = cur.fetchall()
    conn.close()

    items = []
    for row in auction_rows:
        items.append({
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
            "seller": row["seller_name"],
            "price": row["price"] if row["price"] is not None else 0,
            "image": "default-auction.jpg"
        })

    categories = load_categories(category_rows)

    has_prev = page > 1
    has_next = offset + per_page < total_items

    return render_template('browse.html', items=items, categories=categories, page=page, has_prev=has_prev, has_next=has_next)


@app.route('/update_profile', methods=['POST'])
def update_profile():

    # Get User Session Email
    user_email = session['user_email']
    if not user_email:
        return redirect(url_for('login'))

    # Get User Input form
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    new_password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    password_updated = False
    try:
        conn = db_connect()
        cur = conn.cursor()

        # Update First Name and Last Name
        cur.execute("""
                    UPDATE Bidders
                    SET first_name = ?,
                        last_name  = ?
                    WHERE email = ?
                    """, [first_name, last_name, user_email])
        print("Updated Profile Name")
        # Update Password
        if new_password and new_password.strip() != "":
            if new_password != confirm_password:
                flash("Passwords do not match. Please try again.")
            else:
                # Hash New Password before Update in DB
                hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                cur.execute("""
                    UPDATE Users
                    SET password_hash = ?
                    WHERE email = ?
                """, [hashed_password, user_email])
                print("Updated Profile Password")
                password_updated = True
                flash('Password has been updated!', 'success')

        conn.commit()
    except Exception as e:
        print("Error When Updating Profile:",e )
        flash("An error occurred while updating your profile.")
    finally:
        conn.close()
    if password_updated:
        return redirect('/login')
    return redirect('/user_account')


# Helper Function : Make a hierarchical tree from category database
def load_categories(rows):
    nodes = {}
    tree = []

    for row in rows:
        name = row['category_name'].strip()
        parent = row['parent_category'].strip() if row['parent_category'] else None

        node = {
            'name': name,
            'parent': parent,
            'children': [],
        }

        nodes[name] = node

    for node in nodes.values():
        parent = node['parent']

        if parent == '' or parent is None:
            tree.append(node)
        elif parent in nodes:
            nodes[parent]['children'].append(node)
        else:
            tree.append(node)

    return tree


if __name__ == '__main__':
    app.run(debug=True)         # Set debug=True for development to allow auto-reloading 


from flask import Flask, render_template, request, session, redirect, url_for, flash
import sqlite3
import hashlib
import uuid
from datetime import datetime

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

# Add a new patient
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
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

        session['user_email'] = email
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
        street_num = request.form['street_num'].strip()
        street_name = request.form['street_name'].strip()
        city = request.form['city'].strip()
        state = request.form['state'].strip()
        zipcode = request.form['zipcode'].strip()
        age = request.form['age'].strip()
        major = request.form['major'].strip()

        is_seller = request.form.get('is_seller')

        conn = db_connect()
        cur = conn.cursor()

        # already exists?
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        if cur.fetchone():
            conn.close()
            return render_template(
                'signup.html',
                error="Email already registered"
            )

        # split name
        parts = name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        # Users
        cur.execute("""
            INSERT INTO Users (email, password_hash)
            VALUES (?, ?)
        """, (email, hashed_pw))

        #zipcode
        cur.execute("""
            INSERT OR IGNORE INTO Zipcode_Info (zipcode, city, state)
            VALUES (?, ?, ?)
        """, (zipcode, city, state))

        #generate address id
        address_id = uuid.uuid4().hex

        #insert address
        cur.execute("""
                    INSERT INTO Address
                        (address_ID, zipcode, street_num, street_name)
                    VALUES (?, ?, ?, ?)
                    """, (
                        address_id,
                        zipcode,
                        street_num,  # street_num optional for now
                        street_name
                    ))

        # Everyone = Bidder
        cur.execute("""
            INSERT INTO Bidders
            (email, first_name, last_name, age, home_address_id, major)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            email,
            first_name,
            last_name,
            age,
            address_id,
            major
        ))

        conn.commit()
        conn.close()

        session['user_email'] = email

        if is_seller:
            return redirect(url_for('seller_dashboard'))
        else:
            return redirect(url_for('bidder_dashboard'))

    return render_template('signup.html')


@app.route('/bidder_dashboard')
def bidder_dashboard():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    bidder_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            b.Bid_Price,

            a.Listing_ID,
            a.Product_Name,
            a.Reserve_Price,
            a.Status,
            a.Seller_Email

        FROM Bids b

        JOIN Auction_Listings a
            ON b.Listing_ID = a.Listing_ID
           AND b.Seller_Email = a.Seller_Email

        WHERE b.Bidder_email = ?

        ORDER BY b.Bid_ID DESC
    """, (bidder_email,))

    rows = cur.fetchall()

    items = []

    for row in rows:

        status_code = row["Status"]

        if status_code == 1:
            status_text = "Active"

        elif status_code == 2:
            status_text = "Sold"

        else:
            status_text = "Closed"

        items.append({

            "id": row["Listing_ID"],

            "name": row["Product_Name"],

            "my_bid": row["Bid_Price"],

            "price": row["Reserve_Price"],

            "status": status_text,

            "status_code": status_code,

            "seller_email": row["Seller_Email"],

            "image": "default-auction.jpg"

        })

    conn.close()

    return render_template(
        "bidder.html",
        items=items
    )

@app.route('/seller_dashboard')
def seller_dashboard():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    seller_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------------
    # SELLER AVERAGE RATING
    # -----------------------------------
    cur.execute("""
        SELECT
            ROUND(AVG(Rating), 2) AS avg_rating,
            COUNT(*) AS total_reviews
        FROM Rating
        WHERE Seller_Email = ?
    """, (seller_email,))

    rating_row = cur.fetchone()

    avg_rating = rating_row["avg_rating"] if rating_row["avg_rating"] else 0
    total_reviews = rating_row["total_reviews"]

    # -----------------------------------
    # SELLER LISTINGS
    # -----------------------------------
    cur.execute("""
        SELECT
            a.Listing_ID,
            a.Auction_Title,
            a.Product_Name,
            a.Reserve_Price,
            a.Status,

            (
                SELECT MAX(b.Bid_Price)
                FROM Bids b
                WHERE b.Listing_ID = a.Listing_ID
                  AND b.Seller_Email = a.Seller_Email
            ) AS highest_bid

        FROM Auction_Listings a

        WHERE a.Seller_Email = ?

        ORDER BY a.Listing_ID DESC
    """, (seller_email,))

    rows = cur.fetchall()

    items = []

    for row in rows:

        status_code = row["Status"]

        if status_code == 1:
            status_text = "Active"

        elif status_code == 2:
            status_text = "Sold"

        else:
            status_text = "Closed"

        current_price = (
            row["highest_bid"]
            if row["highest_bid"] is not None
            else row["Reserve_Price"]
        )

        items.append({
            "id": row["Listing_ID"],
            "name": row["Auction_Title"],
            "price": current_price,
            "status": status_text,
            "status_code": status_code,
            "image": "default-auction.jpg"
        })

    conn.close()

    return render_template(
        "seller.html",
        items=items,
        avg_rating=avg_rating,
        total_reviews=total_reviews
    )

@app.route('/helpdesk_dashboard')
def helpdesk_dashboard():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------
    # REQUESTS
    # -----------------------------
    if email == "helpdeskteam@lsu.edu":
        cur.execute("""
            SELECT *
            FROM Requests
            ORDER BY request_status ASC, request_id DESC
        """)

    else:
        cur.execute("""
            SELECT *
            FROM Requests
            WHERE helpdesk_staff_email = ?
                OR helpdesk_staff_email = ?
            ORDER BY request_status ASC, request_id DESC
        """, (email, "helpdeskteam@lsu.edu"))

    requests = cur.fetchall()

    # -----------------------------
    # VENDORS
    # -----------------------------
    cur.execute("""
        SELECT Email,
               Business_Name,
               Customer_Service_Phone_Number
        FROM Local_Vendors
        ORDER BY Business_Name
    """)

    vendors = cur.fetchall()

    conn.close()

    return render_template(
        "helpdesk.html",
        requests=requests,
        vendors=vendors
    )

@app.route('/create_auction', methods=['GET', 'POST'])
def create_auction():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Seller':
        return redirect(url_for('browse'))

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT category_name
        FROM Categories
        ORDER BY category_name
    """)
    categories = cur.fetchall()

    if request.method == 'POST':

        title = request.form['title'].strip()
        name = request.form['name'].strip()
        description = request.form['description'].strip()
        condition = request.form['condition'].strip()
        category = request.form['category'].strip()
        quantity = int(request.form['quantity'])

        reserve_price = float(request.form['reserve_price'])
        max_bids = int(request.form['max_bids'])

        seller_email = session['user_email']

        cur.execute("""
            SELECT MAX(Listing_ID)
            FROM Auction_Listings
            """)

        row = cur.fetchone()
        listing_id = 1 if row[0] is None else row[0] + 1

        cur.execute("""
            INSERT INTO Auction_Listings
            (Seller_Email, Listing_ID, Category,
             Auction_Title, Product_Name, Product_Description,
             Quantity, Reserve_Price, Max_bids, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            seller_email,
            listing_id,
            category,
            title,
            name,
            description + " | Condition: " + condition,
            quantity,
            reserve_price,
            max_bids,
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('seller_dashboard'))

    conn.close()

    return render_template(
        "create-auction.html",
        categories=categories
    )

@app.route('/user_account')
def user_account():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------------
    # MAIN USER + ADDRESS + ZIP INFO
    # -----------------------------------
    cur.execute("""
        SELECT
            u.email,

            b.first_name,
            b.last_name,
            b.age,
            b.major,
            b.home_address_id,

            a.street_num,
            a.street_name,
            a.zipcode,

            z.city,
            z.state,

            s.balance,
            s.bank_routing_number,
            s.bank_account_number

        FROM Users u

        LEFT JOIN Bidders b
            ON u.email = b.email

        LEFT JOIN Address a
            ON b.home_address_id = a.address_id

        LEFT JOIN Zipcode_Info z
            ON a.zipcode = z.zipcode

        LEFT JOIN Sellers s
            ON u.email = s.email

        WHERE u.email = ?
    """, (user_email,))

    user_row = cur.fetchone()

    # -----------------------------------
    # CREDIT CARDS
    # -----------------------------------
    cur.execute("""
        SELECT *
        FROM Credit_Cards
        WHERE Owner_email = ?
        ORDER BY credit_card_num
    """, (user_email,))

    credit_cards = cur.fetchall()

    conn.close()

    return render_template(
        "user-account.html",
        user_data=user_row,
        credit_cards=credit_cards
    )

@app.route('/browse')
def browse():

    page = request.args.get('page', 1, type=int)
    per_page = 24
    offset = (page - 1) * per_page

    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    conn = db_connect()
    cur = conn.cursor()

    params = []

    base_query = """
    FROM Auction_Listings a
    LEFT JOIN Local_Vendors lv
        ON a.Seller_Email = lv.Email
    LEFT JOIN Bidders bd
        ON a.Seller_Email = bd.Email
    WHERE a.Status = 1
    """

    # SEARCH
    if q:
        keyword = f"%{q}%"

        base_query += """
        AND (
            a.Auction_Title LIKE ?
            OR a.Product_Name LIKE ?
            OR a.Product_Description LIKE ?
            OR a.Category LIKE ?
            OR lv.Business_Name LIKE ?
            OR bd.first_name LIKE ?
            OR bd.last_name LIKE ?
            OR (bd.first_name || ' ' || bd.last_name) LIKE ?
        )
        """

        params.extend([
            keyword, keyword, keyword, keyword,
            keyword, keyword, keyword, keyword
        ])

    # CATEGORY FILTER
    if category:
        base_query += " AND a.Category = ? "
        params.append(category)

    # TOTAL COUNT
    cur.execute(f"""
        SELECT COUNT(*) AS total
        {base_query}
    """, params)

    total_items = cur.fetchone()["total"]

    # MAIN QUERY
    cur.execute(f"""
        SELECT
            a.Listing_ID,
            a.Auction_Title AS title,
            a.Product_Name AS name,
            a.Product_Description AS description,
            a.Category AS category,
            a.Reserve_Price,

            CASE
                WHEN lv.Business_Name IS NOT NULL THEN lv.Business_Name
                WHEN bd.first_name IS NOT NULL
                     AND bd.last_name IS NOT NULL
                    THEN bd.first_name || ' ' || bd.last_name
                WHEN bd.first_name IS NOT NULL
                    THEN bd.first_name
                ELSE a.Seller_Email
            END AS seller_name,

            (
                SELECT MAX(b.Bid_Price)
                FROM Bids b
                WHERE b.Listing_ID = a.Listing_ID
                  AND b.Seller_Email = a.Seller_Email
            ) AS highest_bid

        {base_query}

        ORDER BY a.Listing_ID DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    rows = cur.fetchall()

    # LOAD CATEGORIES
    cur.execute("SELECT * FROM Categories")
    category_rows = cur.fetchall()

    conn.close()

    items = []

    for row in rows:

        current_price = (
            row["highest_bid"]
            if row["highest_bid"] is not None
            else row["Reserve_Price"]
        )

        items.append({
            "id": row["Listing_ID"],
            "title": row["title"],
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
            "seller": row["seller_name"],
            "price": str(current_price).replace("$", "").strip(),
            "image": "default-auction.jpg"
        })

    categories = load_categories(category_rows)

    has_prev = page > 1
    has_next = offset + per_page < total_items

    return render_template(
        "browse.html",
        items=items,
        categories=categories,
        page=page,
        has_prev=has_prev,
        has_next=has_next
    )

@app.route('/approve_request/<int:request_id>')
def approve_request(request_id):

    if 'user_email' not in session:
        return redirect(url_for('login'))

    helpdesk_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # get request
    cur.execute("""
        SELECT *
        FROM Requests
        WHERE request_id = ?
    """, (request_id,))

    req = cur.fetchone()

    if not req:
        conn.close()
        return redirect(url_for('helpdesk_dashboard'))

    sender_email = req["sender_email"]
    request_type = req["request_type"]

    # Seller Application approval
    if request_type == "SellerApplication":

        # already seller?
        cur.execute("""
            SELECT *
            FROM Sellers
            WHERE Email = ?
        """, (sender_email,))

        if not cur.fetchone():

            cur.execute("""
                INSERT INTO Sellers
                (Email, bank_routing_number, bank_account_number, balance)
                VALUES (?, ?, ?, ?)
            """, (
                sender_email,
                None,
                None,
                0
            ))

    # mark request completed
    cur.execute("""
        UPDATE Requests
        SET request_status = 1,
            helpdesk_staff_email = ?
        WHERE request_id = ?
    """, (
        helpdesk_email,
        request_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('helpdesk_dashboard'))


@app.route('/my_requests')
def my_requests():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM Requests
        WHERE sender_email = ?
        ORDER BY request_id DESC
    """, (email,))

    requests = cur.fetchall()

    conn.close()

    return render_template(
        "my_requests.html",
        requests=requests
    )

@app.route('/apply_seller', methods=['GET', 'POST'])
def apply_seller():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    if request.method == 'POST':

        desc = request.form['description']

        cur.execute("""
            SELECT MAX(request_id)
            FROM Requests
        """)

        row = cur.fetchone()
        request_id = 1 if row[0] is None else row[0] + 1

        cur.execute("""
            INSERT INTO Requests
            (
                request_id,
                sender_email,
                helpdesk_staff_email,
                request_type,
                request_desc,
                request_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            email,
            "helpdeskteam@lsu.edu",
            "SellerApplication",
            desc,
            0
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('bidder_dashboard'))

    conn.close()

    return render_template("apply_seller.html")

@app.route('/update_profile', methods=['POST'])
def update_profile():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    # ----------------------------
    # FORM DATA
    # ----------------------------
    first_name = request.form['firstName'].strip()
    last_name = request.form['lastName'].strip()
    age = request.form['age'].strip()
    major = request.form['major'].strip()

    street_num = request.form['street_num'].strip()
    street_name = request.form['street_name'].strip()
    city = request.form['city'].strip()
    state = request.form['state'].strip()
    zipcode = request.form['zipcode'].strip()

    password = request.form['password'].strip()
    confirm_password = request.form['confirm_password'].strip()

    routing = request.form.get('routing', '').strip()
    account = request.form.get('account', '').strip()

    # credit card
    new_card_number = request.form.get('new_card_number', '').strip()
    new_card_type = request.form.get('new_card_type', '').strip()
    new_exp_month = request.form.get('new_exp_month', '').strip()
    new_exp_year = request.form.get('new_exp_year', '').strip()
    new_cvv = request.form.get('new_cvv', '').strip()

    conn = db_connect()
    cur = conn.cursor()

    # ==================================================
    # ADDRESS / ZIPCODE
    # ==================================================
    address_id = None

    if street_num and street_name and zipcode:

        # make sure zipcode exists
        cur.execute("""
            SELECT *
            FROM Zipcode_Info
            WHERE zipcode = ?
        """, (zipcode,))

        zip_exists = cur.fetchone()

        if not zip_exists and city and state:
            cur.execute("""
                INSERT INTO Zipcode_Info
                (zipcode, city, state)
                VALUES (?, ?, ?)
            """, (zipcode, city, state))

        # existing address?
        cur.execute("""
            SELECT address_id
            FROM Address
            WHERE street_num = ?
              AND street_name = ?
              AND zipcode = ?
        """, (
            street_num,
            street_name,
            zipcode
        ))

        row = cur.fetchone()

        if row:
            address_id = row["address_id"]

        else:
            cur.execute("""
                SELECT MAX(address_id)
                FROM Address
            """)
            row = cur.fetchone()

            next_id = 1 if row[0] is None else row[0] + 1

            cur.execute("""
                INSERT INTO Address
                (address_id, street_num, street_name, zipcode)
                VALUES (?, ?, ?, ?)
            """, (
                next_id,
                street_num,
                street_name,
                zipcode
            ))

            address_id = next_id

    # ==================================================
    # UPDATE BIDDER
    # ==================================================
    cur.execute("""
        UPDATE Bidders
        SET first_name = ?,
            last_name = ?,
            age = ?,
            major = ?,
            home_address_id = ?
        WHERE Email = ?
    """, (
        first_name,
        last_name,
        age if age else None,
        major if major else None,
        address_id,
        email
    ))

    # ==================================================
    # UPDATE SELLER BANK INFO
    # ==================================================
    cur.execute("""
        SELECT *
        FROM Sellers
        WHERE Email = ?
    """, (email,))

    if cur.fetchone():

        cur.execute("""
            UPDATE Sellers
            SET bank_routing_number = ?,
                bank_account_number = ?
            WHERE Email = ?
        """, (
            routing if routing else None,
            account if account else None,
            email
        ))

    # ==================================================
    # ADD CREDIT CARD
    # ==================================================
    if new_card_number and new_card_type:

        cur.execute("""
            SELECT *
            FROM Credit_Cards
            WHERE credit_card_num = ?
        """, (new_card_number,))

        if not cur.fetchone():

            cur.execute("""
                INSERT INTO Credit_Cards
                (
                    credit_card_num,
                    card_type,
                    expire_month,
                    expire_year,
                    security_code,
                    Owner_email
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                new_card_number,
                new_card_type,
                new_exp_month,
                new_exp_year,
                new_cvv,
                email
            ))

    # ==================================================
    # PASSWORD
    # ==================================================
    if password and password == confirm_password:

        hashed_password = hashlib.sha256(
            password.encode()
        ).hexdigest()

        cur.execute("""
            UPDATE Users
            SET password_hash = ?
            WHERE Email = ?
        """, (
            hashed_password,
            email
        ))

    conn.commit()
    conn.close()

    return redirect(url_for('user_account'))

@app.route('/new_request', methods=['GET', 'POST'])
def new_request():

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # load helpdesk emails
    cur.execute("""
        SELECT email
        FROM Helpdesk
        ORDER BY email
    """)

    helpdesks = cur.fetchall()

    if request.method == 'POST':

        request_type = request.form['request_type'].strip()
        description = request.form['description'].strip()
        assigned_email = request.form['helpdesk_email'].strip()

        cur.execute("SELECT MAX(request_id) FROM Requests")
        row = cur.fetchone()

        request_id = 1 if row[0] is None else row[0] + 1

        cur.execute("""
            INSERT INTO Requests
            (
                request_id,
                sender_email,
                helpdesk_staff_email,
                request_type,
                request_desc,
                request_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            email,
            assigned_email,
            request_type,
            description,
            0
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('my_requests'))

    conn.close()

    return render_template(
        "new_request.html",
        helpdesks=helpdesks
    )

@app.route('/rate_seller/<seller_email>/<int:listing_id>', methods=['GET', 'POST'])
def rate_seller(seller_email, listing_id):

    if 'user_email' not in session:
        return redirect(url_for('login'))

    bidder_email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    # -------------------------------------------------
    # VERIFY THIS USER WON THE AUCTION
    # Must be sold listing + this bidder has highest bid
    # -------------------------------------------------
    cur.execute("""
        SELECT
            MAX(b.Bid_Price) AS winning_bid
        FROM Bids b
        JOIN Auction_Listings a
            ON b.Listing_ID = a.Listing_ID
           AND b.Seller_Email = a.Seller_Email
        WHERE a.Listing_ID = ?
          AND a.Seller_Email = ?
          AND a.Status = 2
    """, (
        listing_id,
        seller_email
    ))

    row = cur.fetchone()

    if not row or row["winning_bid"] is None:
        conn.close()
        return redirect(url_for('bidder_dashboard'))

    winning_bid = row["winning_bid"]

    # Did current bidder place that winning bid?
    cur.execute("""
        SELECT *
        FROM Bids
        WHERE Listing_ID = ?
          AND Seller_Email = ?
          AND Bidder_Email = ?
          AND Bid_Price = ?
    """, (
        listing_id,
        seller_email,
        bidder_email,
        winning_bid
    ))

    winner = cur.fetchone()

    if not winner:
        conn.close()
        return redirect(url_for('bidder_dashboard'))

    # TODAY DATE
    today = datetime.now().strftime("%#m/%#d/%y")

    # -------------------------------------------------
    # SUBMIT RATING
    # -------------------------------------------------
    if request.method == 'POST':

        stars = request.form['rating']
        desc = request.form['description'].strip()

        # only once per date
        cur.execute("""
            SELECT *
            FROM Rating
            WHERE Bidder_Email = ?
              AND Seller_Email = ?
              AND Date = ?
        """, (
            bidder_email,
            seller_email,
            today
        ))

        already = cur.fetchone()

        if not already:

            cur.execute("""
                INSERT INTO Rating
                (
                    Bidder_Email,
                    Seller_Email,
                    Date,
                    Rating,
                    Rating_Desc
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                bidder_email,
                seller_email,
                today,
                stars,
                desc
            ))

            conn.commit()

        conn.close()

        return redirect(url_for('bidder_dashboard'))

    conn.close()

    return render_template(
        "rate_seller.html",
        seller_email=seller_email
    )

@app.route('/listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # GET LISTING
    cur.execute("""
        SELECT *
        FROM Auction_Listings
        WHERE Listing_ID = ?
    """, (listing_id,))

    listing = cur.fetchone()

    if not listing:
        conn.close()
        return "Listing not found"

    # GET BIDS
    cur.execute("""
        SELECT *
        FROM Bids
        WHERE Listing_ID = ?
        ORDER BY Bid_Price DESC
    """, (listing_id,))

    bids = cur.fetchall()

    highest_bid = bids[0]["Bid_Price"] if bids else None
    reserve_price = float(
        str(listing["Reserve_Price"])
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    current_price = highest_bid if highest_bid is not None else reserve_price

    max_bids = int(listing["Max_bids"])
    bid_count = len(bids)
    bids_left = max_bids - bid_count

    error = None

    # PLACE BID
    if request.method == 'POST':

        bidder = session['user_email']
        new_bid = float(request.form['bid_price'])
        seller_email = listing["Seller_Email"]
        # seller cannot bid own listing
        if bidder == seller_email:
            conn.close()
            return render_template(
                "listing.html",
                listing=listing,
                error="You cannot bid on your own auction."
            )

        if listing["Status"] != 1:
            error = "Auction is not active."

        elif bid_count >= max_bids:
            error = "Maximum number of bids reached."

        elif bids and bids[0]["Bidder_email"] == bidder:
            error = "You cannot bid twice in a row."

        elif new_bid <= reserve_price:
            error = "Bid must be higher than reserve price."

        elif highest_bid is not None and new_bid <= highest_bid:
            error = "Bid must be higher than current highest bid."

        else:
            cur.execute("SELECT MAX(Bid_ID) FROM Bids")
            row = cur.fetchone()

            bid_id = 1 if row[0] is None else row[0] + 1

            cur.execute("""
                INSERT INTO Bids
                (Bid_ID, Seller_Email, Listing_ID, Bidder_email, Bid_Price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                bid_id,
                listing["Seller_Email"],
                listing_id,
                bidder,
                new_bid
            ))

            conn.commit()

            # AUTO CLOSE IF MAX BIDS HIT
            if bid_count + 1 >= max_bids:
                cur.execute("""
                    UPDATE Auction_Listings
                    SET Status = 2
                    WHERE Listing_ID = ?
                """, (listing_id,))
                conn.commit()

            conn.close()

            return redirect(
                url_for(
                    'view_listing',
                    listing_id=listing_id
                )
            )

    conn.close()

    return render_template(
        "listing.html",
        listing=listing,
        bids=bids,
        highest_bid=current_price,
        bid_count=bid_count,
        max_bids=max_bids,
        bids_left=bids_left,
        error=error
    )

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():

    # -----------------------------------
    # ONLY HELPDESK
    # -----------------------------------
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Helpdesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------------
    # LOAD EXISTING CATEGORIES
    # -----------------------------------
    cur.execute("""
        SELECT *
        FROM Categories
        ORDER BY category_name
    """)

    categories = cur.fetchall()

    # -----------------------------------
    # SUBMIT NEW CATEGORY
    # -----------------------------------
    if request.method == 'POST':

        new_name = request.form['category_name'].strip()
        parent = request.form['parent_category'].strip()

        if new_name:

            # avoid duplicates
            cur.execute("""
                SELECT *
                FROM Categories
                WHERE category_name = ?
            """, (new_name,))

            exists = cur.fetchone()

            if not exists:

                cur.execute("""
                    INSERT INTO Categories
                    (
                        category_name,
                        parent_category
                    )
                    VALUES (?, ?)
                """, (
                    new_name,
                    parent if parent else None
                ))

                conn.commit()

        conn.close()

        return redirect(url_for('helpdesk_dashboard'))

    conn.close()

    return render_template(
        "add_category.html",
        categories=categories
    )

@app.route('/remove_vendor/<vendor_email>')
def remove_vendor(vendor_email):

    # -----------------------------------
    # ONLY HELPDESK CAN USE THIS
    # -----------------------------------
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'HelpDesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------------
    # VERIFY THIS IS A LOCAL VENDOR
    # -----------------------------------
    cur.execute("""
        SELECT *
        FROM Local_Vendors
        WHERE Email = ?
    """, (vendor_email,))

    vendor = cur.fetchone()

    if not vendor:
        conn.close()
        return redirect(url_for('helpdesk_dashboard'))

    # -----------------------------------
    # REMOVE ALL THEIR PRODUCTS
    # -----------------------------------
    cur.execute("""
        DELETE FROM Auction_Listings
        WHERE Seller_Email = ?
    """, (vendor_email,))

    # optional cleanup bids tied to listings
    cur.execute("""
        DELETE FROM Bids
        WHERE Seller_Email = ?
    """, (vendor_email,))

    # -----------------------------------
    # REMOVE LOCAL VENDOR RECORD
    # -----------------------------------
    cur.execute("""
        DELETE FROM Local_Vendors
        WHERE Email = ?
    """, (vendor_email,))

    conn.commit()
    conn.close()

    return redirect(url_for('helpdesk_dashboard'))

@app.route('/delete_card/<card_num>')
def delete_card(card_num):

    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']

    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM Credit_Cards
        WHERE credit_card_num = ?
          AND Owner_email = ?
    """, (
        card_num,
        email
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('user_account'))

@app.route('/change_user_id/<int:request_id>', methods=['GET', 'POST'])
def change_user_id(request_id):

    # -----------------------------------
    # ONLY HELPDESK
    # -----------------------------------
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Helpdesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # -----------------------------------
    # LOAD REQUEST
    # -----------------------------------
    cur.execute("""
        SELECT *
        FROM Requests
        WHERE request_id = ?
    """, (request_id,))

    req = cur.fetchone()

    if not req:
        conn.close()
        return redirect(url_for('helpdesk_dashboard'))

    # -----------------------------------
    # SUBMIT CHANGE
    # -----------------------------------
    if request.method == 'POST':

        old_email = request.form['old_email'].strip().lower()
        new_email = request.form['new_email'].strip().lower()

        # duplicate check
        cur.execute("""
            SELECT *
            FROM Users
            WHERE email = ?
        """, (new_email,))

        if cur.fetchone():
            conn.close()
            return render_template(
                "change_id.html",
                req=req,
                error="New ID already exists."
            )

        # -----------------------------------
        # UPDATE ALL TABLES
        # -----------------------------------
        tables = [

            ("Users", "email"),
            ("Bidders", "email"),
            ("Sellers", "email"),
            ("Helpdesk", "email"),
            ("Local_Vendors", "Email"),

            ("Auction_Listings", "Seller_Email"),

            ("Credit_Cards", "Owner_email"),

            ("Requests", "sender_email"),
            ("Requests", "helpdesk_staff_email"),

            ("Rating", "Bidder_Email"),
            ("Rating", "Seller_Email"),

            ("Bids", "Bidder_Email"),
            ("Bids", "Seller_Email")

        ]

        for table, column in tables:

            cur.execute(f"""
                UPDATE {table}
                SET {column} = ?
                WHERE {column} = ?
            """, (
                new_email,
                old_email
            ))

        # mark request completed
        cur.execute("""
            UPDATE Requests
            SET request_status = 1
            WHERE request_id = ?
        """, (request_id,))

        conn.commit()
        conn.close()

        return redirect(url_for('helpdesk_dashboard'))

    conn.close()

    return render_template(
        "change_id.html",
        req=req
    )

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


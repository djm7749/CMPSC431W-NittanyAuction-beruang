from flask import Flask, render_template, request, session, redirect, url_for, flash
import hashlib
from db import *
from init_db import init_db

app = Flask(__name__)
app.secret_key = "abc123"

DB_NAME = 'auction.db'
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = get_user(email)

        if user is None:
            return render_template('login.html', error="Email not found")

        # Check hashed password
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if user['password_hash'] != hashed_input:
            return render_template('login.html', error="Password incorrect")

        roles = get_user_roles(email)
        session['user_email'] = email
        session['roles'] = roles
        session['active_role'] = roles[0]

        if session['active_role'] == "Helpdesk":
            session['user_email'] = email
            session['roles'] = 'Helpdesk'
            return redirect(url_for('helpdesk_dashboard'))

        elif session['active_role'] == "Seller":
            session['user_email'] = email
            session['roles'] = 'Seller'
            return redirect(url_for('seller_dashboard'))

        elif session['active_role'] == "Bidder":
            session['user_email'] = email
            session['roles'] = 'Bidder'
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

from db import get_bidder_auctions

@app.route('/bidder_dashboard')
def bidder_dashboard():

    active_role = session.get('active_role')
    bidder = session['user_email']
    auction_rows = get_bidder_auctions(bidder)

    items = []

    for auction in auction_rows:
        # status_map = {
        #     1: "Active",
        #     0: "Inactive",
        #     2: "Sold"
        # }

        print(auction.keys())

        highest_bidder = auction["Bidder_Email"] if auction["Bidder_Email"] else "No bids yet"

        if highest_bidder == bidder:
            highest_bidder = "You"

        items.append({
            "name": auction["name"],
            "price": auction["Bid_Price"] if auction["Bid_Price"] else 0,
            "highest_bidder": highest_bidder,
            # "status": status_map.get(auction["status"], "Unknown"),
            "image": "default-auction.jpg"
        })

    return render_template('bidder.html', items=items, active_role=active_role)

@app.route('/seller_dashboard')
def seller_dashboard():

    seller_email = session['user_email']
    active_role = session.get('active_role')
    status_filter = request.args.get('filter', 'all')
    seller_rows = get_auction_listing(seller_email, status_filter)

    items = []

    for row in seller_rows:
        items.append({
            "listing_id": row[0], # Listing ID
            "name": row[1],  # Product_Name
            "price": row[2],  # Reserve_Price (or current bid if you have it)
            "status" : row[3],
            "image": "default-auction.jpg"  # keep frontend unchanged
        })

    return render_template('seller.html', items=items, active_role=active_role, status_filter=status_filter)

@app.route('/helpdesk_dashboard')
def helpdesk_dashboard():
    return render_template('helpdesk.html')


@app.route('/seller_dashboard/create_auction', methods=['GET', 'POST'])
def create_auction():
    active_role = session.get('active_role')
    seller_email = session.get('user_email')

    # Load category hierarchy
    category_options = build_category_dropdown(None)

    if request.method == 'POST':
        auction_title = request.form.get('auction_title', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        reserve_price = f"${request.form.get('reserve_price', '').strip()}"
        max_bids = request.form.get('max_bids', '').strip()
        quantity = request.form.get('quantity', '').strip()

        create_auction_listing(seller_email, auction_title, name, description, category, reserve_price, max_bids,quantity)
        return redirect(url_for('seller_dashboard'))

    return render_template('create-auction.html',active_role=active_role,categories=category_options)

@app.route('/seller_dashboard/listing/<int:listing_id>')
def seller_listing_detail(listing_id):
    seller_email = session.get('user_email')
    active_role = session.get('active_role')

    # retrieve auction listing by id
    listing = get_auction_listing_by_id(seller_email,listing_id)
    # build categories for dropdown
    category_options = build_category_dropdown(None)
    # Initialize removal info
    removal_info = None

    if not listing:
        return "Listing not found.", 404

    # Convert reserve_price (str) into (float) to be displayed in
    reserve_price_value = listing["Reserve_Price"].replace('$','')
    reserve_price_value = float(reserve_price_value)

    # count bids already placed on that auction listing
    bid_count = get_bid_count(seller_email,listing_id)

    edit_blocked = False
    edit_message = None

    # status meanings:  0 = inactive, 1 = active, 2 = sold

    if listing["Status"] == 2:
        edit_blocked = True
        edit_message = "This listing has been sold and can no longer be edited."
    elif listing["Status"] == 1 and bid_count > 0:
        edit_blocked = True
        edit_message = "This active listing cannot be edited because bidding has already started."
    elif listing["Status"] == 0:
        edit_blocked = True
        edit_message = "This listing is inactive and can no longer be edited."
        removal_info = get_listing_removal(seller_email,listing_id)

    return render_template(
        'listing_details.html',listing=listing,bid_count=bid_count,reserve_price_value=reserve_price_value,edit_blocked=edit_blocked,edit_message=edit_message,active_role=active_role,categories=category_options,removal_info=removal_info)
@app.route('/seller_dashboard/listing/<int:listing_id>/update', methods=['POST'])
def update_listing(listing_id):
    seller_email = session.get('user_email')

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    reserve_price_raw = request.form.get('reserve_price', '').strip()
    reserve_price = f"${reserve_price_raw}"
    quantity = request.form.get('quantity', '').strip()
    max_bids = request.form.get('max_bids', '').strip()

    update_auction_listing(seller_email,listing_id,name,description,
        category,reserve_price,quantity,max_bids)

    flash("Listing updated successfully.")
    return redirect(url_for('seller_dashboard'))

@app.route('/seller_dashboard/listing/<int:listing_id>/remove', methods=['POST'])
def remove_listing(listing_id):
    seller_email = session.get('user_email')

    removal_reason = request.form.get('removal_reason', '').strip()

    mark_listing_unactive(seller_email,listing_id,removal_reason)

    flash("Listing marked inactive.")
    return redirect(url_for('seller_dashboard'))

@app.route('/browse')
def browse():

    active_role = session.get('active_role')

    page = request.args.get('page', 1, type=int)
    per_page = 24
    offset = (page - 1) * per_page
    q = request.args.get('q','').strip()

    # handle sidebar categories
    selected_category = request.args.get('category', '').strip()
    # category_path = get_category_path(selected_category) if selected_category else []
    category_path = ["All Categories"]
    if selected_category=="All Categories":
        selected_category = None
    else:
        category_path += get_category_path(selected_category)


    # if category:
    #     categories = get_categories(category)
    # else:
    #     categories = get_categories(category=None)

    categories = get_categories(selected_category if selected_category else None)

    auction_rows, total_items = get_browse_items(q, per_page, offset, selected_category)
    

    # Convert data
    items = []
    for row in auction_rows:
        items.append({
            "listing_id": row["listing_id"],
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
            "seller": row["seller_name"],
            "price": row["price"] if row["price"] else 0,
            "image": "default-auction.jpg"
        })

    has_prev = page > 1
    has_next = offset + per_page < total_items

    return render_template('browse.html', items=items, categories=categories, category_path=category_path, page=page, has_prev=has_prev, has_next=has_next, active_role= active_role)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_email = session['user_email']
    user = get_user(user_email)
    active_role = session.get('active_role')
    address_id = get_user_address_id(user_email, roles = get_user_roles(user_email))

    if not user_email:
        return redirect("/")

    password_updated = False
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    street_num = request.form.get('street_num')
    street_name = request.form.get('street_name')
    zip_code = request.form.get('zip_code')

    # Update User First Name, Last Name, Age, Major
    if active_role == "Bidder":
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        age = request.form.get('age')
        major = request.form.get('major')
        try:
            update_bidder(first_name, last_name, age, major, user_email)
            print("Updated Bidder Profile")
        except Exception as e:
            print("Error updating Bidder Profile", e)

    # Update User Password
    # 1. Check Users Password cannot be empty
    if new_password and new_password.strip() != "":
        print("Password in not null")
        # 2. Check New Password need to be same with Confirm Password
        if new_password != confirm_password:
            flash("Passwords do not match")
            print("Passwords do not match")
            return redirect("/account")
        # 3. Old Password cannot be empty
        if not old_password:
            flash("Old password is required")
            print("Old password is required")
            return redirect("/account")
        hashed_input = hashlib.sha256(old_password.encode()).hexdigest()
        # 4. Old Password need to match before changing a new password
        if user['password_hash'] != hashed_input:
            flash("Current password does not match")
            print("Current password does not match")
            return redirect("/account")
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        # If all is good, It will try to update the Users Table in DB with new hashed password
        try:
            update_password(user_email, hashed_password)
            password_updated = True
            print("Updated Password")
        except Exception as e:
            print("Error updating Password", e)


    # Update User Address
    try:
        update_user_address(address_id, street_num, street_name, zip_code)
        print("Updated Address")
    except Exception as e:
        print("Error updating Address", e)

    # Redirect User to login page if user manages to update password
    if password_updated:
        return redirect("/login")
    return redirect("/account")




@app.route('/account')
def account():
    user_email = session['user_email']
    if not user_email:
        return redirect("/")

    roles = get_user_roles(session['user_email'])
    active_role = session.get('active_role')
    if active_role == 'Helpdesk':
        user_row = get_helpdesk(user_email)
    elif active_role == 'Seller':
        user_row = get_seller(user_email)
    else:
        user_row = get_bidder(user_email)

    user_address = get_user_address(user_email, roles)
    user_credit_cards = get_user_credit_cards(user_email)

    return render_template('account.html', user_data = user_row, active_role=active_role, roles = roles, user_address=user_address, credit_cards=user_credit_cards)

@app.route('/switch_role', methods=['POST'])
def switch_role():

    email = session.get('user_email')
    if not email:
        return redirect(url_for('login'))

    selected_role = request.form.get('active_role')

    session['active_role'] = selected_role

    if session['active_role'] == "Bidder":
        return redirect("/bidder_dashboard")
    elif session['active_role'] == "Seller":
        return redirect("/seller_dashboard")
    else:
        return redirect("/helpdesk_dashboard")

@app.route('/view_listing/<int:listing_id>', methods=['GET', 'POST'])
def view_listing(listing_id):

    # retrieve auction listing
    listing = get_listing(listing_id)
    if not listing:
        return "Listing not found.", 404

    # get reserve price and convert to float for comparison
    reserve_price = float(
        str(listing["Reserve_Price"])
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    # Handle bid submission
    if request.method == 'POST':

        # Check if user is logged in
        bidder = session.get('user_email')
        if not bidder:
            flash("You must be logged in")
            return redirect(url_for('login'))

        listing = get_listing(listing_id)
        seller = listing["Seller_Email"]

        # Get bid price from form and convert to float
        bid_price = float(request.form['bid_price'])

        # Check if bid is higher than current highest bid
        highest_bid = get_highest_bid(listing_id)

        highest_bidder = get_highest_bidder(listing_id)

        # 1. Check if bidder is the seller
        if bidder == seller:
            flash("Seller cannot bid on their own listing")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

        # 2. Check if bidder bid in two consecutive bids
        if bidder == highest_bidder:
            flash("Bidder cannot bid in two consecutive bids")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

        # 3. Check if bid is higher than reserve price and current highest bid
        if highest_bid is not None and bid_price <= highest_bid:

            # 3(a)Check if bid is higher than reserve price
            if bid_price < reserve_price:
                flash("Bid must be higher than reserve price")
                return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

            # 3(b) Bid is higher than reserve price but not higher than current highest bid
            flash("Bid must be higher than the latest bid")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder  )

        # 4. If there are no bids yet, check if bid is higher than reserve price
        if highest_bid is None and bid_price < reserve_price:
            flash("Bid must be higher than reserve price")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

        # 5. Check if max bids has been reached
        max_bids = listing["Max_Bids"]
        bid_count = get_bid_count(seller, listing_id)
        if bid_count >= max_bids:
            flash("Maximum number of bids reached for this listing")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

        if session.get('active_role') != "Bidder":
            flash("Only bidders can place bids")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)
        

        place_bid(listing_id, bidder, bid_price)
        return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)

    # Get the highest bid and bidder for table display
    bids = get_bids_history(listing_id)
    highest_bid = None
    highest_bidder = None

    if bids:
        highest_bid = bids[0]['Bid_Price']
        highest_bidder = bids[0]['Bidder_email']

    return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder)


# Helper Function : Make a hierarchical tree from category database
# def load_categories(rows):
#     nodes = {}
#     tree = []
#
#     for row in rows:
#         name = row['category_name'].strip()
#         parent = row['parent_category'].strip() if row['parent_category'] else None
#
#         node = {
#             'name': name,
#             'parent': parent,
#             'children': [],
#         }
#
#         nodes[name] = node
#
#     for node in nodes.values():
#         parent = node['parent']
#
#         if parent == '' or parent is None:
#             tree.append(node)
#         elif parent in nodes:
#             nodes[parent]['children'].append(node)
#         else:
#             tree.append(node)
#
#     return tree

# Helper function for loading categories in dropdown - used in create and edit auction for sellers
def build_category_dropdown(parent_category=None, level=0, result=None):
    if result is None:
        result = []

    rows = get_categories(parent_category)

    for row in rows:
        category_name = row['category_name']
        # Skip 'root' category
        if category_name != "Root":
            result.append({
                "name": category_name,
                "display_name": ("-" * level) + category_name,
            })

        build_category_dropdown(category_name, level + 1, result)

    return result

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():

    # helpdesk access only
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Helpdesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # load existing categories
    cur.execute("""
        SELECT *
        FROM Categories
        ORDER BY category_name
    """)

    categories = cur.fetchall()


    # submit new categories
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

@app.route('/change_user_id/<int:request_id>', methods=['GET', 'POST'])
def change_user_id(request_id):

    #helpdesk access only
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Helpdesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # LOAD REQUEST
    cur.execute("""
        SELECT *
        FROM Requests
        WHERE request_id = ?
    """, (request_id,))

    req = cur.fetchone()

    if not req:
        conn.close()
        return redirect(url_for('helpdesk_dashboard'))

    # SUBMIT CHANGE
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


        # UPDATE ALL TABLES
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
        WHERE request_id = ?
    """, (
        request_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('helpdesk_dashboard'))

@app.route('/remove_vendor/<vendor_email>')
def remove_vendor(vendor_email):

    # ONLY HELPDESK CAN USE THIS
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'Helpdesk':
        return redirect(url_for('login'))

    conn = db_connect()
    cur = conn.cursor()

    # VERIFY THIS IS A LOCAL VENDOR
    cur.execute("""
        SELECT *
        FROM Local_Vendors
        WHERE Email = ?
    """, (vendor_email,))

    vendor = cur.fetchone()

    if not vendor:
        conn.close()
        return redirect(url_for('helpdesk_dashboard'))

    # REMOVE ALL THEIR PRODUCTS
    cur.execute("""
        DELETE FROM Auction_Listings
        WHERE Seller_Email = ?
    """, (vendor_email,))

    # optional cleanup bids tied to listings
    cur.execute("""
        DELETE FROM Bids
        WHERE Seller_Email = ?
    """, (vendor_email,))


    # REMOVE LOCAL VENDOR RECORD
    cur.execute("""
        DELETE FROM Local_Vendors
        WHERE Email = ?
    """, (vendor_email,))

    conn.commit()
    conn.close()

    return redirect(url_for('helpdesk_dashboard'))



if __name__ == '__main__':
    app.run(debug=True)         # Set debug=True for development to allow auto-reloading 


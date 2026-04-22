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

        street_num = request.form['street_num'].strip()
        street_name = request.form['street_name'].strip()
        zipcode = request.form['zipcode'].strip()

        phone_num = request.form['phone'].strip()

        bank_num = request.form['bank_num'].strip()
        bank_route = request.form['bank_route'].strip()

        conn = db_connect()
        cur = conn.cursor()

        # Check for existing user
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error='Email already registered')

        hashed_input = hashlib.sha256(password.encode()).hexdigest()

        address_id = generate_unique_address_id(cur)

        cur.execute("INSERT INTO Users (email, password_hash) VALUES (?, ?)", (email, hashed_input))
        cur.execute("INSERT INTO Address (address_id,zipcode,street_num,street_name) VALUES (?,?,?,?)",(address_id,zipcode,street_num,street_name))

        # We assume LSU email = Bidder
        if email.endswith('@lsu.edu'):
            parts = name.split()
            first_name = parts[0] if len(parts) > 0 else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

            cur.execute("""INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (email, first_name, last_name, None, address_id, None))

            conn.commit()
            conn.close()

            session['user_email'] = email
            session['active_role'] = "Bidder"

            return redirect(url_for('bidder_dashboard'))

        # We assume non-LSU email = Sellers
        else:
            cur.execute("""INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
                        VALUES (?, ?, ?, ?)""",
                        (email, bank_route, bank_num, 0.00))
            cur.execute("""INSERT INTO Local_Vendors (Email,Business_Name,Business_Address_ID,Customer_Service_Phone_Number)
                        VALUES (?,?,?,?)""",
                        (email,name,address_id,phone_num))

            conn.commit()
            conn.close()

            session['user_email'] = email
            session['active_role'] = "Seller"

            return redirect(url_for('seller_dashboard'))

    return render_template('signup.html')

from db import get_bidder_auctions

@app.route('/bidder_dashboard')
def bidder_dashboard():

    active_role = session.get('active_role')
    bidder = session.get('user_email')
    bidder_name = get_bidder_display_name(bidder)
    auction_rows = get_bidder_auctions(bidder)

    items = []

    for auction in auction_rows:
        # listing = get_auction_listing_by_id(bidder, auction["Listing_ID"])
        listing = get_listing(auction["Listing_ID"])

        bid = get_bids_history(auction["Listing_ID"])
        bid_count = len(bid)
        # bid_count = get_bid_count(bidder, auction["Listing_ID"])

        if listing:
            status = listing["Status"]
        else:
            status = "Unknown"

        highest_bidder = auction["Bidder_Email"] if auction["Bidder_Email"] else "No bids yet"

        if highest_bidder:
            highest_bidder_name = get_bidder_display_name(highest_bidder)

        if highest_bidder == bidder:
            highest_bidder_name = "You"



        items.append({
            "listing_id": auction["Listing_ID"],
            "seller_email": listing["Seller_Email"],
            "name": auction["name"],
            "price": auction["Bid_Price"] if auction["Bid_Price"] else 0,
            "highest_bidder": highest_bidder,
            "highest_bidder_name": highest_bidder_name,
            "status": status,
            "image": "default-auction.jpg",
            "max_bids": listing["Max_bids"],
            "bid_count": bid_count,
            "is_winner": (highest_bidder == bidder)
        })

    return render_template('bidder.html', items=items, active_role=active_role)

@app.route('/seller_dashboard')
def seller_dashboard():

    seller_email = session['user_email']
    active_role = session.get('active_role')
    status_filter = request.args.get('filter', 'all')
    seller_rows = get_auction_listing(seller_email, status_filter)
    seller_rating = get_seller_rating(seller_email)

    items = []

    for row in seller_rows:
        items.append({
            "listing_id": row[0], # Listing ID
            "name": row[1],  # Product_Name
            "price": row[2],  # Reserve_Price (or current bid if you have it)
            "status" : row[3],
            "image": "default-auction.jpg"  # keep frontend unchanged
        })

    return render_template('seller.html', items=items, active_role=active_role, status_filter=status_filter, seller_rating=seller_rating)

@app.route('/helpdesk_dashboard')
def helpdesk_dashboard():

    user_email = session.get('user_email')
    unassigned_request = get_unassigned_request()
    ongoing_request = get_ongoing_request(user_email)
    completed_request = get_completed_request()
    return render_template('helpdesk.html', unassigned=unassigned_request, ongoing=ongoing_request, completed=completed_request)


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
    elif listing["Status"] == 3:
        edit_blocked = True
        edit_message = "This listing is in pending payment and can no longer be edited."

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
    if selected_category == "All Categories":
        selected_category = None
    else:
        category_path += get_category_path(selected_category)

    # if category:
    #     categories = get_categories(category)
    # else:
    #     categories = get_categories(category=None)

    categories = get_categories(selected_category if selected_category else None)

    # Only fetch items if user searches or selects category
    if q or selected_category:
        auction_rows, total_items = get_browse_items(q, per_page, offset, selected_category)
    else:
        auction_rows = []
        total_items = 0

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
    return redirect("/account")



@app.route('/update_password', methods=['POST'])
def update_password():
    user_email = session['user_email']
    user = get_user(user_email)
    active_role = session.get('active_role')
    address_id = get_user_address_id(user_email, roles=get_user_roles(user_email))

    password_updated = False
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    street_num = request.form.get('street_num')
    street_name = request.form.get('street_name')
    zipcode = request.form.get('zipcode')

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
        update_user_address(address_id, street_num, street_name, zipcode)
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

    win = False
    # retrieve auction listing
    listing = get_listing(listing_id)
    if not listing:
        return "Listing not found"

    # get reserve price and convert to float for comparison
    reserve_price = float(
        str(listing["Reserve_Price"])
        .replace("$", "")
        .replace(",", "")
        .strip()
    )

    listing = get_listing(listing_id)
    seller = listing["Seller_Email"]
    seller_rating = get_seller_rating(seller)

    # Handle bid submission
    if request.method == 'POST':

        # Check if user is logged in
        bidder = session.get('user_email')
        if not bidder:
            flash("You must be logged in")
            return redirect(url_for('login'))

        listing = get_listing(listing_id)
        seller = listing["Seller_Email"]
        seller_rating = get_seller_rating(seller)

        # Get bid price from form and convert to float
        bid_price = float(request.form['bid_price'])

        # Check if bid is higher than current highest bid
        highest_bid = get_highest_bid(listing_id)

        highest_bidder = get_highest_bidder(listing_id)

        # 1. Check if bidder is the seller
        if bidder == seller:
            flash("Seller cannot bid on their own listing")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

        # 2. Check if bidder bid in two consecutive bids
        if bidder == highest_bidder:
            flash("Bidder cannot bid in two consecutive bids")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

        # 3. Check if bid is higher than reserve price and current highest bid
        if highest_bid is not None and bid_price <= highest_bid:

            # 3(a)Check if bid is higher than reserve price
            if bid_price < reserve_price:
                flash("Bid must be higher than reserve price")
                return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

            # 3(b) Bid is higher than reserve price but not higher than current highest bid
            flash("Bid must be higher than the latest bid")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

        # 4. If there are no bids yet, check if bid is higher than reserve price
        if highest_bid is None and bid_price < reserve_price:
            flash("Bid must be higher than reserve price")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

        # 5. Check if max bids has been reached
        max_bids = listing["Max_Bids"]
        bid_count = get_bid_count(seller, listing_id)
        if bid_count >= max_bids:
            flash("Maximum number of bids reached for this listing")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

        # 6. Check if user is a bidder, seller cannot bit
        if session.get('active_role') != "Bidder":
            flash("Only bidders can place bids")
            return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)
        

        place_bid(listing_id, bidder, bid_price)
        new_bid_count = bid_count + 1

        # Get updated highest bid and bidder
        highest_bid = get_highest_bid(listing_id)
        highest_bidder = get_highest_bidder(listing_id)
        bids = get_bids_history(listing_id)

        # 7. win the auction
        if new_bid_count == max_bids:
            mark_listing_pending_payment(seller,listing_id)
            return redirect(url_for('payment', seller_email=seller, listing_id=listing_id))
            # flash("Congratulations! You have won the auction!")



        return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

    # Get the highest bid and bidder for table display
    bids = get_bids_history(listing_id)
    highest_bid = None
    highest_bidder = None

    if bids:
        highest_bid = bids[0]['Bid_Price']
        highest_bidder = bids[0]['Bidder_email']

    return render_template('view-listing.html', listing=listing, bids=get_bids_history(listing_id), highest_bid=highest_bid, active_role=session.get('active_role'), highest_bidder=highest_bidder, seller_rating=seller_rating)

@app.route('/payment/<seller_email>/<int:listing_id>')
def payment(seller_email, listing_id):
    active_role = session.get('active_role')
    user_email = session.get('user_email')
    highest_bidder = get_highest_bidder(listing_id)

    if user_email != highest_bidder:
        flash("Only the winning bidder can complete payment.")
        return redirect(url_for('bidder_dashboard'))

    seller_name = get_seller_display_name(seller_email)

    # retrieve listing
    listing = get_auction_listing_by_id(seller_email,listing_id)
    if not listing:
        return "Listing not found",404

    if listing["Status"] != 3:
        flash("This listing is not awaiting payment.")
        return redirect(url_for('bidder_dashboard'))

    # retrieve user credit cards
    cards = get_user_credit_cards(user_email)
    selected_card = cards[0]['credit_card_num'] if cards else None

    # retrieve the final (highest) bid
    final_price = get_highest_bid(listing_id)

    # initialization form action
    show_add_form = request.args.get('show_add_form', '0') == '1'

    return render_template(
        'payment.html',
        listing=listing,
        seller_name=seller_name,
        cards=cards,
        final_price=final_price,
        show_add_form=show_add_form,
        selected_card=selected_card,
        error=None,
        active_role=active_role
    )

@app.route('/payment/<seller_email>/<int:listing_id>/save_card', methods=['POST'])
def save_card(seller_email, listing_id):
    active_role = session.get('active_role')
    user_email = session.get('user_email')
    highest_bidder = get_highest_bidder(listing_id)

    if user_email != highest_bidder:
        flash("Only the winning bidder can complete payment.")
        return redirect(url_for('bidder_dashboard'))

    seller_name = get_seller_display_name(seller_email)

    listing = get_auction_listing_by_id(seller_email, listing_id)
    if not listing:
        return "Listing not found", 404

    if listing["Status"] != 3:
        flash("This listing is not awaiting payment.")
        return redirect(url_for('bidder_dashboard'))


    cards = get_user_credit_cards(user_email)
    selected_card = cards[0]['credit_card_num'] if cards else None

    final_price = get_highest_bid(listing_id)

    credit_card_num = request.form.get('credit_card_num', '').strip()
    card_type = request.form.get('card_type', '').strip()
    expire_month = request.form.get('expire_month', '').strip()
    expire_year = request.form.get('expire_year', '').strip()
    security_code = request.form.get('security_code', '').strip()

    # Input validation
    error = None

    if not credit_card_num or not card_type or not expire_month or not expire_year or not security_code:
        error = "Please fill in all credit card fields."

    elif not expire_month.isdigit():
        error = "Expire month must be a number."

    elif int(expire_month) < 1 or int(expire_month) > 12:
        error = "Expire month must be between 1 and 12."

    elif not expire_year.isdigit():
        error = "Expire year must be a number."

    elif not security_code.isdigit():
        error = "Security code must contain only digits."

    if error:
        return render_template(
            'payment.html',
            listing=listing,
            seller_name=seller_name,
            cards=cards,
            final_price=final_price,
            show_add_form=True,
            selected_card=selected_card,
            error=error,
            active_role=active_role
        )
    try:
        create_credit_card(
            credit_card_num=credit_card_num,
            card_type=card_type,
            expire_month=int(expire_month),
            expire_year=int(expire_year),
            security_code=security_code,
            owner_email=user_email
        )
    except Exception as e:
        flash("This credit card is already exist")
        return redirect(url_for('payment',seller_email=seller_email,listing_id=listing_id))

    return redirect(url_for('payment', seller_email=seller_email, listing_id=listing_id))

@app.route('/payment/<seller_email>/<int:listing_id>/submit', methods=['POST'])
def submit_payment(seller_email, listing_id):
    user_email = session.get('user_email')
    highest_bidder = get_highest_bidder(listing_id)

    if user_email != highest_bidder:
        flash("Only the winning bidder can complete payment.")
        return redirect(url_for('bidder_dashboard'))

    listing = get_auction_listing_by_id(seller_email,listing_id)
    if not listing:
        return "Listing not found",404

    if listing["Status"] != 3:
        flash("This listing is not awaiting payment.")
        return redirect(url_for('bidder_dashboard'))

    final_price = get_highest_bid(listing_id)

    create_transaction(
        seller_email=seller_email,
        listing_id=listing_id,
        bidder_email=user_email,
        payment_amount=final_price
    )

    mark_listing_sold(seller_email, listing_id)

    return redirect(url_for('bidder_dashboard'))

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

    if session.get('active_role') != 'Helpdesk':
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
            # case-insensitive duplicate check
            cur.execute("""
                SELECT *
                FROM Categories
                WHERE LOWER(TRIM(category_name)) =
                      LOWER(TRIM(?))
            """, (new_name,))

            exists = cur.fetchone()

            if exists:
                conn.close()
                return render_template(
                    "add_category.html",
                    categories=categories,
                    error="Category already exists."
                )

            # insert new category
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

        return render_template(
            "add_category.html",
            categories=categories,
            success="Category added successfully.")

    conn.close()

    return render_template(
        "add_category.html",
        categories=categories
    )

@app.route('/claim_request', methods=['POST'])
def claim_request():
    email = session.get('user_email')
    if not email:
        return redirect('/login')

    request_id = request.form.get('request_id')
    helpdesk_claim_request(email, request_id)
    return redirect('/helpdesk_dashboard')


@app.route('/complete_request', methods=['POST'])
def complete_request():
    email = session.get('user_email')
    if not email:
        return redirect('/login')

    request_id = request.form.get('request_id')
    helpdesk_complete_request(request_id)
    return redirect('/helpdesk_dashboard')

@app.route('/delete_card', methods=['POST'])
def delete_card():
    credit_card_num = request.form.get('credit_card_num')
    delete_credit_card(credit_card_num)
    return redirect('/account')

@app.route('/add_credit_card', methods=['POST'])
def add_credit_card():
    credit_card_num = request.form.get('credit_card_num')
    card_type = request.form.get('card_type')
    expire_month = request.form.get('expire_month')
    expire_year = request.form.get('expire_year')
    security_code = request.form.get('security_code')
    owner_email = session.get('user_email')

    if not credit_card_num.isdigit() or len(credit_card_num) not in [15, 16]:
        return redirect('/account')
    if not security_code.isdigit() or len(security_code) not in [3, 4]:
        return redirect('/account')
    if not all([credit_card_num, card_type, expire_month, expire_year, security_code]):
        return redirect('/account')
    try:
        create_credit_card(credit_card_num, card_type, expire_month, expire_year, security_code, owner_email)
        print("Credit card added")
    except Exception as e:
        print("Error Adding Credit Card", e)
    return redirect('/account')

@app.route('/submit_request')
def submit_request():
    active_role = session.get('active_role')
    roles = session.get('roles')
    return render_template('submit_request.html', active_role= active_role, roles=roles)

@app.route('/create_request', methods=['POST'])
def create_request():
    email = session.get('user_email')
    request_type = request.form.get('request_type')
    request_description = request.form.get('request_description')

    try:
        store_create_request(email,request_type,request_description)
        flash("Request submitted successfully!", "success")
        print("Request submitted")
    except Exception as e:
        flash(f"Error Submitting Request: {str(e)}", "danger")
        print("Error Submitting Request", e)
    return redirect('/submit_request')

@app.route('/dashboard')
def dashboard():
    active_role = session.get('active_role')
    if active_role == "Bidder":
        return redirect("bidder_dashboard")
    elif active_role == "Seller":
        return redirect("seller_dashboard")
    else:
        return redirect(url_for('helpdesk_dashboard'))


@app.route('/rating')
def rating():
    seller_email = request.args.get('seller_email')
    return render_template("rating.html", seller_email=seller_email)

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    bidder_email = session.get('user_email')
    seller_email = request.form.get('seller_email')
    rating = request.form.get('rating')
    rating_desc = request.form.get('rating_description')
    try:
        store_rating(bidder_email,seller_email,rating,rating_desc)
        print("Rating submitted")
    except Exception as e:
        print("Error Submitting Rating", e)
        return render_template("rating.html", seller_email=seller_email)
    return redirect("/dashboard")






if __name__ == '__main__':
    app.run(debug=True)         # Set debug=True for development to allow auto-reloading 


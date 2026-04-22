import sqlite3

DB_NAME = 'auction.db'
def db_connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    return user

def get_user_roles(email):
    conn = db_connect()
    cur = conn.cursor()

    roles = []

    cur.execute("SELECT * FROM Helpdesk WHERE email = ?", (email,))
    if cur.fetchone():
        roles.append("Helpdesk")

    cur.execute("SELECT * FROM Sellers WHERE email = ?", (email,))
    if cur.fetchone():
        roles.append("Seller")

    cur.execute("SELECT * FROM Bidders WHERE email = ?", (email,))
    if cur.fetchone():
        roles.append("Bidder")

    conn.close()
    return roles

def get_bidder(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Bidders WHERE email = ?", (email,))

    bidder_row = cur.fetchone()
    conn.close()
    return bidder_row


def get_seller(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Sellers WHERE email = ?", (email,))

    seller_row = cur.fetchone()
    conn.close()
    return seller_row

def get_helpdesk(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Helpdesk WHERE email = ?", (email,))

    helpdesk_row = cur.fetchone()
    conn.close()
    return helpdesk_row

def create_user(email, password_hash):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO Users (email, password_hash) VALUES (?, ?)",
        (email, password_hash)
    )

    conn.commit()
    conn.close()

def create_user_bidder(email, first_name, last_name, age, home_address_id, major):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (email, first_name, last_name, age, home_address_id, major))

    conn.commit()
    conn.close()

def create_user_seller(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
        VALUES (?, ?, ?, ?)
    """, (email, None, None, 0.00))

    conn.commit()
    conn.close()

def update_password(email, password_hash):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
                UPDATE Users
                SET password_hash = ?
                WHERE email = ?
                """, [password_hash, email])
    conn.commit()
    conn.close()

def update_bidder(first_name, last_name, age, major, email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                UPDATE Bidders
                SET first_name = ?, last_name  = ?, age = ?, major = ?
                WHERE email = ?
                """, (first_name, last_name, age , major, email))
    conn.commit()
    conn.close()


def get_bidder_auctions(bidder_email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            a.Listing_ID,
            a.Product_Name AS name,
            b.Bidder_Email,
            b.Bid_Price

        FROM Bids b
        JOIN Auction_Listings a 
            ON a.Listing_ID = b.Listing_ID

        WHERE b.Bid_Price = (
            SELECT MAX(b2.Bid_Price)
            FROM Bids b2
            WHERE b2.Listing_ID = b.Listing_ID
        )

        AND a.Listing_ID IN (
            SELECT Listing_ID 
            FROM Bids 
            WHERE Bidder_Email = ?
        )
    """, (bidder_email,))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_auction_listing(email, status_filter):
    conn = db_connect()
    cur = conn.cursor()

    if status_filter == "active":
        filter_query = "AND Status = 1"
    elif status_filter == "inactive":
        filter_query = "AND Status = 0"
    elif status_filter == "sold":
        filter_query = "AND Status = 2"
    else:
        filter_query = ""

    cur.execute(f"""
                SELECT Listing_ID,Product_Name, Reserve_Price,Status
                FROM Auction_Listings
                WHERE Seller_Email = ? {filter_query}
                """, (email,))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_browse_items(q, per_page=100, offset=0, category=None):
    conn = db_connect()
    cur = conn.cursor()
    params = []

    # base query for both search bar and category sidebar; join auction_listings with Local_Vendors and Bidders to get seller names; filter by active listings only
    base_query = """
    FROM Auction_Listings a
    LEFT JOIN Local_Vendors lv
        ON a.Seller_Email = lv.Email
    LEFT JOIN Bidders bd
        ON a.Seller_Email = bd.Email
    WHERE a.status = 1
    """
    
    # filter by using SEARCH BAR; search across multiple fields in both auction_listings and seller tables
    if q:
        keyword = f"%{q}%"
        base_query += """
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
        params.extend([keyword]*7)


    # filter by using CATEGORY SIDEBAR if sidebar category is selected
    if category:
        base_query += """ AND a.Category = ? """
        params.append(category)

    # Count query
    cur.execute(f"""
        SELECT COUNT(*) AS total
        {base_query}
    """, params)
    total_items = cur.fetchone()["total"]

    # Main query
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
            (SELECT MAX(Bid_Price)
             FROM Bids b
             WHERE b.Listing_ID = a.Listing_ID) AS price
        {base_query}
        ORDER BY a.Listing_ID
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    auction_rows = cur.fetchall()
    conn.close()

    return auction_rows, total_items

def get_categories(parent=None):
    conn = db_connect()
    cur = conn.cursor()

    if parent:
        cur.execute("""
            SELECT * FROM Categories
            WHERE parent_category = ?
        """, (parent,))
    else:
        cur.execute("""
            SELECT * FROM Categories
            WHERE parent_category = 'Root'
        """)

    rows = cur.fetchall()
    conn.close()
    return rows

def create_auction_listing(seller_email,auction_title,name,description,category,reserve_price,max_bids,quantity):
    conn = db_connect()
    cur = conn.cursor()

    # create a new listing id
    # idea: get the max value of the listing id for that seller and increment by 1
    cur.execute("""
                SELECT MAX(Listing_ID) AS max_id
                FROM Auction_Listings
                """)

    row = cur.fetchone()
    listing_id = (row["max_id"] + 1) if row["max_id"] is not None else 1

    cur.execute("""
                INSERT INTO Auction_Listings
                (Seller_Email,Listing_ID,Auction_Title,Product_Name,Product_Description,Category,
                 Reserve_Price,Max_bids,Quantity,Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,?,?)
                """, (
                    seller_email,listing_id,auction_title,name,description,category,
                    reserve_price,max_bids,quantity,1
                ))

    conn.commit()
    conn.close()

def get_auction_listing_by_id(seller_email,listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                SELECT *
                FROM Auction_Listings
                WHERE Seller_Email = ?
                  AND Listing_ID = ?
                """, (seller_email, listing_id))

    listing = cur.fetchone()
    conn.close()

    return listing

def get_bid_count(seller_email,listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                SELECT COUNT(*) AS bid_count
                FROM Bids
                WHERE Seller_Email = ?
                  AND Listing_ID = ?
                """, (seller_email, listing_id))

    # result = cur.fetchone()
    # conn.close()

    return cur.fetchone()["bid_count"]

def update_auction_listing(seller_email, listing_id, product_name, product_description,
                           category, reserve_price, quantity, max_bids):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE Auction_Listings
        SET Product_Name = ?,
            Product_Description = ?,
            Category = ?,
            Reserve_Price = ?,
            Quantity = ?,
            Max_bids = ?
        WHERE Seller_Email = ? AND Listing_ID = ?
    """, (
        product_name,
        product_description,
        category,
        reserve_price,
        quantity,
        max_bids,
        seller_email,
        listing_id
    ))

    conn.commit()
    conn.close()

def get_category_path(category):
    conn = db_connect()
    cur = conn.cursor()

    # store path in list from root to children
    path = []

    while category and category != "Root":
        path.insert(0, category)   # add to front

        cur.execute("""
            SELECT parent_category
            FROM Categories
            WHERE category_name = ?
        """, (category,))

        row = cur.fetchone()
        category = row["parent_category"] if row else None

    conn.close()
    return path

def mark_listing_unactive(seller_email,listing_id, removal_reason):
    conn = db_connect()
    cur = conn.cursor()

    listing = get_auction_listing_by_id(seller_email, listing_id)
    bid_count = get_bid_count(seller_email, listing_id)

    # compute remaining bids
    remaining_bids = max(0, listing["Max_bids"] - bid_count)

    # insert into audit table
    cur.execute("""
                INSERT INTO Listings_Removal
                    (Seller_Email, Listing_ID, Removal_Reason, Remaining_Bids)
                VALUES (?, ?, ?, ?)
                """, (seller_email, listing_id, removal_reason, remaining_bids))

    # update status → inactive
    cur.execute("""
                UPDATE Auction_Listings
                SET Status = 0
                WHERE Seller_Email = ?
                  AND Listing_ID = ?
                """, (seller_email, listing_id))

    conn.commit()
    conn.close()

def get_listing_removal(seller_email,listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                SELECT Removal_Reason, Remaining_Bids
                FROM Listings_Removal
                WHERE Seller_Email = ?
                  AND Listing_ID = ?
                """, (seller_email, listing_id))

    row = cur.fetchone()
    conn.close()
    return row

def get_listing(listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM Auction_Listings
        WHERE Listing_ID = ?
    """, (listing_id,))

    listing = cur.fetchone()
    conn.close()

    return listing

def get_bids_history(listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT Bidder_email, Bid_Price
        FROM Bids
        WHERE Listing_ID = ?
        ORDER BY Bid_Price DESC
    """, (listing_id,))

    bids = cur.fetchall()
    conn.close()

    return bids

def place_bid(listing_id, bidder_email, bid_price):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT MAX(Bid_ID) FROM Bids")
    max_bid_id = cur.fetchone()
    next_bid_id = (max_bid_id[0] + 1) if max_bid_id[0] is not None else 1

    seller_email = get_listing(listing_id)["Seller_Email"]

    cur.execute("""
        INSERT INTO Bids (Bid_ID, Listing_ID, Bidder_email, Bid_Price, Seller_Email)
        VALUES (?, ?, ?, ?, ?)
    """, (next_bid_id, listing_id, bidder_email, bid_price, seller_email))

    conn.commit()
    conn.close()

def get_highest_bid(listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT MAX(Bid_Price) AS highest_bid
        FROM Bids
        WHERE Listing_ID = ?
    """, (listing_id,))

    result = cur.fetchone()
    conn.close()

    if result["highest_bid"] is not None:
        return result["highest_bid"]



def get_highest_bidder(listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT Bidder_email
        FROM Bids
        WHERE Listing_ID = ?
        ORDER BY Bid_Price DESC
        LIMIT 1
    """, (listing_id,))

    result = cur.fetchone()
    conn.close()

    if result:
        return result["Bidder_email"]

def get_user_address_id(email, roles):
    conn = db_connect()
    cur = conn.cursor()

    if "Bidder" in roles:
        cur.execute("""
            SELECT home_address_id
            FROM Bidders
            WHERE email = ?
        """, (email,))
    else:
        cur.execute("""
            SELECT business_address_id
            FROM Local_Vendors
            WHERE email = ?
        """, (email,))

    address_row = cur.fetchone()
    address_id = address_row[0]

    conn.close()

    return address_id

def get_user_address(email,roles):
    conn = db_connect()
    cur = conn.cursor()

    address_id = get_user_address_id(email, roles)
    cur.execute("""
        SELECT zipcode, street_num, street_name
        FROM Address
        WHERE address_id = ?
    """, (address_id,))

    result = cur.fetchone()
    conn.close()
    return result

def update_user_address(address_id, street_num, street_name, zipcode):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE Address
        SET street_num = ?, street_name = ?, zipcode = ?
        WHERE address_id = ?
    """, (street_num, street_name,zipcode,address_id))

    conn.commit()
    conn.close()

def get_user_credit_cards(email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM Credit_Cards
        WHERE owner_email = ?
    """, (email,))

    cards = cur.fetchall()
    conn.close()

    if not cards:
        return []
    return cards

def get_completed_request():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(""" 
        SELECT *
        FROM Requests
        WHERE request_status = 1
    """,)
    completed_requests = cur.fetchall()
    conn.close()

    if not completed_requests:
        return []
    return completed_requests

def get_unassigned_request():

    helpdesk_email = "helpdeskteam@lsu.edu"
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
                SELECT request_id,sender_email,request_type,request_desc
                FROM Requests
                WHERE helpdesk_staff_email = ?
                """, (helpdesk_email,))
    unassigned_requests = cur.fetchall()
    conn.close()
    if not unassigned_requests:
        return []
    return unassigned_requests

def get_ongoing_request(email):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
                SELECT request_id,sender_email,request_type,request_desc
                FROM Requests
                WHERE helpdesk_staff_email = ? AND request_status = 0
                """,(email,))
    ongoing_request = cur.fetchall()
    conn.close()
    if not ongoing_request:
        return []
    return ongoing_request

def get_local_vendors():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM Local_Vendors
    """,)
    local_vendors = cur.fetchall()
    conn.close()

# Claim Request by Changing the helpdesk_staff_email to user claiming the request's email
def helpdesk_claim_request(email, request_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE Requests
        SET helpdesk_staff_email = ?
        WHERE request_id = ?
    """, (email, request_id))
    conn.commit()
    conn.close()

# Complete Request by Changing the request status to 1
def helpdesk_complete_request(request_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE Requests
        SET request_status = 1
        WHERE request_id = ?
    """, (request_id,))
    conn.commit()
    conn.close()

def delete_credit_card(credit_card_num):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM Credit_Cards
        WHERE credit_card_num = ?
    """, (credit_card_num,))
    conn.commit()
    conn.close()


def create_credit_card(credit_card_num, card_type, expire_month, expire_year, security_code, owner_email):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO Credit_Cards
                (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    credit_card_num, card_type, expire_month, expire_year, security_code, owner_email,))
    conn.commit()
    conn.close()

def store_create_request(email, request_type, request_desc):
    conn = db_connect()
    cur = conn.cursor()

    # Get Biggest request ID to create new request ID
    cur.execute("""
        SELECT MAX(request_id) 
        FROM Requests
    """,)
    result = cur.fetchone()

    # If no request_id (table is empty) create request_id = 1
    if result[0] is None:
        next_id = 1
    else:
        # Increment request_id by 1 to ensure PK holds
        next_id = result[0] + 1

    helpdesk_email = "helpdeskteam@lsu.edu"
    cur.execute("""INSERT INTO Requests (request_id, sender_email,helpdesk_staff_email, request_type, request_desc, request_status)
        VALUES (?, ?, ?, ?, ?,?)
    """, (next_id, email, helpdesk_email, request_type, request_desc, 0))
    conn.commit()
    conn.close()


def create_transaction(seller_email, listing_id, bidder_email, payment_amount):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT MAX(Transaction_ID) AS max_id FROM Transactions")
    row = cur.fetchone()
    next_transaction_id = (row["max_id"] + 1) if row["max_id"] is not None else 1

    cur.execute("""
        INSERT INTO Transactions (Transaction_ID, Seller_Email, Listing_ID, Bidder_Email, Date, Payment)
        VALUES (?, ?, ?, ?, DATE('now'), ?)
    """, (next_transaction_id, seller_email, listing_id, bidder_email, payment_amount))

    conn.commit()
    conn.close()

def mark_listing_sold(seller_email, listing_id):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE Auction_Listings
        SET Status = 2
        WHERE Seller_Email = ? AND Listing_ID = ?
    """, (seller_email, listing_id))

    conn.commit()
    conn.close()

def get_seller_display_name(seller_email):
    conn = db_connect()
    cur = conn.cursor()

    # First try local vendor
    cur.execute("""
        SELECT Business_Name
        FROM Local_Vendors
        WHERE Email = ?
    """, (seller_email,))
    row = cur.fetchone()
    if row and row["Business_Name"]:
        conn.close()
        return row["Business_Name"]

    # Then try bidder
    cur.execute("""
        SELECT first_name, last_name
        FROM Bidders
        WHERE email = ?
    """, (seller_email,))
    row = cur.fetchone()
    conn.close()

    if row:
        first_name = row["first_name"] or ""
        last_name = row["last_name"] or ""
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name

    return seller_email

def get_bidder_display_name(bidder_email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT first_name, last_name
        FROM Bidders
        WHERE email = ?
    """, (bidder_email,))
    row = cur.fetchone()
    conn.close()

    if row:
        first_name = row["first_name"] or ""
        last_name = row["last_name"] or ""
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            return full_name

    return bidder_email




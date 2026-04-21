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

def update_bidder(first_name, last_name, age, home_address_id, major, email):
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
                UPDATE Bidders
                SET first_name = ?, last_name  = ?, age = ?, home_address_id = ?, major = ?
                WHERE email = ?
                """, (first_name, last_name, age , home_address_id, major, email))
    conn.commit()
    conn.close()


def get_active_auctions(limit=8):
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
        LIMIT ?
    """, (limit,))

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

    cur.execute("""
                INSERT INTO Auction_Listings
                (Seller_Email,Auction_Title,Product_Name,Product_Description,Category,
                 Reserve_Price,Max_bids,Quantity,Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)
                """, (
                    seller_email,auction_title,name,description,category,
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
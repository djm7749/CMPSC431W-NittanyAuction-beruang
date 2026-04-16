import os
import sqlite3
import pandas as pd
import hashlib

DB_NAME = "auction.db"
DATASETPATH = "NittanyAuctionDataset_v1/"

# Hash Password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# INIT DATABASE
def init_db():
    print("Initializing database...")
    if os.path.exists(DB_NAME):
        print("Database already exists. Skipping initialization.")
        return

    print("Initializing database...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE Users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );
    """)

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

    cursor.execute("""
       CREATE TABLE Sellers (
           email TEXT PRIMARY KEY,
           bank_routing_number TEXT,
           bank_account_number TEXT,
           balance REAL,
           FOREIGN KEY (email) REFERENCES Users (email)
       );
    """)

    cursor.execute("""
       CREATE TABLE Helpdesk (
           email TEXT PRIMARY KEY,
           position TEXT,
           FOREIGN KEY (email) REFERENCES Users (email)
       );
    """)

    cursor.execute("""
        CREATE TABLE Categories(
            category_name TEXT PRIMARY KEY,
            parent_category TEXT,
            FOREIGN KEY (parent_category) REFERENCES Categories (category_name)
        );
    """)

    cursor.execute("""
       CREATE TABLE Auction_Listings(
           seller_email TEXT,
           listing_id INTEGER,
           category TEXT,
           auction_title TEXT,
           product_name TEXT,
           product_description TEXT,
           quantity INTEGER,
           reserve_price REAL,
           max_bids INTEGER,
           status INTEGER DEFAULT 1,    
           PRIMARY KEY (seller_email, listing_id),
           FOREIGN KEY (seller_email) REFERENCES Sellers (email),
           FOREIGN KEY (category) REFERENCES Categories (category_name)
       );
    """)

    cursor.execute("""
       CREATE TABLE Bids(
           bid_id INTEGER PRIMARY KEY AUTOINCREMENT,
           seller_email TEXT,
           listing_id INTEGER,
           bidder_email TEXT,
           bid_price REAL,
           FOREIGN KEY (seller_email, listing_id) REFERENCES Auction_Listings (seller_email, listing_id),
           FOREIGN KEY (bidder_email) REFERENCES Bidders (email)
       );
    """)

    cursor.execute("""
        CREATE TABLE Zipcode_Info (
            zipcode TEXT PRIMARY KEY,
            city TEXT,
            state TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE Address (
            address_id INTEGER PRIMARY KEY,
            zipcode TEXT,
            street_num TEXT,
            street_name TEXT,
            FOREIGN KEY (zipcode) REFERENCES Zipcode_Info(zipcode)
        );
    """)

    cursor.execute("""
        CREATE TABLE Local_Vendors (
            email TEXT PRIMARY KEY,
            business_name TEXT,
            business_address_id INTEGER,
            customer_service_phone_number TEXT,
            FOREIGN KEY (email) REFERENCES Sellers(email),
            FOREIGN KEY (business_address_id) REFERENCES Address(address_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE Credit_Cards (
            credit_card_num TEXT PRIMARY KEY,
            card_type TEXT,
            expire_month INTEGER,
            expire_year INTEGER,
            security_code TEXT,
            owner_email TEXT,
            FOREIGN KEY (owner_email) REFERENCES Bidders(email)
        );
    """)

    cursor.execute("""
        CREATE TABLE Transactions (
            transaction_id INTEGER PRIMARY KEY,
            seller_email TEXT,
            listing_id INTEGER,
            buyer_email TEXT,
            date TEXT,
            payment REAL,
            FOREIGN KEY (seller_email, listing_id)
                REFERENCES Auction_Listings(seller_email, listing_id),
            FOREIGN KEY (buyer_email) REFERENCES Bidders(email)
        );
    """)

    cursor.execute("""
        CREATE TABLE Rating (
            bidder_email TEXT,
            seller_email TEXT,
            date TEXT,
            rating INTEGER,
            rating_desc TEXT,
            PRIMARY KEY (bidder_email, seller_email, date),
            FOREIGN KEY (bidder_email) REFERENCES Bidders(email),
            FOREIGN KEY (seller_email) REFERENCES Sellers(email)
        );
    """)

    cursor.execute("""
        CREATE TABLE Requests (
            request_id INTEGER PRIMARY KEY,
            sender_email TEXT,
            helpdesk_staff_email TEXT,
            request_type TEXT,
            request_desc TEXT,
            request_status INTEGER,
            FOREIGN KEY (sender_email) REFERENCES Users(email),
            FOREIGN KEY (helpdesk_staff_email) REFERENCES Helpdesk(email)
        );
    """)

    print("Tables created.")

    # Populate Users
    try:
        users_df = pd.read_csv("NittanyAuctionDataset_v1/Users.csv")

        for _, row in users_df.iterrows():
            email = row["email"]
            password = hash_password(row["password"])

            cursor.execute("""
                INSERT INTO Users (email, password_hash)
                VALUES (?, ?)
            """, (row["email"], hash_password(row["password"])))
        print("Users loaded successfully!")
    except Exception as e:
        print("Error loading Users:", e)

    # Populate Bidders
    try:
        bidders_df = pd.read_csv(DATASETPATH + "Bidders.csv")

        for _, row in bidders_df.iterrows():
            cursor.execute("""
                INSERT INTO Bidders (email, first_name, last_name, age, home_address_id, major)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (row["email"],row["first_name"],row["last_name"],row["age"],row["home_address_id"],row["major"]))

        print("Bidders loaded.")
    except Exception as e:
        print("Error loading Bidders:", e)

    # Populate Sellers
    try:
        sellers_df = pd.read_csv(DATASETPATH + "Sellers.csv")

        for _, row in sellers_df.iterrows():
            cursor.execute("""
                INSERT INTO Sellers (email, bank_routing_number, bank_account_number, balance)
                VALUES (?, ?, ?, ?)
            """, (row["email"],row["bank_routing_number"],row["bank_account_number"],row["balance"]))

        print("Sellers loaded.")
    except Exception as e:
        print("Error loading Sellers:", e)

    # Populate HelpDesk
    try:
        helpdesk_df = pd.read_csv(DATASETPATH + "Helpdesk.csv")

        for _, row in helpdesk_df.iterrows():
            cursor.execute("""
                INSERT INTO Helpdesk (email, position)
                VALUES (?, ?)
            """, (row["email"],row["Position"]))

        print("Helpdesk loaded.")
    except Exception as e:
        print("Error loading Helpdesk:", e)

    # Populate Categories
    try:
        categories_df = pd.read_csv(DATASETPATH + "Categories.csv")

        for _, row in categories_df.iterrows():
            cursor.execute("""
               INSERT INTO Categories (category_name, parent_category)
               VALUES (?, ?)
               """, (row["category_name"],row["parent_category"]))

        print("Categories loaded.")
    except Exception as e:
        print("Error loading Categories:", e)

    # Populate Auction_Listings
    try:
        listings_df = pd.read_csv(DATASETPATH + "Auction_Listings.csv")

        for _, row in listings_df.iterrows():
            cursor.execute("""
                           INSERT INTO Auction_Listings (seller_email, listing_id, category,auction_title, product_name, product_description,quantity, reserve_price, max_bids, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (row["Seller_Email"], row["Listing_ID"], row["Category"], row["Auction_Title"], row["Product_Name"], row["Product_Description"], row["Quantity"], row["Reserve_Price"], row["Max_bids"], row.get("Status", 1)))

        print("Auction Listings loaded.")
    except Exception as e:
        print("Error loading Auction Listings:", e)

    # Populate Bids
    try:
        bids_df = pd.read_csv(DATASETPATH + "Bids.csv")

        for _, row in bids_df.iterrows():
            cursor.execute("""
                           INSERT INTO Bids (seller_email, listing_id, bidder_email, bid_price)
                           VALUES (?, ?, ?, ?)
                           """, (row["Seller_Email"],row["Listing_ID"],row["Bidder_Email"],row["Bid_Price"]))

        print("Bids loaded.")
    except Exception as e:
        print("Error loading Bids:", e)


    # Populate Zipcode_info
    try:
        zipcode_df = pd.read_csv(DATASETPATH + "Zipcode_Info.csv")

        for _, row in zipcode_df.iterrows():
            cursor.execute("""
                        INSERT INTO Zipcode_Info (zipcode, city, state)
                        VALUES (?, ?, ?)
                        """, (row["zipcode"], row["city"], row["state"]))

        print("Zipcode_Info loaded.")
    except Exception as e:
        print("Error loading Zipcode_Info:", e)


    # Populate Address
    try:
        address_df = pd.read_csv(DATASETPATH + "Address.csv")

        for _, row in address_df.iterrows():
            cursor.execute("""
                        INSERT INTO Address (address_id, zipcode, street_num, street_name)
                        VALUES (?, ?, ?, ?)
                        """, (row["address_id"], row["zipcode"], row["street_num"], row["street_name"]))

        print("Address loaded.")
    except Exception as e:
        print("Error loading Address:", e)


    # Populate Local_Vendors
    try:
        vendors_df = pd.read_csv(DATASETPATH + "Local_Vendors.csv")

        for _, row in vendors_df.iterrows():
            cursor.execute("""
                        INSERT INTO Local_Vendors (email, business_name, business_address_id, customer_service_phone_number)
                        VALUES (?, ?, ?, ?)
                        """, (row["Email"], row["Business_Name"], row["Business_Address_ID"], row["Customer_Service_Phone_Number"]))

        print("Local_Vendors loaded.")
    except Exception as e:
        print("Error loading Local_Vendors:", e)


    # Populate Credit_cards
    try:
        cards_df = pd.read_csv(DATASETPATH + "Credit_Cards.csv")

        for _, row in cards_df.iterrows():
            cursor.execute("""
                        INSERT INTO Credit_Cards (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (row["credit_card_num"], row["card_type"], row["expire_month"], row["expire_year"], row["security_code"], row["Owner_email"]))

        print("Credit_Cards loaded.")
    except Exception as e:
        print("Error loading Credit_Cards:", e)


    # Populate Transactions
    try:
        cards_df = pd.read_csv(DATASETPATH + "Credit_Cards.csv")

        for _, row in cards_df.iterrows():
            cursor.execute("""
                        INSERT INTO Credit_Cards (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (row["credit_card_num"], row["card_type"], row["expire_month"], row["expire_year"], row["security_code"], row["Owner_email"]))

        print("Credit_Cards loaded.")
    except Exception as e:
        print("Error loading Credit_Cards:", e)

    
    # Populate Ratings
    try:
        rating_df = pd.read_csv(DATASETPATH + "Ratings.csv")

        for _, row in rating_df.iterrows():
            cursor.execute("""
                        INSERT INTO Rating (bidder_email, seller_email, date, rating, rating_desc)
                        VALUES (?, ?, ?, ?, ?)
                        """, (row["Bidder_Email"], row["Seller_Email"], row["Date"], row["Rating"], row["Rating_Desc"]))

        print("Rating loaded.")
    except Exception as e:
        print("Error loading Rating:", e)


    # Populate Requests
    try:
        req_df = pd.read_csv(DATASETPATH + "Requests.csv")

        for _, row in req_df.iterrows():
            cursor.execute("""
                        INSERT INTO Requests (request_id, sender_email, helpdesk_staff_email, request_type, request_desc, request_status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (row["request_id"], row["sender_email"], row["helpdesk_staff_email"], row["request_type"], row["request_desc"], row["request_status"]))

        print("Requests loaded.")
    except Exception as e:
        print("Error loading Requests:", e)


    conn.commit()
    conn.close()

    print("Database initialized successfully!")
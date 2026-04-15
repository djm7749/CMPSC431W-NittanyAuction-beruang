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

    conn.commit()
    conn.close()

    print("Database initialized successfully!")
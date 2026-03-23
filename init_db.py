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

    conn.commit()
    conn.close()

    print("Database initialized successfully!")
**NittanyAuction Prototype – Authentication System**

**Overview**

This project is a simple prototype of the NittanyAuction system built using Flask and SQLite.
The current implementation focuses on user authentication, including signup, login, and role-based access.

**Features**

- User signup (Bidder or Seller)
- Secure login using hashed passwords (SHA-256)
- Role-based login:
  - Bidder → browse listings, place bids, manage account, submit requests, rate sellers
  - Seller → create/manage auctions, view bids, maintain seller info
  - Helpdesk → process requests, approve seller applications, manage vendors, manage categories, change user IDs

**Technologies Used**

- Python (Flask)
- SQLite3
- Pandas (for database population from CSV files)
- HTML (basic templates)

**Database Initialization and Population**
- The database is created and populated automatically using init_db.py.
- Process:
    - Creates tables: 
      1. Users(email*, password) 
      
      2. Bidders(email*, first_name, last_name, age, home_address_id, major)
      
      3. Sellers(email*, bank_routing_number, bank_account_number, balance)
      
      4. Helpdesk(email*, position)
      
      5. Auction_listings(Seller_Email*, Listing_ID*, Category, Auction_Title, Product_Name,
         Product_Description, Quantity, Reserve_Price, Max_bids, Status)
      
      6. Bids(Bid_ID*, Seller_Email, Listing_ID, Bidder_email, Bid_price)
      
      7. Requests(request_id*, sender_email, helpdesk_staff_email, request_type,
         request_desc, request_status)
      
      8. Categories(parent_category, category_name*)
      
      9. Credit_cards(credit_card_num*, card type, expire_month, expire_year,
         security_code, Owner_email)
      
      10. Rating(Bidder_Email*, Seller_Email*, Date*, Rating, Rating_Desc)
      
      11. Local_Vendors(Email, Business_Name, Business_Address_ID,
            Customer_Service_Phone_Number)
      
      12. Address(address_ID*, zipcode, street_num, street_name)
      
      13. Zipcode_info(zipcode*, city, state)
      
      14. Transactions(Transaction_ID*, Seller_Email, Listing_ID, Buyer_Email, Date,
            Payment)
      
    - Loads data from CSV files in the dataset folder
    - Hashes all passwords using SHA-256 before inserting into the Users table
    - Ensures foreign key relationships between Users and role tables

**Authentication Logic**

Login:

1. User enters email and password
2. System checks Users table for the email
3. Entered password is hashed and compared with stored password_hash
4. If valid, system checks role tables:
   - Bidders → bidder dashboard
   - Sellers → seller dashboard
   - Helpdesk → helpdesk dashboard

Signup:

1. System checks if email already exists
2. Password is hashed before storing
3. If email ends with @lsu.edu → registered as Bidder,
   Otherwise → registered as Seller

Bidder Features:
1. Browse active auctions
2. Search listings
3. Browse by category hierarchy
4. Place bids
5. Cannot bid on own listings
6. View bid history
7. Apply to become seller 
8. Submit support requests 
9. Rate sellers after winning auctions 
10. Manage profile 
11. Add/remove credit cards

Seller Features:
1. Seller dashboard 
2. Create auctions 
3. Set reserve price of an auction
4. Set max bids 
5. View highest bids 
6. Seller rating display 
7. Update bank info

HelpDesk Features
1. View pending/completed requests
2. Approve seller applications 
3. Change user IDs 
4. Add new categories 
5. Manage local vendors 
6. Remove vendors and their listings

Category System
- Supports parent-child hierarchy:
- Example:
- Electronics
-    ├── Computers 
-    │     ├── Laptops 
-    │     └── Desktops 
-    └── Phones
- Users can browse listings through nested categories.

Local Vendors
- Special subclass of sellers.
- Stores:
1. Business Name
2. Business Address
3. Customer Service Phone
- If a local vendor leaves, their listings are automatically removed.


**Requirements / Installation**

Make sure you have Python installed. Then install required packages:

  ```pip install flask pandas```

**How to Run the Application**

1. Open terminal in the project folder
2. Run the application:
   
   ```python app.py```

4. Open your browser and go to:
   
   ```http://127.0.0.1:5000``` (or http://localhost:5000)

**Project Structure**

1. app.py – main Flask application
2. init_db.py – database creation and population script
3. auction.db – SQLite database (created automatically)
4. templates/ – HTML pages
5. NittanyAuctionDataset_v1/ – CSV dataset files 


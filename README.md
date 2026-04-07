**NittanyAuction Prototype – Authentication System**

**Overview**

This project is a simple prototype of the NittanyAuction system built using Flask and SQLite.
The current implementation focuses on user authentication, including signup, login, and role-based access.

**Features**

- User signup (Bidder or Seller)
- Secure login using hashed passwords (SHA-256)
- Role-based login:
  - Bidder → bidder dashboard
  - Seller → seller dashboard
  - Helpdesk → helpdesk dashboard

**Technologies Used**

- Python (Flask)
- SQLite3
- Pandas (for database population from CSV files)
- HTML (basic templates)

**Database Initialization and Population**

- The database is created and populated automatically using init_db.py.

- Process:

    - Creates tables: Users, Bidders, Sellers, Helpdesk
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

**Requirements / Installation**

Make sure you have Python installed. Then install required packages:

pip install flask pandas

**How to Run the Application**

1. Open terminal in the project folder
2. Run the application:

    - python app.py

3. Open your browser and go to:

    - http://127.0.0.1:5000 (or http://localhost:5000)

**Project Structure**

``` app.py – main Flask application
init_db.py – database creation and population script
auction.db – SQLite database (created automatically)
templates/ – HTML pages
NittanyAuctionDataset_v1/ – CSV dataset files 


from flask import Flask, render_template, request
import sqlite3
import hashlib
from init_db import init_db

DB_NAME = 'auction.db'
init_db()

app = Flask(__name__)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db():
    return sqlite3.connect(DB_NAME);

@app.route('/')
def index():
    return render_template('index.html')

# Add a new patient
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return render_template('signup.html')

if __name__ == '__main__':
    app.run()


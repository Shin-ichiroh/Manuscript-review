import os
from dotenv import load_dotenv
import sys
from datetime import datetime

# Load environment variables and set up system path
load_dotenv()
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from src.core_logic import process_job_posting_url, format_review_for_html
from urllib.parse import urlparse
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key')

import pytz
@app.template_filter('datetime_jst')
def format_datetime_jst(value):
    if value is None:
        return ""
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    jst = pytz.timezone('Asia/Tokyo')
    return value.astimezone(jst).strftime('%Y-%m-%d %H:%M')

# Create the 'instance' folder if it doesn't exist
instance_path = os.path.join(project_root, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Use DATABASE_URL from environment variables if available (e.g. for Azure DB), otherwise fallback to local SQLite
db_uri = os.environ.get('DATABASE_URL')
if not db_uri:
    db_uri = f"sqlite:///{os.path.join(instance_path, 'database.db')}"

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    histories = db.relationship('ReviewHistory', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ReviewHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    job_url = db.Column(db.String(500), nullable=False)
    job_title = db.Column(db.Unicode(200), nullable=True)
    company_name = db.Column(db.Unicode(200), nullable=True) # Added company_name
    review_result_raw = db.Column(db.UnicodeText, nullable=True)
    extracted_info = db.Column(db.UnicodeText, nullable=True) # Added JSON storage
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/review', methods=['POST'])
@login_required
def review():
    job_url = request.form.get('url')
    if not job_url:
        return render_template('results.html', results={"error_message": "Error: No URL provided."}), 400

    results_dict = process_job_posting_url(job_url)

    # Debugging: Check if company_name is in results_dict
    print(f"[app.py debug] results_dict company_name: {results_dict.get('company_name')}")

    # Format extracted data into JSON
    extracted_data = {
        'salary': results_dict.get('salary'),
        'location': results_dict.get('location'),
        'qualifications': results_dict.get('qualifications'),
        'trial_period': results_dict.get('trial_period'),
        'full_text_content': results_dict.get('full_text_content')
    }
    extracted_json = json.dumps(extracted_data, ensure_ascii=False)

    # Safely truncate strings to prevent DB truncation errors
    safe_job_url = job_url[:499] if job_url else job_url
    safe_job_title = results_dict.get('job_title')[:199] if results_dict.get('job_title') else None
    safe_company_name = results_dict.get('company_name')[:199] if results_dict.get('company_name') else None

    # Save to history
    history_entry = ReviewHistory(
        job_url=safe_job_url,
        job_title=safe_job_title,
        company_name=safe_company_name, # Added company_name
        review_result_raw=results_dict.get('review_result_raw'),
        extracted_info=extracted_json,
        author=current_user
    )
    db.session.add(history_entry)
    db.session.commit()

    if results_dict.get("debug_messages"):
        print("\n--- Debug Messages from core_logic (called by app.py) ---")
        for msg in results_dict.get("debug_messages", []):
            print(msg)
        print("--- End of Debug Messages from core_logic ---")

    return render_template('results.html', results=results_dict)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()

    # Base query for all histories, ordered by timestamp
    histories_query = ReviewHistory.query.join(User).order_by(ReviewHistory.timestamp.desc())

    # Apply search filter if query is provided
    if search_query:
        search_pattern = f"%{search_query}%"
        histories_query = histories_query.filter(
            db.or_(
                ReviewHistory.company_name.ilike(search_pattern),
                User.username.ilike(search_pattern)
            )
        )

    histories_pagination = histories_query.paginate(page=page, per_page=10, error_out=False)

    # Format review_result_raw for display and parse JSON
    for history_entry in histories_pagination.items:
        history_entry.formatted_review = format_review_for_html(history_entry.review_result_raw)
        try:
            history_entry.extracted_data = json.loads(history_entry.extracted_info) if history_entry.extracted_info else {}
        except Exception:
            history_entry.extracted_data = {}

    return render_template('history.html', histories=histories_pagination)

with app.app_context():
    db.create_all()
    # Create default admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin')
        admin_user.set_password('gakujo')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

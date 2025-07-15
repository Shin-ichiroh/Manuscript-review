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

# App initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key')

# Create the 'instance' folder if it doesn't exist
instance_path = os.path.join(project_root, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
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
    job_title = db.Column(db.String(200), nullable=True)
    company_name = db.Column(db.String(200), nullable=True) # Added company_name
    review_result_raw = db.Column(db.Text, nullable=True)
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

    # Save to history
    history_entry = ReviewHistory(
        job_url=job_url,
        job_title=results_dict.get('job_title'),
        company_name=results_dict.get('company_name'), # Added company_name
        review_result_raw=results_dict.get('review_result_raw'),
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
    histories_query = ReviewHistory.query.filter_by(author=current_user).order_by(ReviewHistory.timestamp.desc())
    histories_pagination = histories_query.paginate(page=page, per_page=10)

    # Format review_result_raw for display
    for history_entry in histories_pagination.items:
        history_entry.formatted_review = format_review_for_html(history_entry.review_result_raw)

    return render_template('history.html', histories=histories_pagination)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)

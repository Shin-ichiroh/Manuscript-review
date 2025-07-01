import os
from dotenv import load_dotenv

load_dotenv()

import sys
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, request
from src.core_logic import process_job_posting_url

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/review', methods=['POST'])
def review():
    if request.method == 'POST':
        job_url = request.form.get('url')
        if not job_url:
            return render_template('results.html', results={"error_message": "Error: No URL provided."}), 400

        results_dict = process_job_posting_url(job_url)

        if results_dict.get("debug_messages"):
            print("\n--- Debug Messages from core_logic (called by app.py) ---")
            for msg in results_dict.get("debug_messages", []):
                print(msg)
            print("--- End of Debug Messages from core_logic ---")

        return render_template('results.html', results=results_dict)

    return "Invalid request method.", 405

if __name__ == '__main__':
    # Debug mode can be enabled by setting the FLASK_DEBUG environment variable to '1'
    # For example: FLASK_DEBUG=1 python app.py
    # The host and port are typically handled by Gunicorn in production.
    # For local Flask dev server, it will default to localhost:5000.
    # If external access is needed for local dev, user can set FLASK_RUN_HOST=0.0.0.0
    # The sys.path modification is done above to be effective for all imports.
    app.run()

import os # Ensure os is imported for load_dotenv and sys.path logic
from dotenv import load_dotenv # New import

# Load environment variables from .env file if it exists
# This should be one of the first things the app does.
load_dotenv() # New call

# Add project root to sys.path for module resolution
# This helps ensure `from src.module` imports work correctly
# and also that relative imports within the `src` package work when called from app.py.
import sys
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# src_path = os.path.join(project_root, "src") # If src itself needs to be a top-level for some reason
# if src_path not in sys.path:
#    sys.path.insert(0, src_path)


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
    # Note: The sys.path modification is done above, outside the __main__ block,
    # to ensure it's effective for all imports when app.py is run.
    app.run(debug=True, host='0.0.0.0', port=5000)

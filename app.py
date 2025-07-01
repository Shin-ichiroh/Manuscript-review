from flask import Flask, render_template, request
from src.core_logic import process_job_posting_url
import sys
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/review', methods=['POST'])
def review():
    if request.method == 'POST':
        job_url = request.form.get('url')
        if not job_url:
            # Optionally, render an error page or redirect with an error message
            return render_template('results.html', results={"error_message": "Error: No URL provided."}), 400

        results_dict = process_job_posting_url(job_url)

        # Debug messages will be printed to the Flask console.
        if results_dict.get("debug_messages"):
            print("\n--- Debug Messages from core_logic (called by app.py) ---")
            for msg in results_dict.get("debug_messages", []):
                print(msg)
            print("--- End of Debug Messages from core_logic ---")

        # Render the results using the new template
        return render_template('results.html', results=results_dict)

    # Fallback for methods other than POST, though typically not reached if form method is POST
    return "Invalid request method.", 405

if __name__ == '__main__':
    # Add project root to sys.path for module resolution
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Also ensure src is discoverable if it's not directly,
    # though direct `from src.` should work if app.py is in root.
    # src_path = os.path.join(current_dir, "src")
    # if src_path not in sys.path:
    #    sys.path.insert(0, src_path)


    # Restore imports in reviewer.py before running if they were commented out for direct tests
    # This is a manual reminder for the overall development process.
    # Example:
    # try:
    #     from src.reviewer import perform_review
    #     from src.rule_processor import get_mock_vector # Check if this causes issues
    # except ImportError as e:
    #     print(f"Warning: Could not pre-check imports for src.reviewer due to: {e}")
    #     print("Ensure `from .rule_processor import ...` is active in src/reviewer.py if needed by perform_review.")


    app.run(debug=True, host='0.0.0.0', port=5000)

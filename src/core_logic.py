import os

# Use relative imports for modules within the same package (src)
from .scraper import get_dynamic_html_with_selenium, extract_text_from_html, get_site_domain
from .rule_processor import load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
from .reviewer import perform_review

# This function will encapsulate the main processing logic
def process_job_posting_url(job_post_url: str) -> dict:
    """
    Processes a job posting URL through scraping, rulebook loading, and review.
    Returns a dictionary containing all results and debug information.
    """
    results = {
        "job_post_url": job_post_url,
        "site_domain": None,
        "job_title": None,
        "salary": None,
        "location": None,
        "qualifications": None,
        "full_text_content": None,
        "image_ocr_texts": [],
        "rulebook_chunks_count": 0,
        "review_result": None,
        "error_message": None,
        "debug_messages": []
    }

    results["debug_messages"].append(f"--- Starting processing for URL: {job_post_url} ---")

    # --- Phase 1: Data Acquisition ---
    results["debug_messages"].append("--- Phase 1: Data Acquisition (using Selenium) ---")
    site_domain = get_site_domain(job_post_url)
    results["site_domain"] = site_domain
    results["debug_messages"].append(f"Detected site domain: {site_domain}")

    # Note: get_dynamic_html_with_selenium prints its own logs to stdout during execution
    html_content = get_dynamic_html_with_selenium(job_post_url, wait_time=15)

    if not html_content:
        results["error_message"] = "Failed to fetch HTML content using Selenium."
        results["debug_messages"].append(results["error_message"])
        return results

    results["debug_messages"].append("Dynamic HTML content fetched successfully using Selenium.")

    # Note: extract_text_from_html might print warnings (e.g. no selectors found)
    extracted_info = extract_text_from_html(html_content, job_post_url, site_domain)

    results["job_title"] = extracted_info.get('job_title')
    results["salary"] = extracted_info.get('salary')
    results["location"] = extracted_info.get('location')
    results["qualifications"] = extracted_info.get('qualifications')
    results["full_text_content"] = extracted_info.get('full_text')
    results["image_ocr_texts"] = extracted_info.get('image_ocr_texts', [])

    results["debug_messages"].append("[core_logic] Extracted Info Check:")
    results["debug_messages"].append(f"[core_logic]   Job Title: {results['job_title']}")
    results["debug_messages"].append(f"[core_logic]   Salary: {results['salary']}")
    results["debug_messages"].append(f"[core_logic]   Location: {results['location']}")
    results["debug_messages"].append(f"[core_logic]   Qualifications: {results['qualifications']}")
    # results["debug_messages"].append(f"[core_logic]   Full Text Snippet: {results['full_text_content'][:200] if results['full_text_content'] else 'N/A'}...")


    if not results["full_text_content"] and not any([results["job_title"], results["salary"], results["location"], results["qualifications"]]):
        results["error_message"] = "No text content (full_text or specific fields) was extracted from the URL."
        results["debug_messages"].append(results["error_message"])
        # Potentially return early if no text at all, or use a placeholder for review
        # For now, review will proceed with whatever was extracted (even if all N/A)

    # --- Phase 2: AI Review Logic ---
    results["debug_messages"].append("\n--- Phase 2: AI Review Logic ---")

    # Assuming rulebook.md is in the project root, accessible from src via ../
    # load_rulebook itself handles path logic based on its own file location.
    rulebook_content = load_rulebook("rulebook.md")

    if rulebook_content.startswith("Error:") : # Check if load_rulebook returned an error string
        results["error_message"] = f"Failed to load rulebook: {rulebook_content}"
        results["debug_messages"].append(results["error_message"])
        rulebook_vector_db = [] # Ensure it's an empty list for perform_review
    else:
        results["debug_messages"].append("Rulebook loaded successfully.")
        parsed_chunks = parse_rulebook_to_chunks(rulebook_content)
        rulebook_vector_db = add_mock_vectors_to_chunks(parsed_chunks)
        results["rulebook_chunks_count"] = len(rulebook_vector_db)
        results["debug_messages"].append(f"Rulebook processed into {results['rulebook_chunks_count']} vectorized chunks.")

    results["debug_messages"].append("\nPerforming review on the job post data...")

    # perform_review handles Azure credential checks and LLM calls (real or simulated)
    # It also prints its own internal logging to stdout (e.g., API call attempts, fallback messages)
    review_output_from_reviewer = perform_review(
        job_post_url=job_post_url,
        job_title=results["job_title"],
        salary=results["salary"],
        location=results["location"],
        qualifications=results["qualifications"],
        full_text_content=results["full_text_content"], # This is scraper's 'full_text'
        rulebook_vector_db=rulebook_vector_db
    )
    results["review_result"] = review_output_from_reviewer

    results["debug_messages"].append("--- Processing Finished ---")
    return results

if __name__ == '__main__':
    print("--- Testing core_logic.py: process_job_posting_url ---")

    # Test with a default URL.
    # The Gakujo URL is complex and takes time for Selenium. For a quicker test,
    # one might use "http://example.com" and expect fewer specific fields.
    # However, for consistency with main.py's default, using Gakujo.
    test_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"
    # test_url = "https://re-katsu.jp/career/company/recruit/57021/" # Alternative for quicker test if needed

    print(f"Processing URL: {test_url}")

    # Ensure rule_processor imports are available in reviewer.py for RAG vector generation
    # For direct execution of core_logic.py, if reviewer.py's .rule_processor import is commented out,
    # RAG within perform_review will use a placeholder vector. This is acceptable for this structural test.
    # The `from .rule_processor import ...` in reviewer.py is commented for its direct tests.
    # When main.py calls functions from src.reviewer, Python's import mechanism handles it.

    # For this direct test of core_logic.py, we need to ensure its own imports work.
    # The `from .scraper` etc. at the top of core_logic.py will cause an ImportError if run as `python src/core_logic.py`.
    # To make it runnable directly for this test, we would need to adjust python path or use a different execution method.
    # The subtask asks for an if __name__ == "__main__" block here, implying direct execution.
    # I will assume the environment or execution method (e.g. python -m src.core_logic from root) handles the relative imports.
    # If not, this test block will fail on imports, but the function structure is the primary goal.

    # Let's assume for this test that the imports might fail if not run as a module.
    # The primary goal is the function structure, which `main.py` will test as a module.
    # For a simple syntax check and flow:
    try:
        results = process_job_posting_url(test_url)
        print("\n--- Results from process_job_posting_url ---")
        for key, value in results.items():
            if key == "debug_messages":
                print(f"\n{key}:")
                for msg in value:
                    print(f"  {msg}")
            elif key == "image_ocr_texts":
                print(f"\n{key} (count): {len(value)}")
            else:
                # Truncate long text fields for display
                display_value = str(value)
                if isinstance(value, str) and len(value) > 300:
                    display_value = value[:300] + "..."
                print(f"{key}: {display_value}")
    except ImportError as e:
        print(f"ImportError during core_logic.py self-test: {e}")
        print("This is expected if running `python src/core_logic.py` directly due to relative imports.")
        print("The function process_job_posting_url is structured for import by main.py.")
        print("To test core_logic.py directly, run `python -m src.core_logic` from the project root.")
    except Exception as e:
        print(f"An unexpected error occurred during core_logic.py self-test: {e}")

    print("\n--- End of core_logic.py test ---")

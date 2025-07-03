import os
import re # For formatting review output

# Use relative imports for modules within the same package (src)
from .scraper import get_static_html_with_requests, extract_text_from_html, get_site_domain
from .rule_processor import load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
from .reviewer import perform_review

# Helper function to format review text for HTML display
def format_review_for_html(review_text: str | None) -> str:
    if not review_text:
        return "<p>審査結果なし</p>"
    
    # Convert markdown-like bold to <strong> tags
    html_output = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', review_text)
    
    lines = html_output.splitlines()
    processed_html_parts = []
    first_item_processed = False

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("・<strong>問題点がある箇所</strong>"):
            if first_item_processed: # 2つ目以降の「問題点がある箇所」の前に<hr>を挿入
                processed_html_parts.append("<hr style=\"margin-top: 1em; margin-bottom: 1em;\">")
            processed_html_parts.append(f'<p style="margin-bottom: 0.25em; margin-left: 1.5em; text-indent: -1.5em;">・ {stripped_line[1:].strip()}</p>')
            first_item_processed = True
        elif stripped_line.startswith("・"):
             # Remove the "・" and style as a list item (or paragraph with indent)
            processed_html_parts.append(f'<p style="margin-bottom: 0.25em; margin-left: 1.5em; text-indent: -1.5em;">・ {stripped_line[1:].strip()}</p>')
        elif stripped_line: # Non-empty lines also get a paragraph
             processed_html_parts.append(f"<p style=\"margin-bottom: 0.5em;\">{stripped_line}</p>")
        # else: # Avoid adding <br> for completely empty lines by default

    final_html = "".join(processed_html_parts)
    return final_html if final_html.strip() else "<p>審査結果なし</p>"


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
        "review_result": None, # This will store the HTML formatted result
        "review_result_raw": None, # To store the original raw text from AI
        "error_message": None,
        "debug_messages": []
    }

    results["debug_messages"].append(f"--- Starting processing for URL: {job_post_url} ---")

    # --- Phase 1: Data Acquisition ---
    results["debug_messages"].append("--- Phase 1: Data Acquisition (using Requests) ---")
    site_domain = get_site_domain(job_post_url)
    results["site_domain"] = site_domain
    results["debug_messages"].append(f"Detected site domain: {site_domain}")

    html_content = get_static_html_with_requests(job_post_url)

    if not html_content:
        results["error_message"] = "Failed to fetch HTML content using Requests."
        results["debug_messages"].append(results["error_message"])
        return results

    results["debug_messages"].append("Static HTML content fetched successfully using Requests.")

    extracted_info = extract_text_from_html(html_content, job_post_url, site_domain)

    results["job_title"] = extracted_info.get('job_title')
    results["salary"] = extracted_info.get('salary')
    results["location"] = extracted_info.get('location')
    results["qualifications"] = extracted_info.get('qualifications')
    results["full_text_content"] = extracted_info.get('full_text')
    results["image_ocr_texts"] = extracted_info.get('image_ocr_texts', [])

    results["debug_messages"].append("[core_logic] Extracted Info Check:")
    results["debug_messages"].append(f"[core_logic]   Job Title: {results['job_title']}")
    # Add other fields to debug log if needed

    if not results["full_text_content"] and not any([results["job_title"], results["salary"], results["location"], results["qualifications"]]):
        results["error_message"] = "No text content (full_text or specific fields) was extracted from the URL."
        results["debug_messages"].append(results["error_message"])
    
    # --- Phase 2: AI Review Logic ---
    results["debug_messages"].append("\n--- Phase 2: AI Review Logic ---")

    rulebook_content = load_rulebook("rulebook.md")

    if rulebook_content.startswith("Error:") : 
        results["error_message"] = f"Failed to load rulebook: {rulebook_content}"
        results["debug_messages"].append(results["error_message"])
        rulebook_vector_db = [] 
    else:
        results["debug_messages"].append("Rulebook loaded successfully.")
        parsed_chunks = parse_rulebook_to_chunks(rulebook_content)
        rulebook_vector_db = add_mock_vectors_to_chunks(parsed_chunks)
        results["rulebook_chunks_count"] = len(rulebook_vector_db)
        results["debug_messages"].append(f"Rulebook processed into {results['rulebook_chunks_count']} vectorized chunks.")

    results["debug_messages"].append("\nPerforming review on the job post data...")
    
    review_output_from_reviewer = perform_review(
        job_post_url=job_post_url,
        job_title=results["job_title"],
        salary=results["salary"],
        location=results["location"],
        qualifications=results["qualifications"],
        full_text_content=results["full_text_content"],
        rulebook_vector_db=rulebook_vector_db
    )
    results["review_result_raw"] = review_output_from_reviewer 
    results["review_result"] = format_review_for_html(review_output_from_reviewer) # Store HTML formatted

    results["debug_messages"].append("--- Processing Finished ---")
    return results

if __name__ == '__main__':
    print("--- Testing core_logic.py: process_job_posting_url ---")
    test_url = "https://www.gakujo.ne.jp/campus/company/employ/12138/"
    print(f"Processing URL: {test_url}")
    try:
        results = process_job_posting_url(test_url)
        print("\n--- Results from process_job_posting_url ---")
        for key, value in results.items():
            if key == "debug_messages":
                print(f"\n{key}:")
                for msg in value:
                    print(f"  {msg}")
            elif key == "review_result": # Print the HTML formatted one for review
                print(f"\n{key} (HTML formatted for display):\n{value}")
            elif key == "review_result_raw":
                 print(f"\n{key} (Raw AI output):\n{value}")
            elif key == "image_ocr_texts":
                print(f"\n{key} (count): {len(value)}")
                if value: print(f"  First OCR: {value[0]}")
            else:
                display_value = str(value)
                if isinstance(value, str) and len(value) > 150 and key != "full_text_content": # Shorten general strings
                    display_value = value[:150] + "..."
                elif key == "full_text_content" and isinstance(value, str) and len(value) > 300: # Shorten full_text differently
                     display_value = value[:300] + "..."
                print(f"{key}: {display_value}")
    except ImportError as e:
        print(f"ImportError during core_logic.py self-test: {e}")
        print("This is expected if running `python src/core_logic.py` directly due to relative imports.")
        print("To test core_logic.py directly, run `python -m src.core_logic` from the project root.")
    except Exception as e:
        print(f"An unexpected error occurred during core_logic.py self-test: {e}")

    print("\n--- End of core_logic.py test ---")
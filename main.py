import argparse # For command-line argument parsing

# Phase 1 imports
from src.scraper import get_dynamic_html_with_selenium, extract_text_from_html

# Phase 2 imports
from src.rule_processor import load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
from src.reviewer import perform_review

if __name__ == "__main__":
    # NOTE: This script now uses Selenium for web scraping dynamic content.
    # Ensure you have a compatible web browser (e.g., Chrome) and its
    # corresponding WebDriver (e.g., ChromeDriver) installed and accessible.
    # `webdriver-manager` (in requirements.txt) attempts to handle ChromeDriver automatically.

    parser = argparse.ArgumentParser(description="Analyze a job posting URL for potential issues.")
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27", # Default URL
        help="URL of the job posting to analyze."
    )
    args = parser.parse_args()
    sample_url = args.url  # Use the URL from command-line or default

    print(f"--- Starting Full Workflow Integration Test (URL: {sample_url}) ---")

    # --- Phase 1: Data Acquisition ---
    print("\n--- Phase 1: Data Acquisition (using Selenium) ---")

    job_post_url = sample_url
    job_title = None
    salary = None
    location = None
    qualifications = None
    full_text_content = None

    print(f"Fetching dynamic HTML from: {job_post_url}") # Use job_post_url which is from sample_url
    html_content = get_dynamic_html_with_selenium(job_post_url, wait_time=15)

    if html_content:
        print("Dynamic HTML content fetched successfully using Selenium.")

        extracted_info = extract_text_from_html(html_content, job_post_url) # Pass job_post_url as base_url

        print("\n[DEBUG in main.py] Extracted Info Dictionary Check:")
        job_title = extracted_info.get('job_title')
        salary = extracted_info.get('salary')
        location = extracted_info.get('location')
        qualifications = extracted_info.get('qualifications')
        full_text_content = extracted_info.get('full_text')

        print(f"[DEBUG in main.py]   Raw job_title: {job_title}")
        print(f"[DEBUG in main.py]   Raw salary: {salary}")
        print(f"[DEBUG in main.py]   Raw location: {location}")
        print(f"[DEBUG in main.py]   Raw qualifications: {qualifications}")

        print("\nText extracted from dynamic HTML (including mock OCR).")

        if full_text_content:
            specific_fields_extracted = any([job_title, salary, location, qualifications])
            if not specific_fields_extracted:
                if salary is None and location is None and qualifications is None:
                    print("\n  Note from main.py: Core specific fields (salary, location, qualifications) were NOT found by the parser.")
                else:
                    print("\n  Note from main.py: Some specific fields WERE found by the parser (job_title might be a fallback).")
            else:
                print("\n  Note from main.py: All specific fields (job title, salary, etc.) WERE found by the parser according to 'any' check including job_title.")
            print(f"\nUsing full_text_content (first 300 chars for prompt RAG base):\n{full_text_content[:300]}...")
        else:
            print("No 'full_text' was extracted from the dynamic HTML.")
            full_text_content = "求人情報の内容が取得できませんでした（Selenium HTMLは取得成功、テキスト抽出失敗）。これはプレースホルダーのテキストです。"
            print("Using placeholder full_text_content for Phase 2.")
            job_title, salary, location, qualifications = "N/A", "N/A", "N/A", "N/A"

    else:
        print(f"Failed to fetch dynamic HTML content from {job_post_url} using Selenium.")
        full_text_content = "求人情報URLからのHTML取得に失敗しました（Selenium）。これはプレースホルダーのテキストです。"
        print("Using placeholder full_text_content for Phase 2.")
        job_title, salary, location, qualifications = "N/A", "N/A", "N/A", "N/A"


    # --- Phase 2: AI Review Logic ---
    print("\n--- Phase 2: AI Review Logic ---")

    print("Loading rulebook...")
    rulebook_content = load_rulebook("rulebook.md")

    if rulebook_content.startswith("Error:") or rulebook_content.startswith("An unexpected error occurred:"):
        print(f"Failed to load rulebook: {rulebook_content}")
        print("Cannot proceed with review without rulebook.")
    else:
        print("Rulebook loaded successfully.")
        parsed_chunks = parse_rulebook_to_chunks(rulebook_content)
        rulebook_vector_db = add_mock_vectors_to_chunks(parsed_chunks)
        print(f"Rulebook processed into {len(rulebook_vector_db)} vectorized chunks.")

        if not full_text_content:
             print("Full text content is empty, review might not be meaningful but proceeding with a default empty text...")
             full_text_content = "内容が空の求人原稿です。"
             job_title, salary, location, qualifications = "N/A", "N/A", "N/A", "N/A"


        print("\nPerforming review on the job post data...")
        review_result = perform_review(
            job_post_url=job_post_url, # This is the URL from argparse or default
            job_title=job_title,
            salary=salary,
            location=location,
            qualifications=qualifications,
            full_text_content=full_text_content,
            rulebook_vector_db=rulebook_vector_db
        )

        print("\n--- FINAL SIMULATED REVIEW RESULT (using structured data) ---")
        print(review_result)

    print(f"\n--- Full Workflow Integration Test (URL: {job_post_url}) Finished ---")

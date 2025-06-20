# Phase 1 imports
from src.scraper import get_dynamic_html_with_selenium, extract_text_from_html, integrate_all_text

# Phase 2 imports
from src.rule_processor import load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
from src.reviewer import perform_review

if __name__ == "__main__":
    # NOTE: This script now uses Selenium for web scraping dynamic content.
    # Ensure you have a compatible web browser (e.g., Chrome) and its
    # corresponding WebDriver (e.g., ChromeDriver) installed and accessible.
    # `webdriver-manager` (in requirements.txt) attempts to handle ChromeDriver automatically.

    print("--- Starting Full Workflow Integration Test (with Selenium) ---")

    # --- Phase 1: Data Acquisition ---
    print("\n--- Phase 1: Data Acquisition (using Selenium) ---")
    sample_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"
    job_post_text = "" # Initialize

    print(f"Fetching dynamic HTML from: {sample_url}")
    html_content = get_dynamic_html_with_selenium(sample_url, wait_time=15)

    if html_content:
        print("Dynamic HTML content fetched successfully using Selenium.")

        # Remove/comment out saving of debug_main_fetched_page.html
        # try:
        #     with open("debug_main_fetched_page.html", "w", encoding="utf-8") as f:
        #         f.write(html_content)
        #     print("Successfully saved fetched HTML to debug_main_fetched_page.html")
        # except Exception as e:
        #     print(f"Error saving fetched HTML to debug_main_fetched_page.html: {e}")

        extracted_info = extract_text_from_html(html_content, sample_url)

        # Add detailed logging for the extracted_info dictionary
        print("\n[DEBUG in main.py] Extracted Info Dictionary Check:")
        print(f"[DEBUG in main.py]   Raw job_title: {extracted_info.get('job_title')}")
        print(f"[DEBUG in main.py]   Raw salary: {extracted_info.get('salary')}")
        print(f"[DEBUG in main.py]   Raw location: {extracted_info.get('location')}")
        print(f"[DEBUG in main.py]   Raw qualifications: {extracted_info.get('qualifications')}")
        # print(f"[DEBUG in main.py] All keys in extracted_info: {list(extracted_info.keys())}")


        print("\nText extracted from dynamic HTML (including mock OCR).") # Original print statement

        job_post_text = integrate_all_text(extracted_info)
        if job_post_text:
            specific_fields_extracted = any([
                extracted_info.get('job_title'),
                extracted_info.get('salary'),
                extracted_info.get('location'),
                extracted_info.get('qualifications')
            ])
            if not specific_fields_extracted:
                print("\n  Note from main.py: Specific fields (job title, salary, etc.) were NOT found by the current parser according to 'any' check.")
                print("  The 'full_text' from the page will be used for the review phase.")
            else:
                print("\n  Note from main.py: Specific fields (job title, salary, etc.) WERE found by the current parser according to 'any' check.")


            print(f"\nIntegrated job post text (first 300 chars):\n{job_post_text[:300]}...")

        else:
            print("No text content (HTML or OCR) was extracted from the dynamic HTML.")
            job_post_text = "求人情報の内容が取得できませんでした（Selenium HTMLは取得成功、テキスト抽出失敗）。これはプレースホルダーのテキストです。"
            print("Using placeholder job post text for Phase 2.")

    else:
        print(f"Failed to fetch dynamic HTML content from {sample_url} using Selenium.")
        job_post_text = "求人情報URLからのHTML取得に失敗しました（Selenium）。これはプレースホルダーのテキストです。"
        print("Using placeholder job post text for Phase 2.")

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

        if not job_post_text:
             print("Job post text is empty, review might not be meaningful but proceeding with a default empty text...")
             job_post_text = "内容が空の求人原稿です。"

        print("\nPerforming review on the job post text...")
        review_result = perform_review(job_post_text, rulebook_vector_db)

        print("\n--- FINAL SIMULATED REVIEW RESULT (using Selenium-fetched data) ---")
        print(review_result)

    print("\n--- Full Workflow Integration Test (with Selenium) Finished ---")

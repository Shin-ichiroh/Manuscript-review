# Phase 1 imports
from src.scraper import get_html_content, extract_text_from_html, integrate_all_text

# Phase 2 imports
from src.rule_processor import load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
from src.reviewer import perform_review

if __name__ == "__main__":
    print("--- Starting Full Workflow Integration Test ---")

    # --- Phase 1: Data Acquisition ---
    print("\n--- Phase 1: Data Acquisition ---")
    # Using the target URL, but example.com can be used for quicker, simpler HTML
    # sample_url = "http://example.com"
    sample_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"
    job_post_text = "" # Initialize

    print(f"Fetching HTML from: {sample_url}")
    # Define standard headers, as used in scraper.py
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    html_content = get_html_content(sample_url, headers=headers)

    if html_content:
        print("HTML content fetched successfully.")
        # Pass sample_url as base_url for resolving relative image paths in scraper
        extracted_info = extract_text_from_html(html_content, sample_url)
        print("Text extracted from HTML (including mock OCR).")

        job_post_text = integrate_all_text(extracted_info)
        if job_post_text:
            print(f"Integrated job post text (first 300 chars):\n{job_post_text[:300]}...")
        else:
            print("No text content (HTML or OCR) was extracted from the URL.")
            # Provide a default placeholder if critical for Phase 2 and no text was extracted
            job_post_text = "求人情報の内容が取得できませんでした。これはプレースホルダーのテキストです。"
            print("Using placeholder job post text for Phase 2.")

    else:
        print(f"Failed to fetch HTML content from {sample_url}.")
        # Provide a default placeholder if HTML fetching fails
        job_post_text = "求人情報URLからのHTML取得に失敗しました。これはプレースホルダーのテキストです。"
        print("Using placeholder job post text for Phase 2.")

    # --- Phase 2: AI Review Logic ---
    print("\n--- Phase 2: AI Review Logic ---")

    # Load rulebook (rulebook.md should be in the same directory as main.py)
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
            print("Job post text is empty, review might not be meaningful but proceeding...")
            # If job_post_text is still empty here, it means integrate_all_text returned empty
            # and the placeholder from HTML fetch failure wasn't triggered,
            # or the placeholder from successful fetch but empty integration was used.
            # Ensure it has some content for perform_review.
            job_post_text = "内容が空の求人原稿です。"


        print("\nPerforming review on the job post text...")
        review_result = perform_review(job_post_text, rulebook_vector_db)

        print("\n--- FINAL SIMULATED REVIEW RESULT ---")
        print(review_result)

    print("\n--- Full Workflow Integration Test Finished ---")

import requests
from bs4 import BeautifulSoup
import urllib.parse

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager # To manage ChromeDriver
from selenium.webdriver.chrome.options import Options
import time
import os

def get_html_content(url: str, headers: dict | None = None) -> str | None:
    """Fetches HTML content from a URL using requests (static fetch).

    Args:
        url: The URL to fetch content from.
        headers: Optional dictionary of HTTP Headers to send with the request.

    Returns:
        The HTML content as a string if successful, otherwise None.
    """
    print(f"Attempting to fetch static HTML using requests for URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print("Static HTML fetched successfully with requests.")
        return response.text
    except requests.exceptions.Timeout:
        print(f"Error: The request to {url} timed out (requests).")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error occurred while fetching {url} (requests): {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url} (requests): {e}")
        return None

def get_dynamic_html_with_selenium(url: str, wait_time: int = 10) -> str | None:
    """
    Fetches HTML content from a URL after JavaScript rendering using Selenium.
    """
    driver = None
    try:
        print("Attempting to fetch HTML using Selenium WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

        try:
            print("Initializing ChromeDriver using ChromeDriverManager...")
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
            print("ChromeDriver initialized successfully with webdriver_manager.")
        except Exception as e:
            print(f"Failed to initialize ChromeDriver with webdriver_manager: {e}")
            print("Ensure Chrome browser is installed. As a fallback, if ChromeDriver is in PATH, trying basic initialization...")
            driver = webdriver.Chrome(options=chrome_options)
            print("ChromeDriver initialized using basic setup (assuming it's in PATH).")

        print(f"Navigating to URL: {url}")
        driver.get(url)
        print(f"Waiting for {wait_time} seconds for dynamic content to load...")
        time.sleep(wait_time)

        page_source = driver.page_source
        print("Successfully fetched dynamic HTML page source with Selenium.")
        return page_source
    except Exception as e:
        print(f"An error occurred during Selenium HTML fetching: {e}")
        print("Ensure Chrome browser and ChromeDriver are correctly installed and accessible in your system PATH, or that `webdriver_manager` can download ChromeDriver.")
        return None
    finally:
        if driver:
            print("Quitting Selenium WebDriver.")
            driver.quit()


def extract_image_urls(html_content: str, base_url: str) -> list[str]:
    """Extracts all absolute image URLs from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls = []
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if src:
            absolute_url = urllib.parse.urljoin(base_url, src)
            image_urls.append(absolute_url)
    return image_urls

def perform_ocr_on_image(image_url: str) -> str:
    """Simulates performing OCR on an image."""
    print(f"Simulating OCR for image: {image_url}")
    return f"Mock OCR text for {image_url}"

def extract_text_from_html(html_content: str, base_url: str) -> dict[str, any]:
    """
    Extracts specific job details, all available text, and simulated OCR text from images
    using CSS selectors derived from analysis of the target site's dynamic HTML.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    data: dict[str, any] = {
        "job_title": None,
        "salary": None,
        "location": None,
        "qualifications": None,
        "full_text": None,
        "image_ocr_texts": [],
    }

    # Job Title (採用職種) - Note the trailing space in '採用職種 '
    job_title_tag = soup.select_one("dl.sep-text dt:-soup-contains('採用職種 ') + dd div span")
    data['job_title'] = job_title_tag.get_text(separator='\n', strip=True) if job_title_tag else None

    # Salary (給与)
    salary_tag = soup.select_one("dl.sep-text dt:-soup-contains('給与') + dd div span")
    data['salary'] = salary_tag.get_text(separator='\n', strip=True) if salary_tag else None

    # Location (勤務地) - This selector might match multiple <dt>s if "勤務地" appears under different sections.
    # For this specific page, "募集概要" section's 勤務地 is targeted by this general selector.
    # If more specificity is needed (e.g. to distinguish from a company HQ location if also listed similarly),
    # a more complex selector chaining from the section header (e.g. h3:-soup-contains('募集概要') ~ dl.sep-text ...) would be needed.
    location_tag = soup.select_one("dl.sep-text dt:-soup-contains('勤務地') + dd div span")
    data['location'] = location_tag.get_text(separator='\n', strip=True) if location_tag else None

    # Qualifications (応募資格)
    qualifications_tag = soup.select_one("dl.sep-text dt:-soup-contains('応募資格') + dd div span")
    data['qualifications'] = qualifications_tag.get_text(separator='\n', strip=True) if qualifications_tag else None

    # Fallback for Job Title if the specific one isn't found (e.g. general page title)
    if not data['job_title']:
        # This was the original fallback, might be useful if the above is too specific or fails
        title_tag_h1_company = soup.find('h1', class_='h1-company-name_inner')
        if title_tag_h1_company:
            data['job_title'] = title_tag_h1_company.get_text(strip=True)
        elif soup.find('h1'): # Generic H1
             data['job_title'] = soup.find('h1').get_text(strip=True)


    data['full_text'] = soup.get_text(separator=' ', strip=True)

    image_urls = extract_image_urls(html_content, base_url)
    for img_url in image_urls:
        ocr_text = perform_ocr_on_image(img_url)
        data['image_ocr_texts'].append(ocr_text)

    return data

def integrate_all_text(extracted_data: dict) -> str:
    """
    Integrates full_text and image_ocr_texts into a single string.
    """
    text_parts = []
    full_text = extracted_data.get('full_text')
    if full_text:
        text_parts.append(full_text)
    image_ocr_texts = extracted_data.get('image_ocr_texts')
    if image_ocr_texts:
        for ocr_text in image_ocr_texts:
            if ocr_text:
                text_parts.append(ocr_text)
    return "\n\n".join(text_parts)

if __name__ == "__main__":
    print("--- Testing Static HTML Fetch (requests) ---")
    static_url = "http://example.com"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    static_html_content = get_html_content(static_url, headers=headers)
    if static_html_content:
        print(f"Static HTML from {static_url} fetched.\n")
    else:
        print(f"Failed to fetch static HTML from {static_url}\n")

    print("\n--- Testing Selenium-based Dynamic HTML Fetch & Extraction (and saving HTML) ---")
    dynamic_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"

    print(f"Fetching dynamic HTML from: {dynamic_url}")
    dynamic_html = get_dynamic_html_with_selenium(dynamic_url, wait_time=15)

    if dynamic_html:
        print(f"Successfully fetched dynamic HTML (first 500 chars):\n{dynamic_html[:500]}")

        # Temporarily saved HTML, now removing/commenting out this part as per cleanup
        # output_file_path = "temp_dynamic_page.html"
        # try:
        #     with open(output_file_path, "w", encoding="utf-8") as f:
        #         f.write(dynamic_html)
        #     print(f"Successfully saved dynamic HTML to {output_file_path}")
        # except Exception as e:
        #     print(f"Error saving dynamic HTML to file '{output_file_path}': {e}")

        print("\nDynamic HTML fetched successfully. Now extracting specific fields...")
        extracted_info = extract_text_from_html(dynamic_html, dynamic_url)

        print("\n--- Extracted Fields from Dynamic HTML ---")
        print(f"  Job Title: {extracted_info.get('job_title')}")
        print(f"  Salary: {extracted_info.get('salary')}")
        print(f"  Location: {extracted_info.get('location')}")
        print(f"  Qualifications: {extracted_info.get('qualifications')}")

        specific_fields_found = any([
            extracted_info.get('job_title'),
            extracted_info.get('salary'),
            extracted_info.get('location'),
            extracted_info.get('qualifications')
        ])

        if not specific_fields_found:
            print("\n  Note: None of the specific job details (job title, salary, location, qualifications) were found even with dynamic HTML.")
            print("  This might indicate the selectors in `extract_text_from_html` need refinement for this specific page structure,")
            print("  or the content is structured in a way not caught by current simple selectors (e.g., inside iframes not directly accessed).")

        print(f"\n  Full Text (first 200 chars): {extracted_info.get('full_text', '')[:200]}...")

        if extracted_info.get('image_ocr_texts'):
            print(f"  Image OCR Texts (count): {len(extracted_info.get('image_ocr_texts'))}")
        else:
            print("  Image OCR Texts: No images processed or found.")

        final_text = integrate_all_text(extracted_info)
        if final_text:
            print(f"\nIntegrated final text length: {len(final_text)} characters.")
        else:
            print("\nNo text content was integrated from dynamic HTML.")

    else:
        print("Failed to fetch dynamic HTML using Selenium.")

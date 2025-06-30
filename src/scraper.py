import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse # Added for domain parsing

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os

# Global dictionary for site-specific selectors
SITE_SELECTORS = {
    "gakujo.ne.jp": { # Key changed to match output of get_site_domain()
        "job_title": "dl.sep-text dt:-soup-contains('採用職種 ') + dd div span",
        "salary": "dl.sep-text dt:-soup-contains('給与') + dd div span",
        "location": "dl.sep-text dt:-soup-contains('勤務地') + dd div span",
        "qualifications": "dl.sep-text dt:-soup-contains('応募資格') + dd div span",
        "full_text_area": None # For gakujo, we used soup.get_text() on the whole doc effectively
    },
    "re-katsu.jp": {
        "job_title": "span#lblWantedJobType", # Specific title for the role
        "salary": "span#trSalary",      # This span contains <h3> and <p> with details. get_text() will grab all.
        "location": "span#lblWorklocation",
        "qualifications": "span#lblTalentedpeople", # This is for "求める人材"
        "full_text_area": "section#onRec" # Main content area for the job posting
    }
    # Add more site configurations here
}

def get_site_domain(url: str) -> str:
    """Extracts the domain (e.g., 'example.com') from a URL."""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def get_html_content(url: str, headers: dict | None = None) -> str | None:
    """Fetches HTML content from a URL using requests (static fetch)."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception:
        return None

def get_dynamic_html_with_selenium(url: str, wait_time: int = 10) -> str | None:
    """Fetches HTML content from a URL after JavaScript rendering using Selenium."""
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

        try:
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        except Exception:
            driver = webdriver.Chrome(options=chrome_options)

        print(f"Navigating to URL: {url}")
        driver.get(url)
        print(f"Waiting for {wait_time} seconds for dynamic content to load...")
        time.sleep(wait_time)
        page_source = driver.page_source
        print("Successfully fetched dynamic HTML page source with Selenium.")
        return page_source
    except Exception as e:
        print(f"An error occurred during Selenium HTML fetching: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def extract_image_urls(html_content: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls = []
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if src:
            absolute_url = urllib.parse.urljoin(base_url, src)
            image_urls.append(absolute_url)
    return image_urls

def perform_ocr_on_image(image_url: str) -> str:
    return f"Mock OCR text for {image_url}"

def extract_text_from_html(html_content: str, base_url: str, site_domain: str) -> dict[str, any]:
    """
    Extracts specific job details, full text, and image OCR based on site-specific selectors.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    data: dict[str, any] = {
        "job_title": None, "salary": None, "location": None, "qualifications": None,
        "full_text": None, "image_ocr_texts": [],
    }

    selectors_for_site = SITE_SELECTORS.get(site_domain)

    if not selectors_for_site:
        print(f"[extract_text_from_html] WARNING: No specific selectors found for domain '{site_domain}'. Falling back to generic full_text and image extraction.")
        data['full_text'] = soup.get_text(separator='\n', strip=True)
    else:
        # Extract specific fields using site-specific selectors
        job_title_selector = selectors_for_site.get("job_title")
        if job_title_selector:
            job_title_tag = soup.select_one(job_title_selector)
            data['job_title'] = job_title_tag.get_text(separator='\n', strip=True) if job_title_tag else None

        salary_selector = selectors_for_site.get("salary")
        if salary_selector:
            salary_tag = soup.select_one(salary_selector)
            # For salary, location, qualifications on re-katsu, the selector targets a span
            # which itself contains an <h3> (the label) and then <p> (the value).
            # We want to exclude the <h3> from the get_text().
            if salary_tag:
                # Remove the h3 tag before getting text if it's the re-katsu structure
                if site_domain == "re-katsu.jp" and salary_tag.find("h3"):
                    salary_tag.find("h3").decompose()
                data['salary'] = salary_tag.get_text(separator='\n', strip=True)
            else:
                data['salary'] = None

        location_selector = selectors_for_site.get("location")
        if location_selector:
            location_tag = soup.select_one(location_selector)
            if location_tag:
                if site_domain == "re-katsu.jp" and location_tag.find("h3"): # Assuming similar structure
                    location_tag.find("h3").decompose()
                data['location'] = location_tag.get_text(separator='\n', strip=True)
            else:
                data['location'] = None

        qualifications_selector = selectors_for_site.get("qualifications")
        if qualifications_selector:
            qualifications_tag = soup.select_one(qualifications_selector)
            if qualifications_tag:
                if site_domain == "re-katsu.jp" and qualifications_tag.find("h3"): # Assuming similar structure
                    qualifications_tag.find("h3").decompose()
                data['qualifications'] = qualifications_tag.get_text(separator='\n', strip=True)
            else:
                data['qualifications'] = None

        # Fallback for Job Title if specific selector fails
        if not data['job_title']:
            if site_domain == "www.gakujo.ne.jp":
                title_tag_h1_company = soup.find('h1', class_='h1-company-name_inner')
                if title_tag_h1_company: data['job_title'] = title_tag_h1_company.get_text(strip=True)
            # General H1 fallback for any site if still no title (could be re-katsu's main title)
            if not data['job_title']:
                 generic_h1 = soup.find('h1') # This might catch re-katsu's <span class="head-catchcopy"> inside <h1>
                 if generic_h1:
                     # For re-katsu, the h1 contains spans, we want the text of the specific one if possible
                     if site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                         data['job_title'] = generic_h1.find("span", class_="head-catchcopy").get_text(separator='\n', strip=True)
                     else:
                         data['job_title'] = generic_h1.get_text(separator='\n', strip=True)


        # Full text extraction using specific area selector or fallback
        full_text_area_selector = selectors_for_site.get("full_text_area")
        full_text_content_area = None
        if full_text_area_selector:
            full_text_content_area = soup.select_one(full_text_area_selector)

        if full_text_content_area:
            data['full_text'] = full_text_content_area.get_text(separator='\n', strip=True)
        else:
            data['full_text'] = soup.get_text(separator='\n', strip=True)

    # Image extraction (common for all sites)
    image_urls = extract_image_urls(html_content, base_url)
    for img_url in image_urls:
        data['image_ocr_texts'].append(perform_ocr_on_image(img_url))

    return data

def integrate_all_text(extracted_data: dict) -> str:
    text_parts = []
    full_text = extracted_data.get('full_text')
    if full_text: text_parts.append(full_text)
    image_ocr_texts = extracted_data.get('image_ocr_texts')
    if image_ocr_texts:
        for ocr_text in image_ocr_texts:
            if ocr_text: text_parts.append(ocr_text)
    return "\n\n".join(text_parts)

if __name__ == "__main__":
    print("\n--- Testing Scraper with Multi-Site Selector Logic ---")
    dynamic_url = "https://re-katsu.jp/career/company/recruit/57021/"
    # dynamic_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"

    print(f"Fetching dynamic HTML from: {dynamic_url}")
    dynamic_html = get_dynamic_html_with_selenium(dynamic_url, wait_time=15)

    if dynamic_html:
        print(f"Successfully fetched dynamic HTML.")
        site_domain_to_test = get_site_domain(dynamic_url)
        print(f"Detected site domain: {site_domain_to_test}")

        print("\nExtracting text using extract_text_from_html with domain-specific selectors...")
        extracted_info = extract_text_from_html(dynamic_html, dynamic_url, site_domain_to_test)

        print("\n--- Extracted Fields ---")
        print(f"  Job Title: {extracted_info.get('job_title')}")
        print(f"  Salary: {extracted_info.get('salary')}")
        print(f"  Location: {extracted_info.get('location')}")
        print(f"  Qualifications: {extracted_info.get('qualifications')}")
        print(f"  Full Text (first 200 chars): {extracted_info.get('full_text', '')[:200]}...")
        print(f"  Image OCR Texts (count): {len(extracted_info.get('image_ocr_texts'))}")

    else:
        print(f"Failed to fetch dynamic HTML using Selenium from {dynamic_url}.")

import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import os

# Global dictionary for site-specific selectors
SITE_SELECTORS = {
    "gakujo.ne.jp": {
        "job_title": "dl.sep-text dt:-soup-contains('採用職種 ') + dd div span",
        "salary": "dl.sep-text dt:-soup-contains('給与') + dd div span",
        "location": "dl.sep-text dt:-soup-contains('勤務地') + dd div span",
        "qualifications": "dl.sep-text dt:-soup-contains('応募資格') + dd div span",
        "full_text_area": None # ユーザー確認に基づきNoneのまま
    },
    "re-katsu.jp": {
        "job_title": "span#lblWantedJobType",
        "salary": "span#trSalary",
        "location": "span#lblWorklocation",
        "qualifications": "span#lblTalentedpeople",
        "full_text_area": "section#onRec"
    },
    "re-katsu30.jp": {
        "job_title": "h2.recruitDetail__infoTitle",
        "salary": "h3.recruitDetail__sectionSubTitle:-soup-contains('給与') + p.recruitDetail__sectionText",
        "location": "h3.recruitDetail__sectionSubTitle:-soup-contains('勤務地') + p.recruitDetail__sectionText",
        "qualifications": "h3.recruitDetail__sectionSubTitle:-soup-contains('求める人材') + p.recruitDetail__sectionText",
        "full_text_area": "main.recruitDetail > article"
    }
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

def get_static_html_with_requests(url: str) -> str | None:
    """Fetches HTML content from a URL using requests (static fetch)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    }
    try:
        print(f"[scraper] Fetching static HTML from: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生
        print("[scraper] Static HTML content fetched successfully.")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"[scraper] Error fetching static HTML using Requests: {e}")
        return None

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
    # This is a mock OCR function. Replace with actual OCR implementation if needed.
    print(f"[scraper] Mock OCR for image: {image_url}")
    return f"Mock OCR text for {image_url}"

def extract_text_from_html(html_content: str, base_url: str, site_domain: str) -> dict[str, any]:
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
        job_title_selector = selectors_for_site.get("job_title")
        if job_title_selector:
            job_title_tag = soup.select_one(job_title_selector)
            data['job_title'] = job_title_tag.get_text(separator='\n', strip=True) if job_title_tag else None

        salary_selector = selectors_for_site.get("salary")
        if salary_selector:
            salary_tag = soup.select_one(salary_selector)
            if salary_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and salary_tag.find("h3"):
                    salary_tag.find("h3").decompose() # Remove label if present
                data['salary'] = salary_tag.get_text(separator='\n', strip=True)
            else: data['salary'] = None

        location_selector = selectors_for_site.get("location")
        if location_selector:
            location_tag = soup.select_one(location_selector)
            if location_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and location_tag.find("h3"):
                    location_tag.find("h3").decompose() # Remove label if present
                data['location'] = location_tag.get_text(separator='\n', strip=True)
            else: data['location'] = None

        qualifications_selector = selectors_for_site.get("qualifications")
        if qualifications_selector:
            qualifications_tag = soup.select_one(qualifications_selector)
            if qualifications_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and qualifications_tag.find("h3"):
                    qualifications_tag.find("h3").decompose() # Remove label if present
                data['qualifications'] = qualifications_tag.get_text(separator='\n', strip=True)
            else: data['qualifications'] = None

        if not data['job_title']: # Fallback logic for job_title
            if site_domain == "gakujo.ne.jp":
                title_tag_h1_company = soup.find('h1', class_='h1-company-name_inner')
                if title_tag_h1_company: data['job_title'] = title_tag_h1_company.get_text(strip=True)
            if not data['job_title']: # Broader fallback if still no title
                 generic_h1 = soup.find('h1')
                 if generic_h1:
                     # Specific handling for re-katsu.jp h1 if it contains a specific span
                     if site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                         data['job_title'] = generic_h1.find("span", class_="head-catchcopy").get_text(separator='\n', strip=True)
                     else: # Generic h1 text as a broad fallback
                         data['job_title'] = generic_h1.get_text(separator='\n', strip=True)

        full_text_area_selector = selectors_for_site.get("full_text_area")
        full_text_content_area = None
        if full_text_area_selector:
            full_text_content_area = soup.select_one(full_text_area_selector)

        if full_text_content_area:
            data['full_text'] = full_text_content_area.get_text(separator='\n', strip=True)
        else: # Fallback to full body text if no specific area or area not found
            data['full_text'] = soup.get_text(separator='\n', strip=True)

    # Image OCR part (mocked) - kept for structural consistency
    image_urls = extract_image_urls(html_content, base_url)
    for img_url in image_urls:
        data['image_ocr_texts'].append(perform_ocr_on_image(img_url))

    return data

def integrate_all_text(extracted_data: dict) -> str:
    """Combines full_text and OCR image texts for the review phase."""
    text_parts = []
    full_text = extracted_data.get('full_text')
    if full_text: text_parts.append(full_text)
    
    image_ocr_texts = extracted_data.get('image_ocr_texts')
    if image_ocr_texts:
        for ocr_text in image_ocr_texts:
            if ocr_text: text_parts.append(ocr_text)
            
    return "\n\n".join(text_parts)

if __name__ == "__main__":
    print("\n--- Testing Scraper with Multi-Site Selector Logic (using Requests) ---")
    # Test with the Gakujo URL provided by the user, as confirmed suitable for static scraping
    test_url = "https://www.gakujo.ne.jp/campus/company/employ/12138/"
    # test_url = "https://re-katsu.jp/career/company/recruit/57021/" # Another test case
    # test_url = "https://re-katsu30.jp/recruit/1465" # And another

    print(f"Fetching static HTML from: {test_url}")
    static_html = get_static_html_with_requests(test_url)

    if static_html:
        print(f"Successfully fetched static HTML.")
        site_domain_to_test = get_site_domain(test_url)
        print(f"Detected site domain: {site_domain_to_test}")

        print("\nExtracting text using extract_text_from_html with domain-specific selectors...")
        extracted_info = extract_text_from_html(static_html, test_url, site_domain_to_test)

        print("\n--- Extracted Fields ---")
        print(f"  Job Title: {extracted_info.get('job_title')}")
        print(f"  Salary: {extracted_info.get('salary')}")
        print(f"  Location: {extracted_info.get('location')}")
        print(f"  Qualifications: {extracted_info.get('qualifications')}")
        print(f"  Full Text (first 200 chars): {extracted_info.get('full_text', '')[:200]}...")
        print(f"  Image OCR Texts (count): {len(extracted_info.get('image_ocr_texts'))}")
        if extracted_info.get('image_ocr_texts'):
             print(f"  First OCR Text: {extracted_info.get('image_ocr_texts')[0]}")
    else:
        print(f"Failed to fetch static HTML using Requests from {test_url}.")

print("\n--- End of scraper.py test ---")
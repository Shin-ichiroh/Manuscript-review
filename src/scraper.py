import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import os # osはSITE_SELECTORSのパス解決などで間接的に必要になる可能性を考慮し残す (現状直接は使われていない)

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
    print(f"[scraper_debug] Starting extraction for domain: {site_domain}")
    print(f"[scraper_debug] Base URL: {base_url}")

    selectors_for_site = SITE_SELECTORS.get(site_domain)

    if not selectors_for_site:
        print(f"[scraper_debug] WARNING: No specific selectors found for domain '{site_domain}'. Falling back to generic full_text and image extraction.")
        data['full_text'] = soup.get_text(separator='\n', strip=True)
    else:
        # --- Job Title Extraction ---
        job_title_selector = selectors_for_site.get("job_title")
        print(f"[scraper_debug] Attempting job_title with selector: '{job_title_selector}'")
        if job_title_selector:
            job_title_tag = soup.select_one(job_title_selector)
            if job_title_tag:
                data['job_title'] = job_title_tag.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Job title found with primary selector: '{data['job_title']}'")
            else:
                print(f"[scraper_debug] Job title NOT found with primary selector: '{job_title_selector}'")
        else:
            print(f"[scraper_debug] No primary job_title_selector defined for {site_domain}.")

        if not data['job_title']:
            print(f"[scraper_debug] Primary job title extraction failed. Attempting fallbacks for {site_domain}.")
            if site_domain == "gakujo.ne.jp":
                print("[scraper_debug] Trying gakujo.ne.jp specific logic for job title.")
                # Attempt to find "募集概要" section and then "採用職種"
                overview_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'p', 'dt', 'div'] and '募集概要' in tag.get_text(strip=True))
                if overview_header:
                    print(f"[scraper_debug] Found '募集概要' related element: <{overview_header.name}> {overview_header.get_text(strip=True)[:50]}")

                    # Search for "採用職種" label more robustly near the overview_header
                    # We'll look for a dt or strong tag containing '採用職種'
                    current_node = overview_header
                    job_title_label_node = None

                    # Search siblings first, then parent's siblings if overview_header is too specific
                    # This loop is a bit broad, might need refinement based on actual structure
                    # Limit search depth/iterations to avoid performance issues on complex pages
                    search_depth = 0
                    max_search_depth = 20 # How many sibling elements to check

                    while current_node and search_depth < max_search_depth:
                        # Check current_node itself if it's a potential container
                        potential_labels = current_node.find_all(lambda tag: tag.name in ['dt', 'strong', 'p', 'div'] and '採用職種' in tag.get_text(strip=True), limit=5)
                        if potential_labels:
                            # Prefer a dt if available
                            dt_labels = [l for l in potential_labels if l.name == 'dt']
                            if dt_labels:
                                job_title_label_node = dt_labels[0]
                                print(f"[scraper_debug] Found '採用職種' label (dt): <{job_title_label_node.name}>")
                                break
                            job_title_label_node = potential_labels[0] # fallback to first found
                            print(f"[scraper_debug] Found '採用職種' label (other): <{job_title_label_node.name}>")
                            break

                        # Check children of current_node
                        children_labels = current_node.find_all(lambda tag: tag.name in ['dt', 'strong', 'p', 'div'] and '採用職種' in tag.get_text(strip=True), recursive=False, limit=5)
                        if children_labels:
                            dt_labels = [l for l in children_labels if l.name == 'dt']
                            if dt_labels:
                                job_title_label_node = dt_labels[0]
                                print(f"[scraper_debug] Found '採用職種' label in children (dt): <{job_title_label_node.name}>")
                                break
                            job_title_label_node = children_labels[0]
                            print(f"[scraper_debug] Found '採用職種' label in children (other): <{job_title_label_node.name}>")
                            break

                        current_node = current_node.find_next_sibling()
                        search_depth +=1

                    if job_title_label_node:
                        print(f"[scraper_debug] '採用職種' label node found. Text: '{job_title_label_node.get_text(strip=True)}'")
                        # Try to get the next sibling dd or the parent's next sibling's content
                        value_node = None
                        if job_title_label_node.name == 'dt':
                            value_node = job_title_label_node.find_next_sibling('dd')
                            if value_node: print("[scraper_debug] Found dd sibling for dt label.")

                        if not value_node: # If not dt/dd, or dd not found, try parent or general next siblings
                            parent_for_siblings = job_title_label_node.parent
                            next_sibling_after_label = job_title_label_node.find_next_sibling()
                            if next_sibling_after_label:
                                value_node = next_sibling_after_label
                                print(f"[scraper_debug] Using next sibling of label: <{value_node.name}>")
                            elif parent_for_siblings and parent_for_siblings.find_next_sibling():
                                value_node = parent_for_siblings.find_next_sibling()
                                print(f"[scraper_debug] Using parent's next sibling: <{value_node.name if value_node else 'None'}>")


                        if value_node:
                            # Extract text, potentially cleaning it or taking first few lines
                            raw_text = value_node.get_text(separator='\n', strip=True)
                            # Often, job titles are listed one per line or separated by specific characters
                            # For gakujo, it seems to be a slash-separated list or multiline
                            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                            # Heuristic: if a line contains "■" or "／", it's likely part of the job title list
                            job_titles_collected = []
                            for line in lines:
                                if "■" in line or "／" in line or "・" in line or not any(kw in line for kw in ["仕事内容", "勤務地", "給与", "応募資格"]):
                                    job_titles_collected.append(line)
                                    if len(job_titles_collected) >= 5 and "など" not in line : # Stop if we have many and no "など"
                                        break
                                elif job_titles_collected: # Stop if we started collecting and hit a non-title line
                                    break

                            if job_titles_collected:
                                data['job_title'] = "\n".join(job_titles_collected)
                                print(f"[scraper_debug] Job title extracted from '募集概要' (refined): '{data['job_title']}'")
                            else:
                                print("[scraper_debug] Could not refine job title text from value_node.")
                                data['job_title'] = raw_text.splitlines()[0] if raw_text else None # Fallback to first line
                                print(f"[scraper_debug] Job title (fallback to first line of value_node): '{data['job_title']}'")
                        else:
                            print("[scraper_debug] Could not find a suitable value node for '採用職種'.")
                    else:
                        print("[scraper_debug] '採用職種' label not found near '募集概要'.")

                # Fallback to h1.h1-company-name_inner if still no job title (though this is company name)
                if not data['job_title']:
                    print("[scraper_debug] Trying gakujo.ne.jp h1.h1-company-name_inner as last resort for gakujo.")
                    title_tag_h1_company = soup.find('h1', class_='h1-company-name_inner')
                    if title_tag_h1_company:
                        # This is company name, but better than nothing if all else fails.
                        # data['job_title'] = title_tag_h1_company.get_text(strip=True)
                        print(f"[scraper_debug] Found h1.h1-company-name_inner: '{title_tag_h1_company.get_text(strip=True)}'. (This is company name)")
                    else:
                        print("[scraper_debug] gakujo.ne.jp h1.h1-company-name_inner not found.")

            # Broader fallback using generic H1 (less reliable for job title)
            if not data['job_title']:
                print(f"[scraper_debug] Trying generic H1 fallback for {site_domain} as all specific attempts failed.")
                generic_h1 = soup.find('h1')
                if generic_h1:
                    # Specific handling for re-katsu.jp H1
                    if site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                        print("[scraper_debug] Using re-katsu.jp h1 span.head-catchcopy.")
                        data['job_title'] = generic_h1.find("span", class_="head-catchcopy").get_text(separator='\n', strip=True)
                    else:
                        # data['job_title'] = generic_h1.get_text(separator='\n', strip=True) # Usually not job title
                        print(f"[scraper_debug] Generic H1 text: '{generic_h1.get_text(separator='\n', strip=True)}'. (Likely not job title)")
                else:
                    print("[scraper_debug] Generic H1 not found.")

            if not data['job_title']:
                 print(f"[scraper_debug] All job title extraction attempts for {site_domain} ultimately failed.")


        # --- Salary Extraction ---
        salary_selector = selectors_for_site.get("salary")
        print(f"[scraper_debug] Attempting salary with selector: '{salary_selector}'")
        if salary_selector:
            salary_tag = soup.select_one(salary_selector)
            if salary_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and salary_tag.find("h3"):
                    salary_tag.find("h3").decompose()
                data['salary'] = salary_tag.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Salary found: '{data['salary'][:100]}...'") # Print snippet
            else:
                print(f"[scraper_debug] Salary NOT found with selector: '{salary_selector}'")
        else:
            print(f"[scraper_debug] No salary_selector defined for {site_domain}.")

        # For location
        location_selector = selectors_for_site.get("location")
        print(f"[scraper_debug] Attempting location with selector: '{location_selector}'")
        if location_selector:
            location_tag = soup.select_one(location_selector)
            if location_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and location_tag.find("h3"):
                    location_tag.find("h3").decompose()
                data['location'] = location_tag.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Location found: '{data['location'][:100]}...'") # Print snippet
            else:
                print(f"[scraper_debug] Location NOT found with selector: '{location_selector}'")
        else:
            print(f"[scraper_debug] No location_selector defined for {site_domain}.")

        # For qualifications
        qualifications_selector = selectors_for_site.get("qualifications")
        print(f"[scraper_debug] Attempting qualifications with selector: '{qualifications_selector}'")
        if qualifications_selector:
            qualifications_tag = soup.select_one(qualifications_selector)
            if qualifications_tag:
                if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and qualifications_tag.find("h3"):
                    qualifications_tag.find("h3").decompose()
                data['qualifications'] = qualifications_tag.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Qualifications found: '{data['qualifications'][:100]}...'") # Print snippet
            else:
                print(f"[scraper_debug] Qualifications NOT found with selector: '{qualifications_selector}'")
        else:
            print(f"[scraper_debug] No qualifications_selector defined for {site_domain}.")


        full_text_area_selector = selectors_for_site.get("full_text_area")
        print(f"[scraper_debug] Attempting full_text_area with selector: '{full_text_area_selector}'")
        full_text_content_area = None
        if full_text_area_selector:
            full_text_content_area = soup.select_one(full_text_area_selector)

        if full_text_content_area:
            data['full_text'] = full_text_content_area.get_text(separator='\n', strip=True)
            print(f"[scraper_debug] Full text found with selector. Length: {len(data['full_text'])}")
        else:
            print(f"[scraper_debug] Full text selector not found or no selector defined. Falling back to full body text.")
            data['full_text'] = soup.get_text(separator='\n', strip=True)
            print(f"[scraper_debug] Full text (fallback) length: {len(data['full_text'])}")

    # Image OCR part (mocked) - kept for structural consistency
    # image_urls = extract_image_urls(html_content, base_url)
    # for img_url in image_urls:
    #     data['image_ocr_texts'].append(perform_ocr_on_image(img_url))
    print(f"[scraper_debug] Final extracted job_title: '{data['job_title']}'")
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

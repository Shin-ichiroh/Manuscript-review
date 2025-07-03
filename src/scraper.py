import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import os
import re

# Global dictionary for site-specific selectors
SITE_SELECTORS = {
    "gakujo.ne.jp": {
        # Primary job_title selector for gakujo.ne.jp is now handled by specific logic first
        "job_title": "dl.sep-text dt:-soup-contains('採用職種 ') + dd div span", # Kept as a fallback if specific logic fails
        "salary": "dl.sep-text dt:-soup-contains('給与') + dd div span",
        "location": "dl.sep-text dt:-soup-contains('勤務地') + dd div span",
        "qualifications": "dl.sep-text dt:-soup-contains('応募資格') + dd div span",
        "full_text_area": None 
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
        response.raise_for_status()
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
    print(f"[scraper] Mock OCR for image: {image_url}")
    return f"Mock OCR text for {image_url}"

def extract_text_from_html(html_content: str, base_url: str, site_domain: str) -> dict[str, any]:
    soup = BeautifulSoup(html_content, "html.parser")
    data: dict[str, any] = {
        "job_title": None, "salary": None, "location": None, "qualifications": None,
        "full_text": None, "image_ocr_texts": [],
    }
    print(f"[scraper_debug] Starting extraction for domain: {site_domain}")

    selectors_for_site = SITE_SELECTORS.get(site_domain)

    if not selectors_for_site:
        print(f"[scraper_debug] WARNING: No specific selectors found for domain '{site_domain}'. Falling back to generic full_text.")
        data['full_text'] = soup.get_text(separator='\n', strip=True)
    else:
        # --- Job Title Extraction ---
        job_title_extracted_specifically = False
        if site_domain == "gakujo.ne.jp":
            print(f"[scraper_debug] Applying specific gakujo.ne.jp job_title logic for URL: {base_url}")
            
            titles_from_pattern1 = []
            titles_from_pattern2 = []

            # Pattern 1: "募集概要" header followed by "XX卒新卒（職種リスト）" or similar
            overview_header = soup.find(['h2', 'h3', 'h4'], string=lambda s: isinstance(s, str) and '募集概要' in s.strip())
            if overview_header:
                print(f"[scraper_debug] Found '募集概要' header: <{overview_header.name}> '{overview_header.get_text(strip=True)}'")
                collected_texts_after_overview = []
                current_element = overview_header.find_next_sibling()
                elements_to_check = 3 
                while current_element and elements_to_check > 0:
                    if current_element.name in ['h2', 'h3', 'h4', 'dt']: break
                    text_from_elem = current_element.get_text(separator=' ', strip=True)
                    if text_from_elem: collected_texts_after_overview.append(text_from_elem)
                    current_element = current_element.find_next_sibling()
                    elements_to_check -= 1
                
                if collected_texts_after_overview:
                    full_text_after_overview = " ".join(collected_texts_after_overview)
                    print(f"[scraper_debug] Text after '募集概要' for Pattern 1: '{full_text_after_overview[:250]}'")
                    # Regex for "XX卒新卒（...）", "XX職種（...）", or "（...職）"
                    matches = re.finditer(r"(\d+卒新卒\s*（[^）]+）|\w+職種\s*（[^）]+）|（[^）]+職）)", full_text_after_overview)
                    for match in matches:
                        titles_from_pattern1.append(match.group(1))
                    if titles_from_pattern1:
                        print(f"[scraper_debug] Job titles from Pattern 1: {titles_from_pattern1}")
                    else:
                        print(f"[scraper_debug] No job title patterns found in text after '募集概要'.")
            else:
                print(f"[scraper_debug] '募集概要' header not found (Pattern 1).")

            # Pattern 2: "採用職種" dt/dd logic
            print(f"[scraper_debug] Trying dt/dd logic for gakujo (Pattern 2).")
            dt_saiyo_shokushu_list = soup.find_all('dt', string=lambda s: isinstance(s, str) and '採用職種' in s.strip())
            print(f"[scraper_debug] Found {len(dt_saiyo_shokushu_list)} <dt> tags containing '採用職種' for Pattern 2.")
            for dt_tag in dt_saiyo_shokushu_list:
                dd_tag = dt_tag.find_next_sibling('dd')
                if dd_tag:
                    dd_text_strip = dd_tag.get_text(strip=True)
                    dd_full_text = dd_tag.get_text(separator='\n', strip=True)
                    print(f"[scraper_debug] Pattern 2: Found <dd> for <dt>. DD content: '{dd_text_strip[:100]}'")
                    
                    # Heuristic for /61510/ like pages or general lists
                    if "／" in dd_text_strip and not "■" in dd_text_strip and len(dd_text_strip) > 3:
                        titles_from_pattern2.append(dd_full_text.strip())
                        print(f"[scraper_debug] Job titles added from Pattern 2 (dt/dd, simpler heuristic): '{dd_full_text.strip()}'")
                    # Original heuristic for /12138/ like pages
                    elif "■総合職" in dd_text_strip or "■一般職" in dd_text_strip:
                        lines = [line.strip() for line in dd_full_text.split('\n') if line.strip()]
                        job_titles_collected_for_dd = []
                        collecting = False
                        for line in lines:
                            if line.startswith("■"): collecting = True
                            if collecting:
                                if not any(kw in line for kw in ["仕事内容", "勤務地", "給与", "応募資格", "休日休暇"]) or line.startswith("■"):
                                    job_titles_collected_for_dd.append(line)
                                    if len(job_titles_collected_for_dd) >= 7: break
                                elif job_titles_collected_for_dd: break
                        if job_titles_collected_for_dd:
                            titles_from_pattern2.append("\n".join(job_titles_collected_for_dd))
                            print(f"[scraper_debug] Job titles added from Pattern 2 (dt/dd, original heuristic): {' '.join(job_titles_collected_for_dd)}'")
            if not titles_from_pattern2 and dt_saiyo_shokushu_list:
                print(f"[scraper_debug] Pattern 2 (dt/dd logic) did not yield results matching heuristics.")
            elif not dt_saiyo_shokushu_list:
                 print(f"[scraper_debug] No '採用職種' <dt> tags found for Pattern 2.")

            # Combine titles from both patterns, ensuring no duplicates if they happen to be identical strings
            combined_titles = []
            seen_titles = set()
            for title_list in [titles_from_pattern1, titles_from_pattern2]:
                for title_text in title_list:
                    if title_text not in seen_titles:
                        combined_titles.append(title_text)
                        seen_titles.add(title_text)
            
            if combined_titles:
                data['job_title'] = "\n---\n".join(combined_titles) # Join with a clear separator
                job_title_extracted_specifically = True
                print(f"[scraper_debug] Combined job titles for gakujo.ne.jp: '{data['job_title']}'")
            else:
                 print(f"[scraper_debug] All specific gakujo.ne.jp job title logics failed.")
        
        # If specific logic didn't find it, or for other sites, try primary selector from SITE_SELECTORS
        # (This part remains the same as your current working version)
        if not job_title_extracted_specifically:
            # ... (existing code for job_title_selector, H1 fallback etc.)
            job_title_selector = selectors_for_site.get("job_title")
            print(f"[scraper_debug] Attempting job_title with SITE_SELECTORS primary selector: '{job_title_selector}'")
            if job_title_selector:
                job_title_tag = soup.select_one(job_title_selector)
                if job_title_tag:
                    data['job_title'] = job_title_tag.get_text(separator='\n', strip=True)
                    print(f"[scraper_debug] Job title found with SITE_SELECTORS primary selector: '{data['job_title']}'")
                else:
                    print(f"[scraper_debug] Job title NOT found with SITE_SELECTORS primary selector: '{job_title_selector}'")
            else:
                print(f"[scraper_debug] No primary job_title_selector in SITE_SELECTORS for {site_domain}.")

        # Fallback to generic H1 (less reliable)
        if not data['job_title']:
            print(f"[scraper_debug] No job title yet. Trying H1 fallback for {site_domain}.")
            generic_h1 = soup.find('h1')
            if generic_h1:
                if site_domain == "gakujo.ne.jp" and 'h1-company-name_inner' in generic_h1.get('class', []):
                     print(f"[scraper_debug] Found H1 for gakujo (company name): '{generic_h1.get_text(strip=True)}'. Not using for job_title.")
                elif site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                    data['job_title'] = generic_h1.find("span", class_="head-catchcopy").get_text(separator='\n', strip=True)
                    print(f"[scraper_debug] Job title from re-katsu.jp H1 span: '{data['job_title']}'")
                # else: # Avoid assigning generic H1 to job_title unless very sure
                #     print(f"[scraper_debug] Generic H1 text: '{generic_h1.get_text(strip=True)}'. Not assigning to job_title by default.")
            else:
                print(f"[scraper_debug] Generic H1 not found.")
        
        if not data['job_title']:
            print(f"[scraper_debug] All job title extraction attempts for {site_domain} ultimately failed. Job title remains None.")

        # --- Salary, Location, Qualifications --- (using existing selectors from SITE_SELECTORS)
        for field_key in ["salary", "location", "qualifications"]:
            selector = selectors_for_site.get(field_key)
            print(f"[scraper_debug] Attempting {field_key} with selector: '{selector}'")
            if selector:
                tag = soup.select_one(selector)
                if tag:
                    if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and tag.find("h3"):
                        tag.find("h3").decompose()
                    data[field_key] = tag.get_text(separator='\n', strip=True)
                    print(f"[scraper_debug] {field_key.capitalize()} found: '{data[field_key][:100] if data[field_key] else 'None'}...'" )
                else:
                    print(f"[scraper_debug] {field_key.capitalize()} NOT found with selector: '{selector}'")
            else:
                print(f"[scraper_debug] No {field_key}_selector defined for {site_domain}.")

        # --- Full Text ---
        full_text_area_selector = selectors_for_site.get("full_text_area")
        print(f"[scraper_debug] Attempting full_text_area with selector: '{full_text_area_selector}'")
        if full_text_area_selector:
            full_text_content_area = soup.select_one(full_text_area_selector)
            if full_text_content_area:
                data['full_text'] = full_text_content_area.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Full text found with selector. Length: {len(data['full_text'])}")
            else:
                print(f"[scraper_debug] Full text area selector '{full_text_area_selector}' did not find content. Falling back to full body text.")
                data['full_text'] = soup.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] Full text (fallback) length: {len(data['full_text'])}")
        else:
            print(f"[scraper_debug] No full_text_area selector. Falling back to full body text.")
            data['full_text'] = soup.get_text(separator='\n', strip=True)
            print(f"[scraper_debug] Full text (fallback) length: {len(data['full_text'])}")

    # Image OCR (mocked)
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
    test_url = "https://www.gakujo.ne.jp/campus/company/employ/61510/" # Target URL for testing

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
        # print(f"  Image OCR Texts (count): {len(extracted_info.get('image_ocr_texts'))}")
        # if extracted_info.get('image_ocr_texts'):
        #      print(f"  First OCR Text: {extracted_info.get('image_ocr_texts')[0]}")
    else:
        print(f"Failed to fetch static HTML using Requests from {test_url}.")

print("\n--- End of scraper.py test ---")
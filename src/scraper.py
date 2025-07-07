import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse, parse_qs
import os
import re 
import time

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Global dictionary for site-specific selectors
SITE_SELECTORS = {
    "gakujo.ne.jp": {
        "job_title": "dl.sep-text dt:-soup-contains('採用職種 ') + dd div span", 
        "salary": "dl.sep-text dt:-soup-contains('給与') + dd div span",
        "location": "dl.sep-text dt:-soup-contains('勤務地') + dd div span",
        "qualifications": "dl.sep-text dt:-soup-contains('応募資格') + dd div span",
        "full_text_area": "div.sep__detail__contents" # ★★★ この行を追加/更新 ★★★
    },
    "re-katsu.jp": {
        "job_title": "span#lblWantedJobType", # This is Pattern A for re-katsu
        # Pattern B for re-katsu (upper page job title) will be handled by a specific selector in the code
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
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def get_static_html_with_requests(url: str) -> str | None:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    }
    try:
        print(f"[scraper] Fetching static HTML from: {url} (using requests)")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        print("[scraper] Static HTML content fetched successfully (requests).")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"[scraper] Error fetching static HTML using Requests: {e}")
        return None

def get_dynamic_html_with_selenium(url: str, wait_time: int = 10) -> str | None:
    driver = None
    print(f"[scraper_selenium] Attempting to fetch dynamic HTML from: {url}")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        print("[scraper_selenium] Chrome options set.")
        try:
            print("[scraper_selenium] Attempting to start ChromeDriver via ChromeDriverManager...")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("[scraper_selenium] ChromeDriver started via ChromeDriverManager successfully.")
        except Exception as e_manager:
            print(f"[scraper_selenium] ChromeDriverManager failed: {e_manager}. Trying default ChromeDriver path.")
            driver = webdriver.Chrome(options=chrome_options)
            print("[scraper_selenium] ChromeDriver started using default system PATH.")

        print(f"[scraper_selenium] Navigating to URL: {url}")
        driver.get(url)
        print(f"[scraper_selenium] Navigated to URL. Waiting for {wait_time} seconds for dynamic content...")
        time.sleep(wait_time)
        
        page_source = driver.page_source
        if page_source and len(page_source) > 100:
            print(f"[scraper_selenium] Successfully fetched page source. Length: {len(page_source)}")
        else:
            print(f"[scraper_selenium] Page source is empty or very short. Length: {len(page_source) if page_source else 0}")
            return None
        return page_source
    except Exception as e:
        print(f"[scraper_selenium] An error occurred during Selenium HTML fetching for {url}: {e}")
        import traceback
        print(f"[scraper_selenium] Traceback: {traceback.format_exc()}")
        return None
    finally:
        if driver:
            driver.quit()
            print("[scraper_selenium] ChromeDriver quit.")

def fetch_html_content(url: str, use_selenium_if_prv: bool = True) -> str | None:
    print(f"[scraper_fetch] Received URL for processing: {url}")
    try:
        parsed_url = urlparse(url)
        # クエリパラメータをデコードせずに生の文字列として取得してみる
        raw_query_string = parsed_url.query
        print(f"[scraper_fetch] Raw query string: {raw_query_string}")

        query_params = parse_qs(raw_query_string, keep_blank_values=True)
        print(f"[scraper_fetch] Parsed query_params: {query_params}")

        should_use_selenium = False
        if use_selenium_if_prv:
            # prvパラメータの存在と値をより頑健にチェック
            if 'prv' in raw_query_string.lower(): # 生のクエリ文字列で 'prv' をチェック
                prv_values = query_params.get('prv')
                if prv_values:
                    print(f"[scraper_fetch] 'prv' parameter values found: {prv_values}")
                    if any(val.lower() == 'on' for val in prv_values):
                        should_use_selenium = True
                        print(f"[scraper_fetch] 'prv=ON' (case-insensitive) condition met based on parsed values.")
                    else:
                        print(f"[scraper_fetch] 'prv' parsed but value not 'ON'. Values: {prv_values}")
                # もしparse_qsでうまく取れない場合も考慮し、生の文字列でもチェック
                elif 'prv=on' in raw_query_string.lower(): # Check in raw query string as a fallback
                    should_use_selenium = True
                    print(f"[scraper_fetch] 'prv=on' (case-insensitive) found in raw query string. Forcing Selenium.")
                else:
                    print(f"[scraper_fetch] 'prv' key found in raw query but value not 'on'.")
            else:
                print(f"[scraper_fetch] 'prv' key not found in raw query string.")
        else:
            print(f"[scraper_fetch] use_selenium_if_prv is False.")
            
        if should_use_selenium:
            print(f"[scraper_fetch] Decision: Use Selenium for URL: {url}")
            return get_dynamic_html_with_selenium(url)
        else:
            print(f"[scraper_fetch] Decision: Use Requests for URL: {url}")
            return get_static_html_with_requests(url)
            
    except Exception as e_fetch:
        print(f"[scraper_fetch] CRITICAL ERROR in fetch_html_content for URL {url}: {e_fetch}")
        import traceback
        print(f"[scraper_fetch] Traceback: {traceback.format_exc()}")
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
        job_title_extracted_specifically = False
        
        if site_domain == "gakujo.ne.jp":
            print(f"[scraper_debug] Applying specific gakujo.ne.jp job_title logic for URL: {base_url}")
            titles_collected = [] # 取得した職種候補をここに集める
            seen_titles_for_combine = set()

            # --- メインの抽出ロジック: <dt>採用職種</dt> or <dt>職種</dt> ---
            # "採用職種" または "職種" というテキストを持つdtタグを探す
            dt_job_labels = soup.find_all('dt', string=lambda s: isinstance(s, str) and ('採用職種' in s.strip() or s.strip() == '職種'))
            print(f"[scraper_debug] Found {len(dt_job_labels)} <dt> tags with '採用職種' or '職種'.")
            for dt_tag in dt_job_labels:
                dd_tag = dt_tag.find_next_sibling('dd')
                if dd_tag:
                    # ddタグ直下のspanタグの内容を取得しようと試みる
                    span_tag = dd_tag.find('span') # ddの最初の子孫spanを想定
                    job_text_candidate = ""
                    if span_tag:
                        job_text_candidate = span_tag.get_text(separator='\n', strip=True)
                        print(f"[scraper_debug] Found <dd><span> for <dt> '{dt_tag.get_text(strip=True)}'. Span content: '{job_text_candidate[:100]}'")
                    else: # spanがない場合はdd全体のテキストを試す
                        job_text_candidate = dd_tag.get_text(separator='\n', strip=True)
                        print(f"[scraper_debug] Found <dd> for <dt> '{dt_tag.get_text(strip=True)}', no span inside. DD content: '{job_text_candidate[:100]}'")

                    if job_text_candidate and job_text_candidate not in seen_titles_for_combine:
                        # 簡単なヒューリスティック: あまりにも長すぎるものは除外 (例: 300文字以上)
                        # また、明らかに職種ではないキーワードを含むものも除外検討 (例: "仕事内容"がddに入ってしまっている場合など)
                        if len(job_text_candidate) < 300 and not any(kw in job_text_candidate for kw in ["仕事内容詳細", "勤務地詳細"]):
                            titles_collected.append(job_text_candidate)
                            seen_titles_for_combine.add(job_text_candidate)
                            print(f"[scraper_debug] Added to job titles from dt/dd: '{job_text_candidate}'")
                        else:
                            print(f"[scraper_debug] Candidate from dt/dd rejected (too long or keyword conflict): '{job_text_candidate[:50]}...'" )
            
            # --- 補助的な抽出ロジック: 「募集概要」直後のテキスト ---
            # (これは、上記dt/ddで見つからない場合の補完、または追加情報として)
            overview_header = soup.find(['h2', 'h3', 'h4'], string=lambda s: isinstance(s, str) and '募集概要' in s.strip())
            if overview_header:
                print(f"[scraper_debug] Found '募集概要' header for aux check: <{overview_header.name}> '{overview_header.get_text(strip=True)}'")
                collected_texts_after_overview = []
                current_element = overview_header.find_next_sibling()
                elements_to_check = 2 # 直後の2要素程度をチェック
                while current_element and elements_to_check > 0:
                    if current_element.name in ['h2', 'h3', 'h4', 'dt', 'dl']: break # 新しいセクションやリストが始まったら止める
                    text_from_elem = current_element.get_text(separator=' ', strip=True)
                    if text_from_elem: collected_texts_after_overview.append(text_from_elem)
                    current_element = current_element.find_next_sibling()
                    elements_to_check -= 1
                
                if collected_texts_after_overview:
                    full_text_after_overview = " ".join(collected_texts_after_overview)
                    print(f"[scraper_debug] Text after '募集概要' for aux check: '{full_text_after_overview[:200]}'")
                    # ここでは特定のパターンにマッチするものを探す (例: "XX卒新卒（...）" や "（...職）")
                    # または、単純にこのテキストブロックが職種情報らしいか判定する
                    # 今回は、もしこのテキストが短く（例: 100文字以内）、かつdt/ddで見つかったものと異なる場合に採用を検討
                    if len(full_text_after_overview) > 3 and len(full_text_after_overview) < 150:
                        if full_text_after_overview not in seen_titles_for_combine:
                            # これが本当に職種かは慎重に判断。今回は例として追加。
                            # titles_collected.append(full_text_after_overview)
                            # seen_titles_for_combine.add(full_text_after_overview)
                            print(f"[scraper_debug] Aux check: Text after '募集概要' considered as potential job title: '{full_text_after_overview}' (Not adding by default, needs review)")
            else:
                print(f"[scraper_debug] '募集概要' header not found for aux check.")


            if titles_collected:
                data['job_title'] = "\n---\n".join(titles_collected) # Join with a clear separator
                job_title_extracted_specifically = True
                print(f"[scraper_debug] Combined job titles for gakujo.ne.jp: '{data['job_title']}'")
            else: 
                print(f"[scraper_debug] No job titles extracted from specific gakujo.ne.jp logic.")
        
        elif site_domain == "re-katsu.jp":
            print(f"[scraper_debug] Applying specific re-katsu.jp job_title logic.")
            titles_to_combine = [] 
            seen_titles_for_combine = set()

            # Pattern A: Existing selector (SITE_SELECTORS["re-katsu.jp"]["job_title"])
            selector_pattern_a = selectors_for_site.get("job_title") 
            if selector_pattern_a:
                tag_a = soup.select_one(selector_pattern_a)
                if tag_a:
                    title_a = tag_a.get_text(separator='\n', strip=True)
                    if title_a and title_a not in seen_titles_for_combine:
                        titles_to_combine.append(title_a)
                        seen_titles_for_combine.add(title_a)
                        print(f"[scraper_debug] Re-katsu: Job title from Pattern A ('{selector_pattern_a}'): '{title_a}'")
                else:
                    print(f"[scraper_debug] Re-katsu: Job title NOT found with Pattern A selector: '{selector_pattern_a}'")
            else:
                print(f"[scraper_debug] Re-katsu: No Pattern A selector defined in SITE_SELECTORS.")

            # Pattern B: New selector for upper page job title (based on user provided id)
            selector_pattern_b = "span#lblServIcon" 
            
            print(f"[scraper_debug] Re-katsu: Attempting job_title with Pattern B selector: '{selector_pattern_b}'")
            tag_b = soup.select_one(selector_pattern_b)
            if tag_b:
                title_b = tag_b.get_text(separator='\n', strip=True)
                if title_b and title_b not in seen_titles_for_combine:
                    titles_to_combine.append(title_b)
                    seen_titles_for_combine.add(title_b)
                    print(f"[scraper_debug] Re-katsu: Job title from Pattern B ('{selector_pattern_b}'): '{title_b}'")
            else:
                print(f"[scraper_debug] Re-katsu: Job title NOT found with Pattern B selector: '{selector_pattern_b}'")

            if titles_to_combine:
                data['job_title'] = "\n---\n".join(titles_to_combine) 
                job_title_extracted_specifically = True
                print(f"[scraper_debug] Combined job titles for re-katsu.jp: '{data['job_title']}'")
            else:
                print(f"[scraper_debug] No job titles found from any specific pattern for re-katsu.jp.")
        
        # If specific logic for a site didn't set job_title, or for other unhandled sites, try primary selector
        if not job_title_extracted_specifically:
            if site_domain not in ["gakujo.ne.jp", "re-katsu.jp"]: 
                job_title_selector = selectors_for_site.get("job_title")
                print(f"[scraper_debug] Attempting job_title for '{site_domain}' with SITE_SELECTORS primary selector: '{job_title_selector}'")
                if job_title_selector:
                    job_title_tag = soup.select_one(job_title_selector)
                    if job_title_tag:
                        data['job_title'] = job_title_tag.get_text(separator='\n', strip=True)
                        print(f"[scraper_debug] Job title found with SITE_SELECTORS primary selector for '{site_domain}': '{data['job_title']}'")
                    else:
                        print(f"[scraper_debug] Job title NOT found with SITE_SELECTORS primary selector for '{site_domain}': '{job_title_selector}'")
                else:
                    print(f"[scraper_debug] No primary job_title_selector in SITE_SELECTORS for {site_domain}.")

        # Fallback to generic H1 (less reliable) only if still no job title
        if not data['job_title']:
            print(f"[scraper_debug] No job title from specific or primary selectors. Trying H1 fallback for {site_domain}.")
            generic_h1 = soup.find('h1')
            if generic_h1:
                if site_domain == "gakujo.ne.jp" and 'h1-company-name_inner' in generic_h1.get('class', []):
                     print(f"[scraper_debug] Found H1 for gakujo (company name): '{generic_h1.get_text(strip=True)}'. Not using for job_title.")
                elif site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                     print(f"[scraper_debug] Re-katsu H1 with head-catchcopy found: '{generic_h1.find('span', class_='head-catchcopy').get_text(strip=True)}'. Not assigning if specific logic ran.")
            else:
                print(f"[scraper_debug] Generic H1 not found.")
        
        if not data['job_title']:
            print(f"[scraper_debug] All job title extraction attempts for {site_domain} ultimately failed. Job title remains None.")

        # --- Salary, Location, Qualifications ---
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

    print(f"[scraper_debug] Final extracted job_title: '{data['job_title']}'")
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
    
    test_urls = [
        "https://www.gakujo.ne.jp/campus/company/employ/83134?prv=ON", 
        "https://www.gakujo.ne.jp/campus/company/employ/12138/",      
        "https://re-katsu.jp/career/company/recruit/57536/?prv=ON", 
        # "https://re-katsu.jp/career/company/recruit/57021/"       # Example normal re-katsu URL
    ]

    for test_url in test_urls:
        print(f"\n--- Testing URL: {test_url} ---")
        html_content = fetch_html_content(test_url, use_selenium_if_prv=True)
        
        if html_content:
            domain = get_site_domain(test_url)
            print(f"Detected site domain: {domain}")
            extracted_info = extract_text_from_html(html_content, test_url, domain)
            print("\n--- Extracted Fields ---")
            for key, value in extracted_info.items():
                if key == "full_text": print(f"  {key}: {str(value)[:200]}...")
                elif key == "image_ocr_texts": print(f"  {key} (count): {len(value)}")
                else: print(f"  {key}: {value}")
        else:
            print(f"Failed to fetch HTML for {test_url}")

    print("\n--- End of scraper.py test ---")
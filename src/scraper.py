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
    print(f"[scraper_debug] ドメイン '{site_domain}' の抽出処理を開始します。ベースURL: {base_url}")

    selectors_for_site = SITE_SELECTORS.get(site_domain)

    if not selectors_for_site:
        print(f"[scraper_debug] 警告: ドメイン '{site_domain}' に固有のセレクタ定義が見つかりません。ページ全体のテキストを抽出します。")
        data['full_text'] = soup.get_text(separator='\n', strip=True)
    else:
        # 職種情報がサイト固有のロジックで抽出されたかどうかのフラグ
        job_title_extracted_specifically = False
        
        # --- 職種 (job_title) の抽出 ---
        if site_domain == "gakujo.ne.jp":
            print(f"[scraper_debug] gakujo.ne.jp 固有の職種抽出ロジックを適用します。")
            # 複数のパターンから職種情報を収集するためのリスト
            titles_from_pattern1_gakujo = [] # パターン1: 「募集概要」ヘッダー直後のテキストからの抽出用
            titles_from_pattern2_gakujo = [] # パターン2: <dt>採用職種/職種</dt> <dd>...</dd> 構造からの抽出用

            # パターン1: 「募集概要」ヘッダーを探し、その直後のテキストから職種関連情報を抽出
            # h2, h3, h4 タグで、テキストに「募集概要」を含むものを探す
            overview_header = soup.find(['h2', 'h3', 'h4'], string=lambda s: isinstance(s, str) and '募集概要' in s.strip())
            if overview_header:
                print(f"[scraper_debug] Gakujo P1: '募集概要'ヘッダー発見: <{overview_header.name}> '{overview_header.get_text(strip=True)}'")
                collected_texts_after_overview = []
                current_element = overview_header.find_next_sibling()
                elements_to_check = 3 # 「募集概要」ヘッダーの後の数要素をチェック対象とする
                while current_element and elements_to_check > 0:
                    # 新しい主要ヘッダーや定義リストの開始が見つかったら、そこまでを範囲とする
                    if current_element.name in ['h2', 'h3', 'h4', 'dt', 'dl']: 
                        print(f"[scraper_debug] Gakujo P1: 次のセクション開始タグ <{current_element.name}> を検知したためテキスト収集を終了。")
                        break
                    text_from_elem = current_element.get_text(separator=' ', strip=True) # 要素内のテキストをスペース区切りで連結
                    if text_from_elem: 
                        collected_texts_after_overview.append(text_from_elem)
                    current_element = current_element.find_next_sibling()
                    elements_to_check -= 1
                
                if collected_texts_after_overview:
                    full_text_after_overview = " ".join(collected_texts_after_overview)
                    print(f"[scraper_debug] Gakujo P1: '募集概要'直後の収集テキスト: '{full_text_after_overview[:250]}'")
                    # 「XX卒新卒（職種リスト）」、「〇〇職種（リスト）」、「（〇〇職）」のパターンを正規表現で検索
                    matches = re.finditer(r"(\d+卒新卒\s*（[^）]+）|\w+職種\s*（[^）]+）|（[^）]+職）)", full_text_after_overview)
                    for match in matches: 
                        titles_from_pattern1_gakujo.append(match.group(1))
                    if titles_from_pattern1_gakujo: 
                        print(f"[scraper_debug] Gakujo P1: 正規表現で職種候補を発見: {titles_from_pattern1_gakujo}")
                    else: 
                        print(f"[scraper_debug] Gakujo P1: '募集概要'直後のテキストから正規表現パターンに一致する職種は見つかりませんでした。")
                else:
                    print(f"[scraper_debug] Gakujo P1: '募集概要'ヘッダーの直後に有効なテキスト要素が見つかりませんでした。")
            else: 
                print(f"[scraper_debug] Gakujo P1: '募集概要'ヘッダーが見つかりませんでした。")

            # パターン2: <dt>採用職種</dt> または <dt>職種</dt> に続く <dd> から職種情報を抽出
            print(f"[scraper_debug] Gakujo P2: dt/dd構造からの職種抽出ロジックを開始します。")
            # '採用職種' または '職種' という文字列を含むdtタグをすべて検索 (大文字・小文字、前後の空白を考慮)
            dt_job_labels = soup.find_all('dt', string=lambda s: isinstance(s, str) and ('採用職種' in s.strip() or s.strip() == '職種'))
            print(f"[scraper_debug] Gakujo P2: '採用職種'または'職種'を含む<dt>タグを {len(dt_job_labels)}個 発見しました。")
            for dt_tag in dt_job_labels:
                dd_tag = dt_tag.find_next_sibling('dd') # dtタグの直後のddタグを取得
                if dd_tag:
                    job_text_candidate = ""
                    # まず dd > div > span の構造を優先的に探す (ユーザー提供のHTML構造に合致)
                    div_in_dd = dd_tag.find('div')
                    if div_in_dd:
                        span_in_div = div_in_dd.find('span')
                        if span_in_div:
                            job_text_candidate = span_in_div.get_text(separator='\n', strip=True)
                            print(f"[scraper_debug] Gakujo P2: <dt>'{dt_tag.get_text(strip=True)}' に続く <dd><div><span> からテキスト取得: '{job_text_candidate[:100]}'")
                    
                    # 上記で見つからなければ、dd 直下の最初の span を試す
                    if not job_text_candidate:
                        span_tag = dd_tag.find('span') 
                        if span_tag:
                            job_text_candidate = span_tag.get_text(separator='\n', strip=True)
                            print(f"[scraper_debug] Gakujo P2: <dt>'{dt_tag.get_text(strip=True)}' に続く <dd><span> からテキスト取得: '{job_text_candidate[:100]}'")
                    
                    # それでも見つからなければ、dd全体のテキストを試す
                    if not job_text_candidate:
                        job_text_candidate = dd_tag.get_text(separator='\n', strip=True)
                        print(f"[scraper_debug] Gakujo P2: <dt>'{dt_tag.get_text(strip=True)}' に続く <dd> (spanなし) からテキスト取得: '{job_text_candidate[:100]}'")

                    if job_text_candidate: # 候補テキストがあればリストに追加
                        titles_from_pattern2_gakujo.append(job_text_candidate)
                        print(f"[scraper_debug] Gakujo P2: 職種候補リストに追加: '{job_text_candidate}'")
            
            # パターン1とパターン2で収集した職種情報を結合
            combined_titles_gakujo = []
            seen_titles_gakujo = set() # 重複除去用
            print(f"[scraper_debug] Gakujo 結合前: パターン1候補={titles_from_pattern1_gakujo}, パターン2候補={titles_from_pattern2_gakujo}")
            for title_list in [titles_from_pattern1_gakujo, titles_from_pattern2_gakujo]:
                for title_raw in title_list:
                    title = title_raw.strip() # 前後の空白除去
                    # 先頭または末尾の単独 "／" を除去
                    if title.startswith("／"):
                        title = title[1:].strip()
                    if title.endswith("／"):
                        title = title[:-1].strip()
                    
                    # 短すぎるもの、区切り線だけのもの、既に見たものは除外
                    if title and title != "---" and len(title) > 1 and title not in seen_titles_gakujo:
                        combined_titles_gakujo.append(title)
                        seen_titles_gakujo.add(title)
            
            if combined_titles_gakujo:
                data['job_title'] = "\n---\n".join(combined_titles_gakujo) # 複数の職種情報は区切り線で結合
                job_title_extracted_specifically = True
                print(f"[scraper_debug] gakujo.ne.jp の最終的な職種情報: '{data['job_title']}'")
            else: 
                print(f"[scraper_debug] gakujo.ne.jp 固有のロジックでは有効な職種情報が見つかりませんでした。")

        elif site_domain == "re-katsu.jp":
            print(f"[scraper_debug] re-katsu.jp 固有の職種抽出ロジックを適用します。")
            titles_to_combine_rekatsu = [] 
            seen_titles_rekatsu = set()

            # パターンA (re-katsu): SITE_SELECTORS に定義されたセレクタ (例: span#lblWantedJobType)
            selector_pattern_a = selectors_for_site.get("job_title") 
            if selector_pattern_a:
                tag_a = soup.select_one(selector_pattern_a)
                if tag_a:
                    title_a = tag_a.get_text(separator='\n', strip=True)
                    if title_a: # 空でなければ追加候補
                        titles_to_combine_rekatsu.append(title_a)
                        print(f"[scraper_debug] Re-katsu PA: セレクタ '{selector_pattern_a}' から職種候補取得: '{title_a}'")
                else:
                    print(f"[scraper_debug] Re-katsu PA: セレクタ '{selector_pattern_a}' に一致する要素が見つかりません。")
            else:
                print(f"[scraper_debug] Re-katsu PA: SITE_SELECTORSにjob_titleの定義がありません。")

            # パターンB (re-katsu): ページ上部の職種情報 (id="lblServIcon" を持つspan)
            selector_pattern_b = "span#lblServIcon" 
            print(f"[scraper_debug] Re-katsu PB: セレクタ '{selector_pattern_b}' で職種情報を試みます。")
            tag_b = soup.select_one(selector_pattern_b)
            if tag_b:
                title_b = tag_b.get_text(separator='\n', strip=True)
                if title_b: # 空でなければ追加候補
                    titles_to_combine_rekatsu.append(title_b)
                    print(f"[scraper_debug] Re-katsu PB: セレクタ '{selector_pattern_b}' から職種候補取得: '{title_b}'")
            else:
                print(f"[scraper_debug] Re-katsu PB: セレクタ '{selector_pattern_b}' に一致する要素が見つかりません。")

            # re-katsu.jp で収集した職種情報を結合
            final_titles_rekatsu = []
            for title_raw in titles_to_combine_rekatsu: # titles_to_combine_rekatsu を使用
                title = title_raw.strip()
                if title.startswith("／"):
                    title = title[1:].strip()
                if title.endswith("／"):
                    title = title[:-1].strip()
                if title and title != "---" and len(title) > 1 and title not in seen_titles_rekatsu:
                    final_titles_rekatsu.append(title)
                    seen_titles_rekatsu.add(title)

            if final_titles_rekatsu:
                data['job_title'] = "\n---\n".join(final_titles_rekatsu) 
                job_title_extracted_specifically = True
                print(f"[scraper_debug] re-katsu.jp の最終的な職種情報: '{data['job_title']}'")
            else:
                print(f"[scraper_debug] re-katsu.jp 固有のロジックでは有効な職種情報が見つかりませんでした。")
        
        # サイト固有ロジックで職種が取得できなかった場合、または未対応ドメインの場合のフォールバック処理
        if not job_title_extracted_specifically:
            # re-katsu30.jp など、上記以外のサイトはここでSITE_SELECTORSの"job_title"を試す
            if site_domain not in ["gakujo.ne.jp", "re-katsu.jp"]: 
                job_title_selector = selectors_for_site.get("job_title")
                print(f"[scraper_debug] ドメイン '{site_domain}' のプライマリ職種セレクタ '{job_title_selector}' を試みます。")
                if job_title_selector:
                    job_title_tag = soup.select_one(job_title_selector)
                    if job_title_tag:
                        data['job_title'] = job_title_tag.get_text(separator='\n', strip=True)
                        print(f"[scraper_debug] ドメイン '{site_domain}' のプライマリセレクタで職種取得: '{data['job_title']}'")
                    else:
                        print(f"[scraper_debug] ドメイン '{site_domain}' のプライマリセレクタ '{job_title_selector}' に一致する要素が見つかりません。")
                else:
                    print(f"[scraper_debug] ドメイン '{site_domain}' のSITE_SELECTORSにjob_titleの定義がありません。")

        # H1タグからの最終フォールバック (職種がまだ取得できていない場合)
        if not data['job_title']:
            print(f"[scraper_debug] サイト固有およびプライマリセレクタで職種取得失敗。H1タグからのフォールバックを試みます ({site_domain})。")
            generic_h1 = soup.find('h1')
            if generic_h1:
                h1_text = generic_h1.get_text(strip=True)
                # 特定サイトのH1が会社名であることが分かっている場合は、それを職種として採用しない
                if site_domain == "gakujo.ne.jp" and 'h1-company-name_inner' in generic_h1.get('class', []):
                     print(f"[scraper_debug] gakujo.ne.jp のH1タグは会社名 ('{h1_text}') のため、職種としては採用しません。")
                elif site_domain == "re-katsu.jp" and generic_h1.find("span", class_="head-catchcopy"):
                     # re-katsu.jpのH1内の特定spanは既に専用ロジックで試行済みのため、ここでは採用しないか、慎重に扱う
                     print(f"[scraper_debug] re-katsu.jp のH1タグ内の 'head-catchcopy' ('{generic_h1.find('span', class_='head-catchcopy').get_text(strip=True)}') は専用ロジックで処理済みのはずです。")
                # 上記以外で、H1が職種情報を含む可能性が低い場合は採用しない。
                # もしH1を汎用的に職種として採用する場合は以下のコメントを解除するが、誤判定が多い可能性がある。
                # else:
                #    data['job_title'] = h1_text
                #    print(f"[scraper_debug] H1タグから職種候補取得: '{data['job_title']}' (注意: 精度は低い可能性があります)")
            else:
                print(f"[scraper_debug] H1タグが見つかりませんでした。")
        
        if not data['job_title']:
            print(f"[scraper_debug] 全ての職種抽出試行が失敗しました。({site_domain}) Job title は None のままです。")

        # --- 給与 (salary)、勤務地 (location)、応募資格 (qualifications) の抽出 ---
        # これらは既存のSITE_SELECTORS定義に基づいて抽出を試みる
        for field_key in ["salary", "location", "qualifications"]:
            selector = selectors_for_site.get(field_key)
            print(f"[scraper_debug] フィールド '{field_key}' のセレクタ '{selector}' で抽出を試みます。")
            if selector:
                tag = soup.select_one(selector)
                if tag:
                    # re-katsuサイト特有の不要なh3見出し除去（もしあれば）
                    if (site_domain == "re-katsu.jp" or site_domain == "re-katsu30.jp") and tag.find("h3"):
                        tag.find("h3").decompose()
                        print(f"[scraper_debug] フィールド '{field_key}' のre-katsu系サイト用h3見出しを除去しました。")
                    data[field_key] = tag.get_text(separator='\n', strip=True)
                    print(f"[scraper_debug] フィールド '{field_key}' 取得成功: '{data[field_key][:100] if data[field_key] else 'None'}...'" )
                else:
                    print(f"[scraper_debug] フィールド '{field_key}' のセレクタ '{selector}' に一致する要素が見つかりません。")
            else:
                print(f"[scraper_debug] フィールド '{field_key}' のセレクタがSITE_SELECTORSに定義されていません。")

        # --- 全文テキスト (full_text) の抽出 ---
        full_text_area_selector = selectors_for_site.get("full_text_area")
        print(f"[scraper_debug] 全文テキストエリアのセレクタ '{full_text_area_selector}' で抽出を試みます。")
        if full_text_area_selector:
            full_text_content_area = soup.select_one(full_text_area_selector)
            if full_text_content_area:
                data['full_text'] = full_text_content_area.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] 全文テキストをセレクタで取得しました。文字数: {len(data['full_text'])}")
            else:
                print(f"[scraper_debug] 全文テキストエリアのセレクタ '{full_text_area_selector}' に一致する要素が見つかりません。ページ全体のテキストを取得します。")
                data['full_text'] = soup.get_text(separator='\n', strip=True)
                print(f"[scraper_debug] 全文テキスト (フォールバック) の文字数: {len(data['full_text'])}")
        else:
            print(f"[scraper_debug] 全文テキストエリアのセレクタが定義されていません。ページ全体のテキストを取得します。")
            data['full_text'] = soup.get_text(separator='\n', strip=True)
            print(f"[scraper_debug] 全文テキスト (フォールバック) の文字数: {len(data['full_text'])}")

    print(f"[scraper_debug] 最終的に抽出された職種: '{data['job_title']}'")
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
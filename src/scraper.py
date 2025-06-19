import requests
from bs4 import BeautifulSoup
import urllib.parse

def get_html_content(url: str, headers: dict | None = None) -> str | None:
    """Fetches HTML content from a URL.

    Args:
        url: The URL to fetch content from.
        headers: Optional dictionary of HTTP Headers to send with the request.

    Returns:
        The HTML content as a string if successful, otherwise None.
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        print(f"Error: The request to {url} timed out.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error occurred while fetching {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def extract_image_urls(html_content: str, base_url: str) -> list[str]:
    """Extracts all absolute image URLs from HTML content.

    Args:
        html_content: The HTML content as a string.
        base_url: The base URL for resolving relative image URLs.

    Returns:
        A list of absolute image URLs.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls = []
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if src:
            absolute_url = urllib.parse.urljoin(base_url, src)
            image_urls.append(absolute_url)
    return image_urls

def perform_ocr_on_image(image_url: str) -> str:
    """Simulates performing OCR on an image.

    Args:
        image_url: The URL of the image to process.

    Returns:
        Placeholder text representing the OCR result.
    """
    print(f"Simulating OCR for image: {image_url}")
    return f"Mock OCR text for {image_url}"

def extract_text_from_html(html_content: str, base_url: str) -> dict[str, any]:
    """
    Extracts specific job details, all available text, and simulated OCR text from images.
    Args:
        html_content: The HTML content as a string.
        base_url: The base URL for resolving relative image URLs.

    Returns:
        A dictionary containing various extracted data fields.
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

    title_tag = soup.find('h1')
    if title_tag:
        data['job_title'] = title_tag.get_text(strip=True)

    salary_th = soup.find('th', string=lambda t: t and '給与' in t)
    if salary_th and salary_th.find_next_sibling('td'):
        data['salary'] = salary_th.find_next_sibling('td').get_text(strip=True)

    location_th = soup.find('th', string=lambda t: t and '勤務地' in t)
    if location_th and location_th.find_next_sibling('td'):
        data['location'] = location_th.find_next_sibling('td').get_text(strip=True)

    qualifications_th = soup.find('th', string=lambda t: t and ('応募資格' in t or '対象となる方' in t))
    if qualifications_th and qualifications_th.find_next_sibling('td'):
        data['qualifications'] = qualifications_th.find_next_sibling('td').get_text(strip=True)

    data['full_text'] = soup.get_text(separator=' ', strip=True)

    image_urls = extract_image_urls(html_content, base_url)
    for img_url in image_urls:
        ocr_text = perform_ocr_on_image(img_url)
        data['image_ocr_texts'].append(ocr_text)

    return data

def integrate_all_text(extracted_data: dict) -> str:
    """
    Integrates full_text and image_ocr_texts into a single string.

    Args:
        extracted_data: The dictionary returned by extract_text_from_html.

    Returns:
        A single string combining all text parts, separated by double newlines.
    """
    text_parts = []

    full_text = extracted_data.get('full_text')
    if full_text: # Ensure it's not None and not empty
        text_parts.append(full_text)

    image_ocr_texts = extracted_data.get('image_ocr_texts')
    if image_ocr_texts: # Ensure it's not None and not empty
        for ocr_text in image_ocr_texts:
            if ocr_text: # Ensure individual OCR text is not None/empty
                text_parts.append(ocr_text)

    return "\n\n".join(text_parts)

if __name__ == "__main__":
    sample_url = "https://www.gakujo.ne.jp/campus/company/employ/82098/?prv=ON&WINTYPE=%27SUB%27"
    # sample_url = "https://www.wikipedia.org/" # For testing with images

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    print(f"Fetching URL: {sample_url}")
    html_content = get_html_content(sample_url, headers=headers)

    if html_content:
        print("\nAttempting to extract data...")
        extracted_info = extract_text_from_html(html_content, sample_url)

        print("\nExtracted Data (Details):")
        specific_fields_found = False
        for key, value in extracted_info.items():
            if key == "image_ocr_texts":
                print(f"  {key.replace('_', ' ').capitalize()}:")
                if value: # If list is not empty
                    for item in value:
                        print(f"    - {item}")
                else:
                    print("    No images found or processed for OCR.")
            else:
                display_value = value[:200] + '...' if value and key == 'full_text' and isinstance(value, str) and len(value) > 200 else value
                print(f"  {key.replace('_', ' ').capitalize()}: {display_value}")

            if key not in ["full_text", "image_ocr_texts"] and value is not None:
                specific_fields_found = True

        if not specific_fields_found and not extracted_info.get("image_ocr_texts"): # Adjusted condition
            print("\n  Note: None of the specific job details were found, and no images were processed for OCR.")
            print("  This often indicates that the content is loaded dynamically by JavaScript.")
            print("  The 'Full text' field (if populated) shows text from the initial HTML response.")

        # Integrate and print all text
        print("\n--- Integrated Full Text ---")
        integrated_text = integrate_all_text(extracted_info)
        if integrated_text:
            print(integrated_text)
        else:
            print("No text content (HTML or OCR) was extracted to integrate.")

    else:
        print("Failed to retrieve HTML content.")

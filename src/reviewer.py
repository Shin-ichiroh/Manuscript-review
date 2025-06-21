import math

# Using relative import for modules within the same package (src)
from .rule_processor import get_mock_vector, load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks

REVIEW_PROMPT_TEMPLATE = """\
### 命令
あなたは、求人広告の基準や原稿審査マニュアルに従って原稿を審査し、不適切な表現や不足している項目などを指摘するエージェントです。
審査ルールに基づいて入力情報を審査し、問題がある場合、その問題点を具体的に指摘してください。

### 制約条件
* 問題点がある場合のみ、出力形式に従って問題点を指摘してください。
* 問題がない場合は、何も出力しないでください。
* 指摘は、問題点がある箇所、問題の内容、そして修正提案を簡潔に記述してください。
* 審査ルールに記載されていない問題は指摘しないでください。

### 審査ルール
{relevant_rules}

### 入力情報
求人原稿URL: {job_post_url}
職種: {job_title}
給与: {salary}
勤務地: {location}
応募資格: {qualifications}
求人原稿のその他全文テキスト: {full_text_content}

### 出力
・**問題点がある箇所**: （例：給与欄、応募資格欄など）
・**問題の内容**: （例：最低賃金の記載がありません。固定残業代に関する必須項目3点の記載がありません。など）
・**修正提案**: （例：月給25万円以上のように最低保証額を記載してください。固定残業代の金額、充当時間数、超過分の追加支給について明記してください。など）
"""

def simulate_rag_retrieval(job_post_vector: list[float], rulebook_vector_db: list[dict], num_relevant_rules: int = 3) -> str:
    """
    Simulates retrieving relevant rules from the vector database.
    """
    scored_rules = []
    for rule_chunk in rulebook_vector_db:
        rule_vector = rule_chunk.get('vector')
        if not rule_vector or len(rule_vector) != len(job_post_vector):
            continue

        distance = sum(abs(v1 - v2) for v1, v2 in zip(job_post_vector, rule_vector))
        scored_rules.append({'rule_text': rule_chunk['rule_text'], 'score': distance})

    scored_rules.sort(key=lambda x: x['score'])

    relevant_rules_texts = [chunk['rule_text'] for chunk in scored_rules[:num_relevant_rules]]

    return "\n\n---\n\n".join(relevant_rules_texts)

def simulate_ai_call(prompt: str) -> str:
    """
    Simulates calling an AI model with the assembled prompt.
    """
    print("\n--- SIMULATING AI CALL WITH PROMPT (first 600 chars): ---") # Increased length for better visibility
    print(prompt[:600] + "..." if len(prompt) > 600 else prompt)
    print("--- END OF SIMULATED PROMPT ---")

    import random
    if random.random() < 0.5: # Return a mock violation about 50% of the time
        return """\
・**問題点がある箇所**: 給与セクション (シミュレーション)
・**問題の内容**: 「月給20万円」とのみ記載されていますが、最低賃金の明示方法として、手当が含まれる場合はその内訳（例：一律〇〇手当）を明記する必要があります。また、固定残業代が含まれる場合は、その金額、充当時間数、超過分の追加支給の旨の3点の記載が必須です。(シミュレーションによる指摘)
・**修正提案**: 例：「月給20万円（基本給18万円 + 一律住宅手当2万円）」のように手当内訳を明記してください。固定残業代が含まれる場合は、「固定残業代〇円（〇時間分）を含む。超過分は別途支給。」のように3点を明記してください。(シミュレーションによる提案)"""
    else:
        return "審査の結果、問題は見つかりませんでした。(シミュレーション)"

def perform_review(
    job_post_url: str,
    job_title: str | None,
    salary: str | None,
    location: str | None,
    qualifications: str | None,
    full_text_content: str | None, # This will be the integrated text from scraper
    rulebook_vector_db: list[dict]
) -> str:
    """
    Performs a simulated review of the job post using structured data and full text.
    """
    print(f"\n--- Starting review for job post from URL: {job_post_url} ---")

    # Use full_text_content for RAG vectorization
    text_for_rag = full_text_content if full_text_content is not None else ""
    job_post_vector = get_mock_vector(text_for_rag)
    print(f"Generated mock vector for RAG based on full_text_content (first 100 chars): {text_for_rag[:100]}...")

    retrieved_rules_text = simulate_rag_retrieval(job_post_vector, rulebook_vector_db)
    if not retrieved_rules_text:
        retrieved_rules_text = "関連するルールは見つかりませんでした。" # Fallback
    print(f"\n--- Retrieved relevant rules (first 200 chars): ---\n{retrieved_rules_text[:200]}...\n")

    # Prepare data for formatting the prompt
    prompt_data = {
        "job_post_url": job_post_url if job_post_url else "N/A",
        "job_title": job_title if job_title else "N/A",
        "salary": salary if salary else "N/A",
        "location": location if location else "N/A",
        "qualifications": qualifications if qualifications else "N/A",
        "full_text_content": full_text_content if full_text_content else "N/A", # This is the integrated text
        "relevant_rules": retrieved_rules_text
    }
    assembled_prompt = REVIEW_PROMPT_TEMPLATE.format(**prompt_data)

    ai_response = simulate_ai_call(assembled_prompt)
    return ai_response

if __name__ == "__main__":
    print("--- Reviewer Self-Test with Structured Data ---")

    # 1. Load and process the rulebook
    # Path is relative to src/ when running `python src/reviewer.py`
    # For this to work, rulebook.md must be accessible, e.g. in parent dir.
    # And rule_processor.py must be importable.
    print("Initializing Reviewer System for self-test...")
    try:
        rulebook_content = load_rulebook("../rulebook.md")
        if rulebook_content.startswith("Error:") or rulebook_content.startswith("An unexpected error occurred:"):
            print(f"Failed to load rulebook for self-test: {rulebook_content}")
            rulebook_vector_db = []
        else:
            print("Rulebook loaded successfully for self-test.")
            parsed_chunks = parse_rulebook_to_chunks(rulebook_content)
            print(f"Parsed {len(parsed_chunks)} rule chunks for self-test.")
            rulebook_vector_db = add_mock_vectors_to_chunks(parsed_chunks)
            print(f"Added mock vectors to {len(rulebook_vector_db)} chunks for self-test.")
    except Exception as e:
        print(f"Error during rulebook processing in self-test: {e}")
        rulebook_vector_db = []


    if not rulebook_vector_db:
        print("Cannot proceed with self-test without a rulebook vector database.")
    else:
        # 2. Define sample structured data
        sample_url = "http://example.com/job/test123"
        sample_title = "テストエンジニア"
        sample_salary = "月給30万円 (スキル・経験により応相談)"
        sample_location = "東京都千代田区"
        sample_qualifications = "テスト経験3年以上、自動化スキル尚可"
        sample_full_text = "これはテスト求人の全文です。\n職種：テストエンジニア\n給与：月給30万円\n勤務地：東京都千代田区\n応募資格：テスト経験3年以上。\nその他詳細多数..." # This would be the integrated text in a real scenario

        # 3. Perform the review
        review_result = perform_review(
            job_post_url=sample_url,
            job_title=sample_title,
            salary=sample_salary,
            location=sample_location,
            qualifications=sample_qualifications,
            full_text_content=sample_full_text, # Pass the integrated full text here
            rulebook_vector_db=rulebook_vector_db
        )

        # 4. Print the result
        print("\n--- SELF-TEST FINAL REVIEW RESULT ---")
        print(review_result)
        print("--- END OF SELF-TEST REVIEW ---")

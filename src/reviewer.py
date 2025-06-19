import math # For vector distance calculation if needed, though sum of abs diff is simpler

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

### 入力情報（求人原稿テキスト）
{job_post_text}

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
            # Skip if vector is missing or mismatched dimension (should not happen with mock data)
            continue

        # Calculate sum of absolute differences (Manhattan distance)
        # Lower score means more similar for this metric
        distance = sum(abs(v1 - v2) for v1, v2 in zip(job_post_vector, rule_vector))
        scored_rules.append({'rule_text': rule_chunk['rule_text'], 'score': distance})

    # Sort by score (ascending, as lower distance is better)
    scored_rules.sort(key=lambda x: x['score'])

    relevant_rules_texts = [chunk['rule_text'] for chunk in scored_rules[:num_relevant_rules]]

    return "\n\n---\n\n".join(relevant_rules_texts) # Separate rules for clarity

def simulate_ai_call(prompt: str) -> str:
    """
    Simulates calling an AI model with the assembled prompt.
    """
    print("\n--- SIMULATING AI CALL WITH PROMPT (first 500 chars): ---")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("--- END OF SIMULATED PROMPT ---")

    # For demonstration, let's return a mock violation sometimes
    # This can be made more sophisticated, e.g., based on prompt content
    import random
    if random.random() < 0.5:
        return """\
・**問題点がある箇所**: 給与セクション
・**問題の内容**: 「月給20万円」とのみ記載されていますが、最低賃金の明示方法として、手当が含まれる場合はその内訳（例：一律〇〇手当）を明記する必要があります。また、固定残業代が含まれる場合は、その金額、充当時間数、超過分の追加支給の旨の3点の記載が必須です。
・**修正提案**: 例：「月給20万円（基本給18万円 + 一律住宅手当2万円）」のように手当内訳を明記してください。固定残業代が含まれる場合は、「固定残業代〇円（〇時間分）を含む。超過分は別途支給。」のように3点を明記してください。"""
    else:
        return "審査の結果、問題は見つかりませんでした。"

def perform_review(job_post_text: str, rulebook_vector_db: list[dict]) -> str:
    """
    Performs a simulated review of the job post text against the rulebook.
    """
    print(f"\n--- Starting review for job post: ---\n{job_post_text[:200]}...\n")

    job_post_vector = get_mock_vector(job_post_text)
    print(f"Generated mock vector for job post: {job_post_vector}")

    retrieved_rules_text = simulate_rag_retrieval(job_post_vector, rulebook_vector_db)
    if not retrieved_rules_text:
        retrieved_rules_text = "関連するルールは見つかりませんでした。" # Fallback if no rules found
    print(f"\n--- Retrieved relevant rules (first 200 chars): ---\n{retrieved_rules_text[:200]}...\n")

    final_prompt = REVIEW_PROMPT_TEMPLATE.format(
        relevant_rules=retrieved_rules_text,
        job_post_text=job_post_text
    )

    ai_response = simulate_ai_call(final_prompt)
    return ai_response

if __name__ == "__main__":
    print("--- Initializing Reviewer System ---")

    # 1. Load and process the rulebook
    # Assuming rulebook.md is in the parent directory of src/
    rulebook_content = load_rulebook("../rulebook.md")
    if rulebook_content.startswith("Error:") or rulebook_content.startswith("An unexpected error occurred:"):
        print(f"Failed to load rulebook: {rulebook_content}")
        rulebook_vector_db = []
    else:
        print("Rulebook loaded successfully.")
        parsed_chunks = parse_rulebook_to_chunks(rulebook_content)
        print(f"Parsed {len(parsed_chunks)} rule chunks.")
        rulebook_vector_db = add_mock_vectors_to_chunks(parsed_chunks)
        print(f"Added mock vectors to {len(rulebook_vector_db)} chunks.")

    if not rulebook_vector_db:
        print("Cannot proceed without a rulebook vector database.")
    else:
        # 2. Create a sample job post
        sample_job_post_text = "これはテスト用の求人原稿です。月給20万円。住宅手当あり。詳細はウェブで。"

        # 3. Perform the review
        review_result = perform_review(sample_job_post_text, rulebook_vector_db)

        # 4. Print the result
        print("\n--- FINAL REVIEW RESULT ---")
        print(review_result)
        print("--- END OF REVIEW ---")

        # Test with a slightly different job post
        sample_job_post_text_2 = "急募！エンジニア募集。月給30万円以上。経験者優遇。交通費支給。"
        review_result_2 = perform_review(sample_job_post_text_2, rulebook_vector_db)
        print("\n--- FINAL REVIEW RESULT 2 ---")
        print(review_result_2)
        print("--- END OF REVIEW 2 ---")

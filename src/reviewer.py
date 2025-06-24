import math
import os

# OpenAI imports
from openai import AzureOpenAI

# Using relative import for modules within the same package (src)
# from .rule_processor import get_mock_vector, load_rulebook, parse_rulebook_to_chunks, add_mock_vectors_to_chunks
# NOTE: Temporarily commented out. Needed for full perform_review functionality (RAG).

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

def get_azure_openai_credentials() -> dict | None:
    """
    Retrieves Azure OpenAI API credentials from environment variables.
    Returns:
        A dictionary with credentials if all are found, otherwise None.
    """
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_version = os.environ.get("OPENAI_API_VERSION")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

    missing_vars = []
    if not api_key:
        missing_vars.append("AZURE_OPENAI_API_KEY")
    if not azure_endpoint:
        missing_vars.append("AZURE_OPENAI_ENDPOINT")
    if not api_version:
        missing_vars.append("OPENAI_API_VERSION")
    if not deployment_name:
        missing_vars.append("AZURE_OPENAI_DEPLOYMENT_NAME")

    if missing_vars:
        print("Error: Missing one or more Azure OpenAI environment variables.")
        print("Please ensure the following are set:")
        for var_name in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT_NAME"]:
            is_set = bool(os.environ.get(var_name))
            value_display = "Present (value hidden)" if var_name == "AZURE_OPENAI_API_KEY" and is_set else os.environ.get(var_name, "MISSING")
            print(f"- {var_name}: {value_display}")
        return None

    return {
        "api_key": api_key,
        "azure_endpoint": azure_endpoint,
        "api_version": api_version,
        "deployment_name": deployment_name,
    }

def call_actual_llm_api(prompt_text: str, credentials: dict, max_tokens: int = 1500, temperature: float = 0.7) -> str | None:
    """
    Calls the Azure OpenAI API to get a completion for the given prompt.
    """
    print("\nAttempting to call Azure OpenAI API...")

    try:
        client = AzureOpenAI(
            api_key=credentials["api_key"],
            azure_endpoint=credentials["azure_endpoint"],
            api_version=credentials["api_version"]
        )
        print("AzureOpenAI client initialized successfully.")
    except Exception as e:
        print(f"Error initializing AzureOpenAI client: {e}")
        return None

    try:
        print(f"Sending request to Azure OpenAI: deployment='{credentials['deployment_name']}', max_tokens={max_tokens}, temperature={temperature}")
        chat_completion = client.chat.completions.create(
            model=credentials["deployment_name"],
            messages=[
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        response_content = chat_completion.choices[0].message.content
        print("Azure OpenAI API call successful.")
        return response_content

    except Exception as e:
        print(f"Error during Azure OpenAI API call: {e}")
        return None

def simulate_rag_retrieval(job_post_vector: list[float] | None, rulebook_vector_db: list[dict], num_relevant_rules: int = 3) -> str:
    """
    Simulates retrieving relevant rules. Handles case where job_post_vector might be None if get_mock_vector isn't available.
    """
    if job_post_vector is None: # If get_mock_vector could not be imported/used
        return "（RAG FAILED: Mock vector generation skipped due to missing dependencies）"

    scored_rules = []
    for rule_chunk in rulebook_vector_db:
        rule_vector = rule_chunk.get('vector')
        if not rule_vector or len(rule_vector) != len(job_post_vector):
            continue
        distance = sum(abs(v1 - v2) for v1, v2 in zip(job_post_vector, rule_vector))
        scored_rules.append({'rule_text': rule_chunk['rule_text'], 'score': distance})

    if not scored_rules:
        return "関連するルールは見つかりませんでした（RAG DB 空またはベクトル不一致）。"

    scored_rules.sort(key=lambda x: x['score'])
    relevant_rules_texts = [chunk['rule_text'] for chunk in scored_rules[:num_relevant_rules]]
    return "\n\n---\n\n".join(relevant_rules_texts)

def simulate_ai_call(prompt: str) -> str:
    """
    Simulates an AI call, used as a fallback.
    """
    print("\n--- SIMULATING AI CALL (FALLBACK) WITH PROMPT (first 600 chars): ---")
    print(prompt[:600] + "..." if len(prompt) > 600 else prompt)
    print("--- END OF SIMULATED PROMPT (FALLBACK) ---")

    import random
    if random.random() < 0.5:
        return """\
・**問題点がある箇所**: 給与セクション (シミュレーション fallback)
・**問題の内容**: 最低賃金の明示方法に問題あり。(シミュレーション fallback)
・**修正提案**: 適切な形式で記載してください。(シミュレーション fallback)"""
    else:
        return "審査の結果、問題は見つかりませんでした。(シミュレーション fallback)"

def perform_review(
    job_post_url: str,
    job_title: str | None,
    salary: str | None,
    location: str | None,
    qualifications: str | None,
    full_text_content: str | None,
    rulebook_vector_db: list[dict] # This would ideally be populated by rule_processor functions
) -> str:
    print(f"\n--- Starting review for job post from URL: {job_post_url} ---")

    text_for_rag = full_text_content if full_text_content is not None else ""

    # Attempt to use get_mock_vector if available (it won't be if imports are commented)
    job_post_vector = None
    try:
        # This will only work if the import is active and rule_processor is found
        from .rule_processor import get_mock_vector as actual_get_mock_vector
        job_post_vector = actual_get_mock_vector(text_for_rag)
        print(f"Generated mock vector for RAG using rule_processor.get_mock_vector (first 100 chars of text): {text_for_rag[:100]}...")
    except ImportError:
        print("Warning: rule_processor.get_mock_vector not available for RAG vector generation in this context.")
        # Create a dummy vector if get_mock_vector is not available
        job_post_vector = [0.0] * 10 # Placeholder vector
        print(f"Using placeholder vector for RAG. Text (first 100 chars): {text_for_rag[:100]}...")


    retrieved_rules_text = simulate_rag_retrieval(job_post_vector, rulebook_vector_db)
    if not retrieved_rules_text or retrieved_rules_text.startswith("（RAG FAILED") or retrieved_rules_text.startswith("関連するルールは見つかりませんでした"):
        print(f"\n--- RAG problem or no rules found: ---\n{retrieved_rules_text}\n")
        # Provide a default rules text if RAG fails completely or returns no rules
        if not retrieved_rules_text.strip() or retrieved_rules_text.startswith("（RAG FAILED") or retrieved_rules_text.startswith("関連するルールは見つかりませんでした"):
             retrieved_rules_text = "関連する審査ルールを特定できませんでした。一般的な注意点に基づいて審査します。"
    else:
        print(f"\n--- Retrieved relevant rules (first 200 chars): ---\n{retrieved_rules_text[:200]}...\n")

    prompt_data = {
        "job_post_url": job_post_url if job_post_url else "N/A",
        "job_title": job_title if job_title else "N/A",
        "salary": salary if salary else "N/A",
        "location": location if location else "N/A",
        "qualifications": qualifications if qualifications else "N/A",
        "full_text_content": full_text_content if full_text_content else "N/A",
        "relevant_rules": retrieved_rules_text
    }
    assembled_prompt = REVIEW_PROMPT_TEMPLATE.format(**prompt_data)

    review_result = None
    azure_credentials = get_azure_openai_credentials()

    if azure_credentials:
        print("\n--- Attempting Real LLM Call via Azure OpenAI ---")
        actual_llm_response = call_actual_llm_api(assembled_prompt, azure_credentials)
        if actual_llm_response:
            review_result = actual_llm_response
        else:
            print("Real LLM call failed. Falling back to simulation.")
            sim_response = simulate_ai_call(assembled_prompt)
            review_result = f"[REAL API CALL FAILED] {sim_response}"
    else:
        # get_azure_openai_credentials() already prints the error about missing vars
        print("\n--- Azure OpenAI credentials not found. Falling back to simulation. ---")
        review_result = simulate_ai_call(assembled_prompt)

    return review_result if review_result is not None else "Review process failed to produce a result."


if __name__ == "__main__":
    print("--- Reviewer Self-Test: Azure OpenAI Call & Fallback Logic ---")

    # Test credential retrieval
    azure_credentials_test = get_azure_openai_credentials()

    if azure_credentials_test:
        print("\nAzure OpenAI credentials FOUND for self-test.")
        print(f"  API Key: Present")
        print(f"  Azure Endpoint: {azure_credentials_test['azure_endpoint']}")
        print(f"  API Version: {azure_credentials_test['api_version']}")
        print(f"  Deployment Name: {azure_credentials_test['deployment_name']}")
    else:
        print("\nAzure OpenAI credentials NOT FOUND for self-test. API call will be skipped by perform_review, forcing fallback.")

    # Define sample structured data for perform_review
    sample_url = "http://example.com/job/self_test"
    sample_title = "テストポジション"
    sample_salary = "月給 25万円"
    sample_location = "東京本社"
    sample_qualifications = "経験不問、学習意欲のある方"
    sample_full_text = "これは自己テスト用の求人広告の全文です。職種はテストポジション、給与は月給25万円。勤務地は東京本社です。応募資格は経験不問ですが、学習意欲のある方を歓迎します。その他、福利厚生も充実しています。"

    # Simulate an empty rulebook_vector_db as rule_processor is not imported here
    mock_rulebook_vector_db = []
    # To make RAG slightly more interesting if it could run, we could add a dummy chunk:
    # mock_rulebook_vector_db = [{"rule_text": "テストルール1: 全ての項目は明確に記載すること。", "vector": [0.0]*10}]


    print("\nCalling perform_review (will attempt real API if creds were found, else simulate)...")
    # perform_review will call get_azure_openai_credentials() again internally
    review_output = perform_review(
        job_post_url=sample_url,
        job_title=sample_title,
        salary=sample_salary,
        location=sample_location,
        qualifications=sample_qualifications,
        full_text_content=sample_full_text,
        rulebook_vector_db=mock_rulebook_vector_db
    )

    print("\n--- SELF-TEST FINAL REVIEW OUTPUT ---")
    print(review_output)
    print("--- END OF SELF-TEST ---")

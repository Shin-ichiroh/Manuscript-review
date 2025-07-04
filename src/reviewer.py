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
* 軽微な表現の揺れも検知してください。

### 特に注意すべき確認事項
以下の点について特に注意深く確認し、該当する場合は指摘事項に含めてください：
- **固定残業制について**:
    - 固定残業代制度を採用している場合、1. 固定残業代の金額、2. その金額に充当する労働時間数、3. 固定残業代を超える労働を行った場合は追加支給する旨、の3点が明確に記載されているか。
    - 固定残業時間が月45時間を超える場合は、三六協定に関する適切な注釈（特別条項付き三六協定の締結など）が記載されているか。
- **勤務時間について**:
    - 始業・終業時刻、実働時間、休憩時間が具体的に明記されているか。「実働8時間」のような記載だけでなく、具体的な時刻の記載が必要か確認してください。
- **給与について**:
    - 複数の勤務地が記載されている場合、勤務地ごとの給与体系が明確に示されているか、あるいは全勤務地共通の給与である旨が明記されているか。勤務地のリストと給与情報の間に矛盾や記載漏れがないか。
- **試用期間について**:
    - 試用期間が設定されており、かつ本採用時と労働条件（給与等）が異なる場合、1. 異なる条件の内容、2. それ以外の条件に変更はない旨、の両方が明記されているか。
- **改正職業安定法に基づく明示事項**:
    - 「従事すべき業務の変更の範囲」が具体的に記載されているか。
- **差別的表現・不適切な表現について**:
    - 応募者の出身地、居住地、性別、年齢（法令で許可される場合を除く）を不当に限定する表現（例：「○○県出身者歓迎」）がないか。
    - 「笑顔が素敵」「明るい性格」のような、応募者の性格や容姿に関する主観的な表現や、業務遂行能力と直接関連しない特性を求める記述がないか。もしあれば、客観的なスキルや経験に基づく表現への修正を提案すること。
- **受動喫煙対策について**:
    - 就業場所における受動喫煙を防止するための具体的な措置（例：屋内禁煙、喫煙専用室設置など）が明記されているか。「対策なし」という記載だけでは不十分な場合がある。
- **原稿内情報の整合性について**:
    - 求人広告内の複数箇所（例：広告上部のサマリーと詳細な募集要項）で、勤務地、職種、給与などの情報に矛盾がないか。
- **給与（特定地域での記載漏れチェック）**: リストアップされた全ての勤務地（特に「北海道」のような具体的な地域名が明記されている場合）について、対応する給与情報が明確に記載されているか、記載漏れがないか、特に注意して確認してください。
- **試用期間の詳細**: 試用期間の定めがあり、かつ本採用時と労働条件（給与、勤務時間など）が異なる場合、その全ての相違点、及び『その他の労働条件は本採用時と変更なし』といった趣旨の記載が明確にされているか、厳密に確認してください。
- **業務の変更の範囲 (再確認)**: 改正職業安定法に基づき、「従事すべき業務の変更の範囲」に関する具体的な記載が求人情報に含まれているか、必ず確認してください。記載が全くない場合は指摘が必要です。
- **勤務地情報の整合性 (P.3.1 version)**: 求人情報内で勤務地が複数回（例：広告ヘッダー、概要セクション、募集要項詳細など）記載されている場合、それら全ての勤務地情報が完全に一致しているか、矛盾や食い違いがないか、詳細に比較・確認してください。
- **主観的表現の再チェック (P.3.1 version)**: 人事担当者のコメント等で、『○○な方』『○○力がある方』といった表現が使われている場合、それが具体的な業務スキルや測定可能な経験に基づいているか、それとも『笑顔が素敵』『高いコミュニケーション能力』のような定義が曖昧で主観に左右される可能性のある表現か、再度厳しくチェックしてください。後者の場合は、客観的基準への修正を促す指摘を検討してください。

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
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_version = os.environ.get("OPENAI_API_VERSION")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
    if not (api_key and azure_endpoint and api_version and deployment_name):
        return None
    return {
        "api_key": api_key, "azure_endpoint": azure_endpoint,
        "api_version": api_version, "deployment_name": deployment_name,
    }

def call_actual_llm_api(prompt_text: str, credentials: dict, max_tokens: int = 1500, temperature: float = 0.7) -> str | None:
    try:
        client = AzureOpenAI(
            api_key=credentials["api_key"], azure_endpoint=credentials["azure_endpoint"], api_version=credentials["api_version"]
        )
    except Exception as e:
        return None
    try:
        chat_completion = client.chat.completions.create(
            model=credentials["deployment_name"], messages=[{"role": "user", "content": prompt_text}],
            max_tokens=max_tokens, temperature=temperature,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print("-" * 50); print("[call_actual_llm_api] ERROR: An exception occurred during Azure OpenAI API call.")
        print(f"[call_actual_llm_api] Exception Type: {type(e).__name__}"); print(f"[call_actual_llm_api] Exception Args: {e.args}"); print(f"[call_actual_llm_api] Exception Str: {str(e)}")
        if hasattr(e, 'http_status'): print(f"[call_actual_llm_api] HTTP Status: {e.http_status}")
        if hasattr(e, 'code'): print(f"[call_actual_llm_api] Error Code: {e.code}")
        print("-" * 50)
        return None

def simulate_rag_retrieval(job_post_vector: list[float] | None, rulebook_vector_db: list[dict], num_relevant_rules: int = 3) -> str:
    if job_post_vector is None: return "（RAG FAILED: Mock vector generation skipped or failed）"
    scored_rules = []
    for rule_chunk in rulebook_vector_db:
        rule_vector = rule_chunk.get('vector')
        if not rule_vector or len(rule_vector) != len(job_post_vector): continue
        distance = sum(abs(v1 - v2) for v1, v2 in zip(job_post_vector, rule_vector))
        scored_rules.append({'rule_text': rule_chunk['rule_text'], 'score': distance})
    if not scored_rules: return "関連するルールは見つかりませんでした（RAG DB 空またはベクトル不一致）。"
    scored_rules.sort(key=lambda x: x['score'])
    return "\n\n---\n\n".join([chunk['rule_text'] for chunk in scored_rules[:num_relevant_rules]])

def simulate_ai_call(prompt: str) -> str:
    print("\n--- SIMULATING AI CALL (FALLBACK) WITH PROMPT (first 1800 chars): ---")
    print(prompt[:1800] + "..." if len(prompt) > 1800 else prompt)
    print("--- END OF SIMULATED PROMPT (FALLBACK) ---")
    import random
    if random.random() < 0.5: return "・**問題点がある箇所**: 給与セクション (シミュレーション fallback)\n・**問題の内容**: 最低賃金の明示方法に問題あり。(シミュレーション fallback)\n・**修正提案**: 適切な形式で記載してください。(シミュレーション fallback)"
    else: return "審査の結果、問題は見つかりませんでした。(シミュレーション fallback)"

def perform_review(
    job_post_url: str, job_title: str | None, salary: str | None, location: str | None,
    qualifications: str | None, full_text_content: str | None, rulebook_vector_db: list[dict]
) -> str:
    text_for_rag_parts = []
    if job_title: text_for_rag_parts.append(f"職種: {job_title}")
    if salary: text_for_rag_parts.append(f"給与: {salary}")
    if location: text_for_rag_parts.append(f"勤務地: {location}")
    if qualifications: text_for_rag_parts.append(f"応募資格: {qualifications}")
    if text_for_rag_parts and full_text_content: text_for_rag_parts.append("\n---\n本文:")
    if full_text_content: text_for_rag_parts.append(full_text_content)
    text_for_rag = "\n".join(text_for_rag_parts).strip() if text_for_rag_parts else "求人情報なし"

    job_post_vector = None
    try:
        from .rule_processor import get_mock_vector as actual_get_mock_vector
        job_post_vector = actual_get_mock_vector(text_for_rag)
    except ImportError:
        job_post_vector = [0.0] * 10

    retrieved_rules_text = simulate_rag_retrieval(job_post_vector, rulebook_vector_db)
    if not retrieved_rules_text.strip() or retrieved_rules_text.startswith("（RAG FAILED") or retrieved_rules_text.startswith("関連するルールは見つかりませんでした"):
        retrieved_rules_text = "関連する審査ルールを特定できませんでした。一般的な注意点に基づいて審査します。"

    prompt_data = {
        "job_post_url": job_post_url or "N/A", "job_title": job_title or "N/A", "salary": salary or "N/A",
        "location": location or "N/A", "qualifications": qualifications or "N/A",
        "full_text_content": full_text_content or "N/A", "relevant_rules": retrieved_rules_text
    }
    assembled_prompt = REVIEW_PROMPT_TEMPLATE.format(**prompt_data)

    review_result = None
    azure_credentials = get_azure_openai_credentials()

    if azure_credentials:
        if not all(azure_credentials.values()):
             review_result = simulate_ai_call(assembled_prompt)
        else:
            actual_llm_response = call_actual_llm_api(assembled_prompt, azure_credentials)
            if actual_llm_response:
                review_result = actual_llm_response
            else:
                sim_response = simulate_ai_call(assembled_prompt)
                review_result = f"[REAL API CALL FAILED] {sim_response}"
    else:
        review_result = simulate_ai_call(assembled_prompt)

    return review_result if review_result is not None else "Review process failed to produce a result."


if __name__ == "__main__":
    print("--- Current REVIEW_PROMPT_TEMPLATE (Reverted to P.2 + P.3.1 state): ---")
    print(REVIEW_PROMPT_TEMPLATE)
    print("--- End of Template Print ---")

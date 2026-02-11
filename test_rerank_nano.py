import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

RERANK_PROMPT = """주어진 [사용자 질문]과 검색된 [법률 문서들] 사이의 관련성을 분석하여, 가장 관련성이 높은 상위 {k}개의 문서만 선별하라.

[사용자 질문]
{query}

[법률 문서 목록]
{docs_text}

[작성 규칙]
1. 각 문서가 질문의 법적 쟁점을 해결하는 데 얼마나 직접적인지 1~10점 사이의 점수를 매겨라.
2. 점수가 높은 순서대로 상위 {k}개의 문서 인덱스(0부터 시작)만 JSON 배열 형식으로 응답하라.
3. 결과는 반드시 다음과 같은 형식을 지켜라: {{"ranked_indices": [2, 0, 5]}}
"""

def test_rerank():
    print("--- Testing Rerank with gpt-5-nano ---")
    query = "빵을 만들다 믹서기에 손가락이 잘렸어"
    docs_text = "[0] 근로기준법 제2조 > 근로자란... \n[1] 산재보험법 ... \n[2] 안전보건규칙 ... "
    
    llm = ChatOpenAI(model_name="gpt-5-nano", temperature=0)
    prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
    chain = prompt | llm
    
    start_time = time.time()
    try:
        print("Invoking chain...")
        response = chain.invoke({
            "query": query,
            "docs_text": docs_text,
            "k": 2
        })
        print(f"Response: {response.content}")
        print(f"Time taken: {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_rerank()

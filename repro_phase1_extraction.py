
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator import Orchestrator, ConversationState
from app.llm_factory import LLMFactory
from llm.prompts import build_checklist_prompt, CHECKLIST_PHASE_FOUNDATIONAL

# Load environment variables
load_dotenv()

async def test_phase1_extraction():
    print("--- Verifying Phase 1 Extraction Quality ---")
    
    llm = LLMFactory.create_llm(os.getenv("LLM_TYPE", "openai"), model_name="gpt-5-nano")
    
    # Mock legal text with both Purpose (should be skipped) and Application (should be kept)
    law_text = """
    제1조(목적) 이 법은 근로조건의 기준을 정함으로써 근로자의 기본적 생활을 보장, 향상시키며 균형 있는 국민경제의 발전에 이바지함을 목적으로 한다.
    제2조(정의) ① 이 법에서 사용하는 용어의 뜻은 다음과 같다.
    1. "근로자"란 직업의 종류와 관계없이 임금을 목적으로 사업이나 사업장에 근로를 제공하는 사람을 말한다.
    2. "사용자"란 사업주 또는 사업 경영 담당자, 그 밖에 근로자에 관한 사항에 대하여 사업주를 위하여 행위하는 사람을 말한다.
    제11조(적용 범위) ① 이 법은 상시 5명 이상의 근로자를 사용하는 모든 사업 또는 사업장에 적용한다.
    """
    
    # Build template
    template_str = build_checklist_prompt("PHASE1_FOUNDATIONAL")
    
    # Format the template (simulating _sync_checklist)
    prompt_raw = template_str.format(
        current_issue_name="기초 성립 요건",
        law_context=law_text,
        chat_history="",
        confirmed_facts="",
        current_checklist="",
        user_input="",
        investigation_phase="PHASE1_FOUNDATIONAL"
    )
    
    print("\n[Requesting Extraction...]")
    # Using ChatPromptTemplate like orchestrator does
    from langchain_core.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate.from_template(template_str)
    res = llm.invoke(prompt.format(
        current_issue_name="기초 성립 요건",
        law_context=law_text,
        chat_history="",
        confirmed_facts="",
        current_checklist="",
        user_input="",
        investigation_phase="PHASE1_FOUNDATIONAL"
    ))
    checklist_json = res.content
    
    print("\n[Extracted Checklist]")
    print(checklist_json)
    
    import json
    data = json.loads(checklist_json)
    requirements = [item["requirement"] for item in data.get("issue_checklist", [])]
    
    print("\n[Requirements Only]")
    for r in requirements:
        print(f"- {r}")

    # Verification (Requirements only)
    forbidden_terms = ["목적", "이바지", "국민경제", "보호 대상의 법적 근거", "기준 설정의 주체"]
    found_forbidden = []
    for r in requirements:
        for t in forbidden_terms:
            if t in r:
                found_forbidden.append(f"{r} (contains '{t}')")
    
    if found_forbidden:
        print(f"\n[FAIL] Declarative/purpose terms in requirements: {found_forbidden}")
    else:
        print("\n[PASS] No purpose/declarative items in requirements.")
        
    # Should find subjects
    required_terms = ["근로자", "증거", "입증", "계약", "5명", "규모"]
    found_requirements_with_terms = []
    for r in requirements:
        for t in required_terms:
            if t in r:
                found_requirements_with_terms.append(t)
    
    print(f"[Key Terms Found] {list(set(found_requirements_with_terms))}")

    if any("근로자" in r and ("증거" in r or "입증" in r or "계약" in r) for r in requirements):
        print("[PASS] Worker status proof item found.")
    else:
        print("[FAIL] No worker status proof item found.")

if __name__ == "__main__":
    asyncio.run(test_phase1_extraction())

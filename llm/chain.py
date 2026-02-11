import json
import os
from app.llm_factory import LLMFactory
from data.collector import DataCollector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from llm.prompts import (
    SYSTEM_PROMPT,
    RESPONSE_PROMPT,
    QUESTION_PROMPT,
    INTERIM_SUMMARY_PROMPT,
    CHECKLIST_PHASE_NARROWING
)
import re

def normalize_req(text):
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', text).lower()

# --- Category Narrowing (Phase 0.5) ---
# Now using CHECKLIST_PHASE_NARROWING from prompts.py
CATEGORY_NARROWING_PROMPT = CHECKLIST_PHASE_NARROWING

class ResponseComposer:
    def __init__(self, model_name: str = None):
        self.llm = LLMFactory.create_llm(os.getenv("LLM_TYPE", "openai"), model_name=model_name)
        self.collector = DataCollector()

    def generate_question(self, question_text: str, detected_issues: list = None) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", QUESTION_PROMPT)
        ])
        chain = prompt | self.llm
        
        # detected_issues is now list of [{"key": "...", "korean": "..."}]
        issue_names = [i["korean"] for i in (detected_issues or []) if isinstance(i, dict)]
        if not issue_names and detected_issues: # fallback for legacy
            issue_names = detected_issues
            
        detected_issues_korean = ", ".join(issue_names)
        
        response = chain.invoke({
            "question_text": question_text,
            "detected_issues_korean": detected_issues_korean or "법률 상담"
        })
        return response.content

    def generate_conclusion(self, judgment_message: str, confirmed_facts: str, retrieved_laws: str, detected_issues: list = None, issue_checklist: dict = None) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", RESPONSE_PROMPT)
        ])
        chain = prompt | self.llm
        
        # detected_issues is now list of [{"key": "...", "korean": "..."}]
        issue_names = [i["korean"] for i in (detected_issues or []) if isinstance(i, dict)]
        if not issue_names and detected_issues:
            issue_names = detected_issues
            
        detected_issues_korean = ", ".join(issue_names)

        # Format checklist for prompt
        checklist_text = ""
        if issue_checklist:
            for issue, items in issue_checklist.items():
                checklist_text += f"\n[{issue}]\n"
                for item in items:
                    checklist_text += f"- {item['requirement']}: {item['status']} ({item.get('reason', '')})\n"

        response = chain.invoke({
            "judgment_message": judgment_message,
            "confirmed_facts": confirmed_facts,
            "retrieved_laws": retrieved_laws,
            "issue_checklist_text": checklist_text or "체크리스트 정보 없음",
            "detected_issues_korean": detected_issues_korean or "법률 상담"
        })
        return response.content

    def generate_interim_check(self, confirmed_facts: str, issue_checklist: dict, issue_mapping: dict = None) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", INTERIM_SUMMARY_PROMPT)
        ])
        chain = prompt | self.llm
        
        checklist_text = ""
        if issue_checklist:
            for issue_key, items in issue_checklist.items():
                # Use Korean name if mapping exists
                issue_display = issue_mapping.get(issue_key, issue_key) if issue_mapping else issue_key
                
                # Check for "Showstopper" pruning: If the PRIMARY existence item is NO, prune detail items
                # Uses the LLM-provided `type` field — no Korean pattern matching needed.
                has_existence_no = any(
                    item.get('type') == 'existence' and item['status'] == "NO"
                    for item in items
                )
                
                section_text = f"\n#### [{issue_display}]\n"
                item_added = False
                for item in items:
                    # Pruning: If primary existence is NO, only show that existence item
                    if has_existence_no and item.get('type') != 'existence':
                        continue
                        
                    status_map = {"YES": "✓", "NO": "✕", "UNKNOWN": "○", "INSUFFICIENT": "△"}
                    display_status = status_map.get(item['status'], item['status'])
                    section_text += f"- **{item['requirement']}**: {display_status} ({item.get('reason', '')})\n"
                    item_added = True
                
                if item_added:
                    checklist_text += section_text

        response = chain.invoke({
            "confirmed_facts": confirmed_facts,
            "issue_checklist_text": checklist_text or "체크리스트 정보 없음"
        })
        
        # Log successful interim check generation
        self.collector.log_interaction(
            user_input=f"[INTERIM_CHECK] Facts: {confirmed_facts}", 
            ai_response=response.content,
            metadata={"type": "interim_summary"}
        )
        
        return response.content

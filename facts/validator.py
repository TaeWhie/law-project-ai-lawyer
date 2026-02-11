import json
import os
from typing import Dict, List
from facts.schemas import FactState
from app.llm_factory import LLMFactory
from langchain_core.prompts import ChatPromptTemplate
from llm.prompts import FACT_EXTRACTION_PROMPT

class FactValidator:
    def __init__(self, model_name: str = None):
        self.llm = LLMFactory.create_llm(os.getenv("LLM_TYPE", "openai"), model_name=model_name)

    def _clean_json_output(self, text: str) -> str:
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def extract_facts(self, user_input: str, required_facts: List[str], context_question: str = "") -> Dict[str, FactState]:
        if not required_facts:
            return {}
            
        prompt = ChatPromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "context_question": context_question,
                "required_facts": ", ".join(required_facts),
                "user_input": user_input
            })
            print(f"DEBUG LLM Raw Response: {response.content}")
            # Clean JSON string if needed (sometimes LLM adds markdown blocks)
            content = self._clean_json_output(response.content)
            data = json.loads(content)
            print(f"DEBUG Parsed JSON: {data}")
            
            return {k: FactState(v) for k, v in data.items() if v in FactState.__members__}
        except Exception as e:
            print(f"Error extracting facts: {e}")
            return {f: FactState.UNKNOWN for f in required_facts}

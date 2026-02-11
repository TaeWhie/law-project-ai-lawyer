import json
import os
from typing import List
from app.llm_factory import LLMFactory
from langchain_core.prompts import ChatPromptTemplate
from llm.prompts import ISSUE_CLASSIFICATION_PROMPT

class IssueClassifier:
    def __init__(self, model_name: str = None):
        self.llm = LLMFactory.create_llm(os.getenv("LLM_TYPE", "openai"), model_name=model_name)

    def _clean_json_output(self, text: str) -> str:
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def classify_issues(self, user_input: str, chat_history: str = "", selected_law: str = "근로기준법", **kwargs) -> dict:
        # Load pre-indexed categories from unified index v2.0
        index_path = os.path.join(os.path.dirname(__file__), "..", "judgment", "legal_index.json")
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # Get law-specific categories
            law_data = index_data.get("laws", {}).get(selected_law, {})
            cat_list = law_data.get("categories", [])
            
            if not cat_list:
                # If no categories for selected law, try finding in other laws or provide summary
                all_cats = []
                for l_name, l_data in index_data.get("laws", {}).items():
                    all_cats.extend(l_data.get("categories", []))
                cat_list = all_cats[:10]  # Limit to 10 for prompt size if generic
            
            categories = "\n".join([f"- {c['key']} ({c['korean']}): {c['description']}" for c in cat_list])
            if not categories:
                categories = "사용 가능한 법률 카테고리가 없습니다."
        except Exception as e:
            print(f"Warning: Could not load legal_index.json ({e}). Classification may be less accurate.")
            categories = "법률 카테고리를 불러올 수 없습니다."

        prompt = ChatPromptTemplate.from_template(ISSUE_CLASSIFICATION_PROMPT)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "user_input": user_input,
                "categories": categories,
                "chat_history": chat_history,
                "current_step": kwargs.get("current_step", "START")
            })
            content = self._clean_json_output(response.content)
            data = json.loads(content)
            
            return {
                "intent": data.get("intent", "INVESTIGATION"),
                "issues": data.get("issues", []),
                "reason": data.get("reason", "No reason provided")
            }
        except Exception as e:
            print(f"Error classifying issues: {e}")
            return {"intent": "INVESTIGATION", "issues": []}
    
    def select_law(self, user_input: str) -> dict:
        """Select the most relevant law based on user input."""
        # Load available laws from legal_index.json
        index_path = os.path.join(os.path.dirname(__file__), "..", "judgment", "legal_index.json")
        available_laws_list = []
        
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # Get law names from unified structure
            if "laws" in index_data:
                available_laws_list = list(index_data["laws"].keys())
            else:
                available_laws_list = ["근로기준법"]  # Fallback
        except Exception as e:
            print(f"Warning: Could not load available laws ({e}). Defaulting to 근로기준법.")
            available_laws_list = ["근로기준법"]
        
        # Format available laws for prompt
        available_laws_text = "\n".join([f"- {law}" for law in available_laws_list])
        
        # Import prompt
        from llm.prompts import LAW_SELECTION_PROMPT
        
        prompt = ChatPromptTemplate.from_template(LAW_SELECTION_PROMPT)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "user_input": user_input,
                "available_laws": available_laws_text
            })
            content = self._clean_json_output(response.content)
            data = json.loads(content)
            
            selected_law = data.get("selected_law", "근로기준법")
            
            # Validate selection
            if selected_law not in available_laws_list and selected_law != "기타법률":
                print(f"[Law Selection] Invalid selection '{selected_law}'. Defaulting to 근로기준법.")
                selected_law = "근로기준법"
            
            return {
                "selected_law": selected_law,
                "confidence": data.get("confidence", "medium"),
                "reason": data.get("reason", "자동 선택")
            }
        except Exception as e:
            print(f"Error selecting law: {e}. Defaulting to 근로기준법.")
            return {
                "selected_law": "근로기준법",
                "confidence": "low",
                "reason": f"Selection error: {e}"
            }

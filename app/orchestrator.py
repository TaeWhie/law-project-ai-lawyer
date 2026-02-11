import json
import os
import uuid
import re
from typing import Dict, Any, List, Optional
from app.state import ConversationState
from judgment.engine import JudgmentEngine
from facts.validator import FactValidator
from rag.retriever import LawRetriever
from llm.chain import ResponseComposer
from llm.classifier import IssueClassifier
from app.llm_factory import LLMFactory
from data.collector import DataCollector
from llm.prompts import (
    QUESTION_GENERATOR_PROMPT,
    DIRECT_LEGAL_ANSWER_PROMPT, 
    WITTY_GUIDANCE_PROMPT,
    FACT_EXTRACTION_PROMPT,
    build_checklist_prompt
)
from langchain_core.prompts import ChatPromptTemplate
from difflib import SequenceMatcher

class Orchestrator:
    def __init__(self):
        self._ensure_legal_index()
        self.classifier = IssueClassifier()
        self.validator = FactValidator()
        self.retriever = LawRetriever()
        self.composer = ResponseComposer()
        self.llm = LLMFactory.create_llm("openai")
        self.collector = DataCollector()

    def _ensure_legal_index(self):
        from app.indexer import LegalIndexer
        print("Refreshing Legal Index and Vectors on startup...")
        indexer = LegalIndexer()
        indexer.run()

    def _clean_json_output(self, text: str) -> str:
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def normalize(self, text: str) -> str:
        # General cleaning only: remove parentheses, symbols, and lowercase
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'[^가-힣a-zA-Z0-9]', '', text).lower()
        return text

    def _classify_intent(self, user_input: str, state: ConversationState) -> (str, bool):
        """Deterministically or via LLM classify user intent."""
        positives = ["네", "예", "맞아요", "그렇습니다", "맞음", "진행", "진행해", "응", "어"]
        negatives = ["아니오", "아뇨", "틀려요", "아닙니다", "아님", "아니"]
        clean_input = user_input.strip().replace(" ", "")
        
        # Heuristic 1: PROCEED in REVIEW stage
        if state.verification_stage == "REVIEW" and any(p in clean_input for p in positives):
            return "PROCEED", True
            
        # Heuristic 2: Simple factual answer
        if len(clean_input) < 10 and (any(p == clean_input for p in positives) or any(n == clean_input for n in negatives)):
            return "INVESTIGATION", True
            
        # Fallback to LLM
        recent_history = state.message_log[-4:] if state.message_log else []
        history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history])
        res = self.classifier.classify_issues(user_input, chat_history=history_text, current_step=state.current_step)
        return res.get("intent", "INVESTIGATION"), False
    
    
    def _check_if_narrowing_needed(self, article_numbers: List[str] = None, issue_key: str = None, law_name: str = "근로기준법") -> bool:
        """Check if articles need narrowing (threshold: 5)."""
        # Direct check with article list
        if article_numbers is not None:
            return len(article_numbers) >= 5
        
        # Fallback: check by issue_key (for initial check)
        if issue_key is None:
            return False
            
        index_path = "judgment/legal_index.json"
        if not os.path.exists(index_path):
            return False
        
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                unified_index = json.load(f)
                if "laws" in unified_index:
                    index_data = unified_index["laws"].get(law_name, {})
                else:
                    index_data = unified_index
            
            category = next((c for c in index_data.get("categories", []) 
                           if c["key"] == issue_key), None)
            
            if not category:
                return False
            
            article_count = len(category.get("core_articles", []))
            return article_count >= 5
        except:
            return False
    
    def _generate_narrowing_question(self, user_input: str, issue_key: str, issue_name: str, state: ConversationState, target_articles: List[str] = None) -> str:
        """Generate narrowing question using broad RAG retrieval and core articles."""
        try:
            # 1. Gather Candidate Articles
            # Use a broad RAG search (high k) to capture the legal context without hardcoded sub-queries
            search_query = user_input if user_input and user_input != "[INTERNAL_NEXT]" else issue_name
            rag_docs = self.retriever.retrieve(query=search_query, k=40, use_llm_rerank=False)
            
            # Additional source: Core articles from the legal index
            index_path = "judgment/legal_index.json"
            core_article_nums = []
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)["laws"].get(state.selected_law, {})
                    
                    # If the issue is money-related (Wages/Hours), pull from multiple relevant categories
                    # instead of just the one matching issue_key.
                    money_related_keys = ["cat_6329", "cat_5072", "cat_6122"] # Wages, Dismissal/Retirement, Hours (Allowances)
                    
                    for cat in index.get("categories", []):
                        if cat["key"] == issue_key or cat["key"] in money_related_keys:
                            core_article_nums.extend([str(a["num"] if isinstance(a, dict) else a) for a in cat.get("core_articles", [])])
            except: pass

            # Combine and deduplicate article numbers
            rag_article_nums = [str(d.metadata.get("ArticleNumber")) for d in rag_docs if d.metadata.get("ArticleNumber")]
            combined_nums = list(dict.fromkeys(core_article_nums + rag_article_nums))[:60] # Sufficiently large pool

            # 2. Build Rich Context (Titles/Descriptions)
            # Prioritize Core Articles and then RAG-specific matches
            article_context_parts = []
            seen_nums = set()
            
            # Helper: Map RAG docs for quick lookup, prioritizing [Law] over [Decree]
            doc_map = {}
            for d in rag_docs:
                num = str(d.metadata.get("ArticleNumber"))
                if not num: continue
                
                is_law = "[법률]" in d.metadata.get("Article", "") or "[법률]" in d.metadata.get("Title", "")
                
                if num not in doc_map:
                    doc_map[num] = d
                else:
                    # If existing is not law and new is law, replace
                    existing = doc_map[num]
                    existing_is_law = "[법률]" in existing.metadata.get("Article", "") or "[법률]" in existing.metadata.get("Title", "")
                    if is_law and not existing_is_law:
                        doc_map[num] = d
            
            # Identify missing core articles and fetch them
            missing_nums = [n for n in combined_nums if n not in doc_map]
            
            if missing_nums:
                try:
                    # Fetch missing articles from vectorstore
                    vs = self.retriever._get_vectorstore()
                    # Chroma allows 'where' filter with $in operator
                    results = vs.get(where={"ArticleNumber": {"$in": missing_nums}})
                    
                    if results and results['ids']:
                        for i, doc_id in enumerate(results['ids']):
                            meta = results['metadatas'][i]
                            content = results['documents'][i]
                            art_num = str(meta.get("ArticleNumber"))
                            
                            # Create a pseudo-doc-like object or just store format
                            # Check if valid article
                            if art_num:
                                # Check if existing doc is Law
                                existing = doc_map.get(art_num)
                                is_law = meta.get("Article", "").startswith("[법률]") or meta.get("Title", "").endswith("(법률)")
                                
                                if existing:
                                    existing_is_law = "[법률]" in existing.metadata.get("Article", "") or "[법률]" in existing.metadata.get("Title", "")
                                    if is_law and not existing_is_law:
                                         class SimpleDoc:
                                            def __init__(self, c, m):
                                                self.page_content = c
                                                self.metadata = m
                                         doc_map[art_num] = SimpleDoc(content, meta)
                                else:
                                    class SimpleDoc:
                                        def __init__(self, c, m):
                                            self.page_content = c
                                            self.metadata = m
                                    doc_map[art_num] = SimpleDoc(content, meta)
                except Exception as e:
                    print(f"[Orchestrator] Failed to fetch missing core articles: {e}")

            for num in combined_nums:
                if num in seen_nums: continue
                doc = doc_map.get(num)
                if doc:
                    title = doc.metadata.get("Title", "알 수 없음")
                    label = doc.metadata.get("Article", f"제{num}조")
                    content = doc.page_content[:250].replace("\n", " ").strip()
                    article_context_parts.append(f"[{label} - {title}] {content}")
                    seen_nums.add(num)
            
            article_context_text = "\n".join(article_context_parts)
            
            # 3. Prepare Prompt Context
            # Only include the very last interaction to keep focus on the current classification task
            recent_history = state.message_log[-1:] if state.message_log else []
            history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history])
            
            # 4. Call LLM
            from llm.chain import CATEGORY_NARROWING_PROMPT
            from langchain_core.prompts import ChatPromptTemplate
            
            prompt = ChatPromptTemplate.from_template(CATEGORY_NARROWING_PROMPT)
            chain = prompt | self.composer.llm
            
            response = chain.invoke({
                "user_input": user_input,
                "chat_history": history_text,
                "article_context": article_context_text
            })
            
            # 5. Parse and Save
            result = self._clean_json_output(response.content)
            parsed = json.loads(result)
            
            state.narrowing_options = parsed.get("options", [])
            state.narrowing_issue_key = issue_key
            
            # Ensure the divisions are visible to the user by appending them to the question
            question = parsed.get("question", "상황에 대해 조금 더 구체적으로 말씀해 주실 수 있을까요?")
            labels_summary = "\n".join([f"{i+1}. {opt['label']}" for i, opt in enumerate(state.narrowing_options)])
            final_question = f"{question}\n\n{labels_summary}"
            
            print(f"[Narrowing] Dynamic RAG Pulled {len(combined_nums)} articles. Generated {len(state.narrowing_options)} groups.")
            return final_question
            
        except Exception as e:
            print(f"[Narrowing] Error: {e}")
            return "상황을 구체적으로 말씀해 주시면 정확한 분석을 위해 법적 범위를 좁히는 데 도움이 됩니다."
    
    def _filter_articles_by_answer(self, user_answer: str, options: List[Dict]) -> List[str]:
        """Filter articles based on user's narrowing answer. Returns article numbers."""
        if not options:
            return []
        
        # Normalize answer
        answer_normalized = self.normalize(user_answer)
        
        # 1. Numeric Match (e.g. "1", "1번", "첫번째")
        import re
        nums = re.findall(r'\d+', user_answer)
        if nums:
            idx = int(nums[0]) - 1
            if 0 <= idx < len(options):
                print(f"[Narrowing] Numeric match: {idx+1} → {options[idx].get('label')}")
                return options[idx].get("article_numbers", [])

        # 2. Heuristic Keyword Match
        matched_articles = []
        for option in options:
            # Check if option label or keywords match
            label_match = self.normalize(option.get("label", "")) in answer_normalized
            keyword_match = any(self.normalize(kw) in answer_normalized for kw in option.get("keywords", []))
            
            if label_match or keyword_match:
                article_numbers = option.get("article_numbers", [])
                if article_numbers:
                    matched_articles.extend(article_numbers)
                    print(f"[Narrowing] Heuristic match: {option.get('label', 'unknown')} → {article_numbers}")
                    return list(set(matched_articles))

        # 3. Semantic Match (LLM Fallback) - For "Flexible" matching
        try:
            from llm.prompts import NARROWING_MATCH_PROMPT
            options_text = "\n".join([f"- {opt['label']}: {', '.join(opt.get('keywords', []))}" for opt in options])
            
            prompt = ChatPromptTemplate.from_template(NARROWING_MATCH_PROMPT)
            match_res = (prompt | self.composer.llm).invoke({
                "user_answer": user_answer,
                "options_text": options_text
            }).content.strip()
            
            print(f"[Narrowing] Semantic match attempt: '{user_answer}' -> '{match_res}'")
            
            selected_opt = next((o for o in options if o["label"] == match_res), None)
            if selected_opt:
                print(f"[Narrowing] Semantic match success: {selected_opt['label']}")
                return selected_opt.get("article_numbers", [])
        except Exception as e:
            print(f"[Narrowing] Semantic match failed: {e}")
        
        return []
    
    def _get_law_context(self, state: ConversationState, issue_name: str, issue_key: str, use_foundational: bool = False):
        """RAG with caching to improve performance."""
        if not use_foundational and state.cached_law_context and state.cached_issue_key == issue_key:
            return state.cached_law_context, ""
            
        print(f"[RAG] Retrieving context for {issue_key} (foundational={use_foundational})...")
        
        # 1. Load Knowledge Mapping from Unified Index (Version 2.0)
        index_data = {}
        index_path = "judgment/legal_index.json"
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    unified_index = json.load(f)
                if "laws" in unified_index:
                    index_data = unified_index["laws"].get(state.selected_law, {})
                else:
                    index_data = unified_index
            except: pass

        # Foundational Logic
        if use_foundational:
            foundational_query = index_data.get("foundational_query", f"{state.selected_law} 총칙 및 적용범위(제1조~제14조)")
            print(f"[RAG] Using Foundational query: {foundational_query}")
            # Use retrieve() which handles both search and rerank
            reranked = self.retriever.retrieve(foundational_query, k=3)
            law_context = "\n\n".join([f"[{d.metadata.get('source', 'Unknown')}]\n{d.page_content}" for d in reranked])
            return law_context, foundational_query

        # 2. Extract Keywords and Articles for Query Expansion
        expanded_query = issue_name
        target_articles = []
        
        categories = index_data.get("categories", [])
        # Find matching category (strict key match or keyword match)
        category = next((c for c in categories if c["key"] == issue_key), None)
        if not category:
            # Fallback: fuzzy match or just search keywords in name
            category = next((c for c in categories if issue_name in c["korean"] or c["korean"] in issue_name), None)

        if category:
            keywords = category.get("search_keywords", [])
            
            # Helper to clean and format article strings with type support
            def format_article(a):
                if isinstance(a, dict):
                    num = re.sub(r"[제조\s]", "", str(a.get("num", "")))
                    atype = a.get("type", "법")
                else:
                    num = re.sub(r"[제조\s]", "", str(a))
                    atype = "법"
                
                if not num: return None, None
                
                # Format for Query Expansion (Exact terminology for better RAG hits)
                if "의" in num:
                    parts = num.split("의")
                    styled_num = f"제{parts[0]}조의{parts[1]}"
                else:
                    styled_num = f"제{num}조"
                    
                if atype in ["령", "시행령"]: full_name = f"{state.selected_law} 시행령 {styled_num}"
                elif atype in ["규", "시행규칙"]: full_name = f"{state.selected_law} 시행규칙 {styled_num}"
                else: full_name = f"{state.selected_law} {styled_num}"
                
                return num, full_name

            raw_core = category.get("core_articles", [])
            raw_penalty = category.get("penalty_articles", [])
            
            # CRITICAL: Apply narrowing filter if it exists
            if state.narrowing_current_articles:
                print(f"[RAG] Narrowing active. Filtering articles for Phase 3.")
                target_nums = state.narrowing_current_articles
                
                # 1. Filter core articles
                filtered_core = [a for a in raw_core if str(a.get("num") if isinstance(a, dict) else a) in target_nums]
                
                # 2. Extract Sub-articles (Decrees/Rules) for Phase 3 investigation
                sub_articles = []
                for a in filtered_core:
                    if isinstance(a, dict) and "sub_articles" in a:
                        sub_articles.extend(a["sub_articles"])
                
                if sub_articles:
                    print(f"[RAG] Found {len(sub_articles)} sub-articles (Decrees/Rules) for narrowed context.")
                
                raw_core = filtered_core + sub_articles
                raw_penalty = [a for a in raw_penalty if str(a.get("num") if isinstance(a, dict) else a) in target_nums]

            processed_articles = [format_article(a) for a in raw_core + raw_penalty if a]
            
            # Use full names for query expansion
            full_names = list(set([item[1] for item in processed_articles if item and item[1]]))
            target_articles = list(set([item[0] for item in processed_articles if item and item[0]]))
            
            if keywords:
                expanded_query += " " + " ".join(keywords)
            
            if full_names:
                expanded_query += " " + " ".join(full_names)
                
            print(f"[RAG] Expanded Query: {expanded_query}")

        # 3. Foundational Query Retrieval (ONLY for foundational phase)
        selected_law = state.selected_law
        
        # Get foundational query for selected law
        foundational_query = self._get_foundational_query(selected_law) if use_foundational else ""
        
        # Check if the law exists in legal_index.json
        index_path = "judgment/legal_index.json"
        law_data_exists = False
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                unified_index = json.load(f)
                if "laws" in unified_index and selected_law in unified_index["laws"]:
                    law_data_exists = True
        except: pass

        if foundational_query:
            # [CRITICAL] Increase k for broad 'General Provisions' coverage
            foundational_laws = self.retriever.retrieve(query=foundational_query, k=15)
            
            # [NEW] Force include all Articles from the Foundational Category for 100% coverage
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    unified_index = json.load(f)
                    law_meta = unified_index.get("laws", {}).get(selected_law, {})
                    # Look for category named '총칙' or similar foundational categories
                    foundational_cat = next((c for c in law_meta.get("categories", []) if c.get("korean") == "총칙" or c.get("cat_code") == "C1"), None)
                    if foundational_cat:
                        foundational_core_articles = [a["num"] if isinstance(a, dict) else a for a in foundational_cat.get("core_articles", [])]
                        foundational_art_queries = [f"제{num}조" for num in foundational_core_articles]
                        print(f"[RAG] Force adding foundational core articles: {foundational_core_articles}")
                        for q in foundational_art_queries:
                            # Avoid over-retrieval, just get the specific article
                            art_doc = self.retriever.retrieve(query=q, k=1, use_llm_rerank=False)
                            if art_doc:
                                foundational_laws.extend(art_doc)
            except Exception as e:
                print(f"[Debug] Could not auto-expand foundational articles: {e}")

            print(f"[RAG] Including foundational laws (k=15 + core): {foundational_query}")
        else:
            foundational_laws = []
            if not law_data_exists or selected_law == "기타법률":
                print(f"[RAG] Data for '{selected_law}' not found or generic. Foundational laws skipped.")
            else:
                print(f"[RAG] No foundational query defined for {selected_law}. Skipping.")
        
        issue_laws = self.retriever.retrieve(query=expanded_query, k=10) # Increased k for wider coverage
        
        # 4. Mandatory inclusion of core/penalty articles if missing
        existing_articles = [doc.metadata.get("ArticleNumber") for doc in issue_laws]
        missing_cores = [a for a in target_articles if a not in existing_articles]
        
        if missing_cores:
            print(f"[RAG] Force retrieving missing mandatory articles: {missing_cores}")
            for article_num in missing_cores:
                core_doc = self.retriever.retrieve(query=f"제{article_num}조", k=1, use_llm_rerank=False)
                if core_doc:
                    issue_laws.extend(core_doc)

        context = "\n".join([f"[{doc.metadata.get('Article', '법령')}] {doc.page_content}" for doc in foundational_laws + issue_laws])
        # Store BOTH context and expanded_query in cache as a tuple
        # Store law selection in state for reference
        state.selected_law = selected_law
        state.cached_law_context = (context, expanded_query)
        state.cached_issue_key = issue_key
        return context, expanded_query
    
    def _get_foundational_query(self, law_name: str) -> str:
        """Get foundational query for a specific law from legal_index.json."""
        if law_name == "기타법률":
            return ""  # No foundational query for unknown laws
        
        index_path = "judgment/legal_index.json"
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                unified_index = json.load(f)
            
            law_data = unified_index.get("laws", {}).get(law_name, {})
            foundational_query = law_data.get("foundational_query", "")
            
            if not foundational_query:
                print(f"[Warning] No foundational_query defined for law: {law_name}")
            
            return foundational_query
        except Exception as e:
            print(f"[Error] Failed to load foundational_query for {law_name}: {e}")
            return ""

    def _heuristic_update(self, user_input: str, state: ConversationState) -> bool:
        """Try to update the last asked item without LLM."""
        if not state.last_asked_item:
            return False
            
        positives = ["네", "예", "맞아요", "그렇습니다", "맞음", "응", "어"]
        negatives = ["아니오", "아뇨", "틀려요", "아닙니다", "아님", "아니"]
        clean_input = user_input.strip().replace(" ", "")
        
        current_checklist = state.issue_checklist.get(state.issue_type, [])
        for item in current_checklist:
            if item["requirement"] == state.last_asked_item:
                if any(p == clean_input for p in positives):
                    item["status"] = "YES"
                    item["reason"] = "사용자 직접 긍정 (Heuristic)"
                    return True
                elif any(n == clean_input for n in negatives):
                    item["status"] = "NO"
                    item["reason"] = "사용자 직접 부정 (Heuristic)"
                    return True
        return False

    def process_input(self, user_input: str, state: ConversationState) -> str:
        is_internal_transition = user_input == "[INTERNAL_NEXT_ISSUE]"
        if is_internal_transition:
            intent, skip_classifier = "INVESTIGATION", True
        else:
            intent, skip_classifier = self._classify_intent(user_input, state)

        # Skip logic
        skip_sync = False
        if not is_internal_transition and skip_classifier and intent == "INVESTIGATION":
            skip_sync = self._heuristic_update(user_input, state)

        # Branching
        if intent == "CHITCHAT":
            return self._handle_chitchat(user_input, state)
        elif intent == "INFO_QUERY":
            return self._handle_info_query(user_input, state)
        elif intent == "PROCEED":
            if state.investigation_phase == "CORE":
                state.investigation_phase = "DEEP"
                state.verification_stage = "PENDING"
                return self.process_input("[INTERNAL_NEXT_ISSUE]", state)

        # Investigation Flow
        try:
            return self._perform_investigation(user_input, state, skip_sync, is_internal_transition, intent, skip_classifier)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"처리 중 오류가 발생했습니다: {str(e)}"

    def _extract_facts(self, user_input: str, state: ConversationState):
        """Extract facts using LLM and update state.facts."""
        current_checklist = state.issue_checklist.get(state.issue_type, [])
        if not current_checklist:
            return

        required_facts = "\n".join([f"- {i['requirement']}" for i in current_checklist])
        prompt = ChatPromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
        
        try:
            res = self.llm.invoke(prompt.format(
                context_question=state.last_asked_item_text or "없음",
                user_input=user_input,
                required_facts=required_facts
            ))
            extracted = json.loads(self._clean_json_output(res.content))
            
            for fact_name, status in extracted.items():
                if status in ["YES", "NO"]:
                    from facts.schemas import FactState
                    state.update_fact(fact_name, FactState(status))
        except Exception as e:
            print(f"[Fact Extraction Error] {e}")

    def _perform_investigation(self, user_input: str, state: ConversationState, skip_sync: bool, is_internal: bool, intent: str, is_heuristic: bool) -> str:
        # Extract facts BEFORE anything else
        if not is_internal and state.current_step == "INVESTIGATING":
            self._extract_facts(user_input, state)

        # 0. Initial Setup & Law/Issue Selection
        if state.current_step == "START":
            # [CRITICAL] 0.1 Law Selection FIRST
            first_user_message = next((msg["content"] for msg in state.message_log if msg["role"] == "user"), user_input)
            law_selection = self.classifier.select_law(first_user_message)
            state.selected_law = law_selection["selected_law"]
            print(f"[Law Selection] Early Selection: {state.selected_law}")

            # 0.2 Issue Classification
            res = self.classifier.classify_issues(user_input, selected_law=state.selected_law)
            detected = res.get("issues", [{"key": "others", "korean": "기타 법률 상담"}])
            state.detected_issues = detected
            state.issue_type = detected[0]["key"]
            state.current_step = "INVESTIGATING"
            state.investigation_phase = "PHASE1_NARROWING" # [MOD] Start in Narrowing (New Phase 1)
            # Use RAG to get initial candidate articles based on user input for better narrowing context
            initial_docs = self.retriever.retrieve(query=user_input, k=15, use_llm_rerank=False)
            state.narrowing_current_articles = [str(d.metadata.get("ArticleNumber")) for d in initial_docs if d.metadata.get("ArticleNumber")]
            if not state.narrowing_current_articles:
                state.narrowing_current_articles = self._get_initial_articles(state) # Fallback to static
            for issue in detected:
                state.issue_checklist[issue["key"]] = []
            is_new_issue_start = True
        else:
            is_new_issue_start = state.issue_type not in state.issue_checklist or not state.issue_checklist[state.issue_type]

        current_issue = next((i for i in state.detected_issues if i["key"] == state.issue_type), state.detected_issues[0])
        current_issue_name = current_issue["korean"]

        # 1. [Phase 1] Article Narrowing (Old Phase 2)
        if state.investigation_phase == "PHASE1_NARROWING":
            print(f"[Phase 1] Narrowing logic for {len(state.narrowing_current_articles)} articles")
            needs_narrowing = self._check_if_narrowing_needed(article_numbers=state.narrowing_current_articles, law_name=state.selected_law)
            
            if needs_narrowing and state.narrowing_depth < 3:
                if state.narrowing_pending:
                    filtered = self._filter_articles_by_answer(user_input, state.narrowing_options)
                    if filtered:
                        state.narrowing_current_articles = filtered
                        state.narrowing_depth += 1
                        state.narrowing_pending = False
                        # Re-calculate if further narrowing needed
                        return self._perform_investigation("[INTERNAL_NEXT]", state, True, True, "INVESTIGATION", True)
                    else:
                        return self._handle_narrowing_fail(user_input, state)
                
                question_text = self._generate_narrowing_question("", state.issue_type, current_issue_name, state, state.narrowing_current_articles)
                if question_text:
                    state.narrowing_pending = True
                    return self.composer.generate_question(question_text, detected_issues=state.detected_issues)
            
            print("[Phase 1] Complete or skipped. Transitioning to Phase 2.")
            state.investigation_phase = "PHASE2_INVESTIGATION"
            state.narrowing_pending = False
            # Fallthrough to Phase 2
 
        # 2. [Phase 2] Factual Investigation (Old Phase 3)
        if state.investigation_phase == "PHASE2_INVESTIGATION":
            print(f"[Phase 2] Investigating {len(state.narrowing_current_articles)} articles")
            law_context, query = self._get_law_context(state, current_issue_name, state.issue_type, use_foundational=False)
            checklist, conclusion = self._sync_checklist(user_input, state, law_context, skip_sync)
            
            if all(i["status"] in ["YES", "NO"] for i in checklist) and checklist:
                # Issue complete
                state.dynamic_issue_data[state.issue_type] = {"conclusion": conclusion, "law": law_context}
                idx = next(i for i, x in enumerate(state.detected_issues) if x["key"] == state.issue_type)
                if idx < len(state.detected_issues) - 1:
                    state.issue_type = state.detected_issues[idx+1]["key"]
                    state.investigation_phase = "PHASE1_NARROWING" # Reset to Narrowing for next issue
                    return self.process_input("[INTERNAL_NEXT_ISSUE]", state)
                
                # All issues complete -> Final Report
                state.judgment_ready = True
                concs = "\n\n".join([v["conclusion"] for v in state.dynamic_issue_data.values()])
                laws = "\n".join([v["law"] for v in state.dynamic_issue_data.values()])
                confirmed_facts = "\n".join([f"- {k}: {v.value}" for k, v in state.facts.items()])
                return self.composer.generate_conclusion(concs, confirmed_facts=confirmed_facts, retrieved_laws=laws, detected_issues=state.detected_issues, issue_checklist=state.issue_checklist)

            question = self._generate_next_question(state, checklist, conclusion)
            return question

        return "상담이 진행 중입니다."

    def _attach_interim_check(self, question: str, state: ConversationState) -> str:
        """Attach a summarized checklist to the question."""
        confirmed_facts = "\n".join([f"{k}: {v.value}" for k, v in state.facts.items()])
        issue_mapping = {issue["key"]: issue["korean"] for issue in state.detected_issues}
        
        interim_check = self.composer.generate_interim_check(
            confirmed_facts=confirmed_facts or "아직 확인된 사실이 적습니다.",
            issue_checklist=state.issue_checklist,
            issue_mapping=issue_mapping
        )
        
        return f"{question}\n\n{interim_check}"

    def _update_issue_progress(self, state: ConversationState):
        """Calculate progress percentage for each issue based on checklist status."""
        for issue_key, checklist in state.issue_checklist.items():
            if not checklist:
                state.issue_progress[issue_key] = 0
                continue
            
            resolved = [i for i in checklist if i["status"] in ["YES", "NO"]]
            # Limit progress to 95% until complete, or use simple linear calc
            progress = int((len(resolved) / len(checklist)) * 100)
            state.issue_progress[issue_key] = progress

    def _sync_checklist(self, user_input, state, law_context, skip_sync):
        """Internal helper to synchronize checklist with LLM."""
        current_issue_name = next((i["korean"] for i in state.detected_issues if i["key"] == state.issue_type), "이슈")
        
        if skip_sync and state.issue_checklist.get(state.issue_type):
            return state.issue_checklist[state.issue_type], "상태 유지"

        confirmed_facts = "\n".join([f"- {k}: {v.value}" for k, v in state.facts.items()])
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state.message_log[-6:]])
        current_checklist_text = "\n".join([f"- {item['requirement']} ({item['status']})" for item in state.issue_checklist.get(state.issue_type, [])])

        prompt = ChatPromptTemplate.from_template(build_checklist_prompt(state.investigation_phase))
        res = self.llm.invoke(prompt.format(
            current_issue_name=current_issue_name,
            law_context=law_context,
            confirmed_facts=confirmed_facts or "없음",
            chat_history=history_text,
            user_input=user_input,
            current_checklist=current_checklist_text or "없음",
            investigation_phase=state.investigation_phase
        ))
        
        data = json.loads(self._clean_json_output(res.content))
        new_items = data.get("issue_checklist", [])
        
        # [NEW] Force state from extracted facts before merging
        for item in new_items:
            norm_name = self.normalize(item["requirement"])
            # Match against state.facts
            for fact_name, fact_obj in state.facts.items():
                if SequenceMatcher(None, norm_name, self.normalize(fact_name)).ratio() > 0.8:
                    item["status"] = fact_obj.value
                    item["reason"] = "사실 데이터베이스에서 동기화됨"

        self._merge_checklists(state, new_items, is_new=not state.issue_checklist.get(state.issue_type))
        
        # [NEW] Update progress bars after merge
        self._update_issue_progress(state)
        
        return state.issue_checklist[state.issue_type], data.get("conclusion", "")

    def _get_initial_articles(self, state):
        """Helper to get article list for narrowing."""
        index_path = "judgment/legal_index.json"
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)["laws"].get(state.selected_law, {})
                cat = next((c for c in index.get("categories", []) if c["key"] == state.issue_type), None)
                return [a["num"] if isinstance(a, dict) else a for a in cat.get("core_articles", [])] if cat else []
        except: return []

    def _generate_checklist_summary(self, state: ConversationState) -> str:
        """Create a visual text summary of the current checklist status."""
        checklist = state.issue_checklist.get(state.issue_type, [])
        if not checklist: return ""
        
        summary_lines = []
        for item in checklist:
            icon = "✓" if item["status"] == "YES" else "✕" if item["status"] == "NO" else "○"
            summary_lines.append(f"{icon} {item['requirement']}")
        
        return "\n".join(summary_lines)

    def _generate_next_question(self, state, checklist, conclusion):
        """Helper to generate targeted question for the next step."""
        prompt = ChatPromptTemplate.from_template(QUESTION_GENERATOR_PROMPT)
        res = self.llm.invoke(prompt.format(
            checklist=json.dumps(checklist, ensure_ascii=False),
            investigation_phase=state.investigation_phase
        ))
        parsed = json.loads(self._clean_json_output(res.content))
        question_text = parsed.get("question", "추가 상황을 말씀해 주세요.")
        state.last_asked_item_text = question_text
        
        return self.composer.generate_question(question_text, detected_issues=state.detected_issues)

    def _merge_checklists(self, state: ConversationState, new_items: List[Dict], is_new: bool):
        old_checklist = state.issue_checklist.get(state.issue_type, [])
        merged_map = {self.normalize(i["requirement"]): i for i in old_checklist}
        
        for new in new_items:
            norm = self.normalize(new["requirement"])
            target = None
            if norm in merged_map:
                target = merged_map[norm]
            else:
                for k, v in merged_map.items():
                    if SequenceMatcher(None, norm, k).ratio() > 0.65:
                        target = v; break
            
            if target:
                if new["status"] in ["YES", "NO", "INSUFFICIENT"] or target["status"] == "UNKNOWN":
                    target["status"], target["reason"] = new["status"], new["reason"]
            else:
                merged_map[norm] = new
        
        final = list(merged_map.values())
        if is_new:
            for i in final:
                # Strictly force UNKNOWN for details and foundational factors on first detection
                # unless they were explicitly mentioned (which the LLM should handle, but we emphasize here)
                is_foundational = i.get("type") == "existence" or any(kw in i["requirement"] for kw in ["근로자", "사용자", "사업장", "고용"])
                if i.get("type") != "existence" or is_foundational:
                    # If it's the very first time we see this issue, nothing should be YES except unprovable existence
                    # But even existence for foundational must be proven.
                    if state.investigation_phase == "PHASE1_FOUNDATIONAL":
                        i["status"] = "UNKNOWN"
        state.issue_checklist[state.issue_type] = final

    def _handle_info_query(self, user_input, state):
        # Determine likely issue for context
        res = self.classifier.classify_issues(user_input)
        issue = res.get("issues", [{"key": "others", "korean": "기타 법률 상담"}])[0]
        law_ctx, expanded_query = self._get_law_context(state, issue["korean"], issue["key"])
        
        prompt = ChatPromptTemplate.from_template(DIRECT_LEGAL_ANSWER_PROMPT)
        ans = (prompt | self.llm).invoke({"user_input": user_input, "law_context": law_ctx})
        return ans.content

    def _handle_chitchat(self, user_input, state):
        prompt = ChatPromptTemplate.from_template(WITTY_GUIDANCE_PROMPT)
        ans = (prompt | self.llm).invoke({"user_input": user_input})
        return ans.content

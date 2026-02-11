from typing import List, Dict, Any
import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import json

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
class LawRetriever:
    def __init__(self, persist_directory: str = "data/chroma", collection_name: str = "statutes"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.collection_name = collection_name
        # Note: Embedding model should match what was used during ingestion
        # Dynamic switching based on env
        from app.llm_factory import LLMFactory
        import os
        embed_type = os.getenv("EMBEDDING_TYPE", os.getenv("LLM_TYPE", "openai"))
        self.embeddings = LLMFactory.create_embeddings(embed_type)
        self.vectorstore = None

    def _get_vectorstore(self):
        if self.vectorstore is None:
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
        return self.vectorstore

    def retrieve(self, query: str, tier: str = None, k: int = 5, use_llm_rerank: bool = True) -> List[Any]:
        vs = self._get_vectorstore()
        
        # 1. Selection logic
        pool_k = k * 3 if use_llm_rerank else k
        
        # ... (article detection same)
        import re
        article_match = re.search(r"제?\s*(\d+)\s*조", query)
        
        search_filter = {}
        if tier:
            search_filter["tier"] = tier
            
        if article_match:
            article_num = article_match.group(1)
            article_filter = {"ArticleNumber": article_num}
            if tier:
                article_filter = {"$and": [article_filter, {"tier": tier}]}
            results = vs.similarity_search(query, k=pool_k, filter=article_filter)
            if not results:
                results = vs.similarity_search(query, k=pool_k, filter=search_filter if search_filter else None)
        else:
            results = vs.similarity_search(query, k=pool_k, filter=search_filter if search_filter else None)

        if not results:
            return []

        if not results:
            return []

        if not use_llm_rerank:
            # Heuristic sort for Act/Statute preference
            results.sort(key=lambda x: 0 if "[법률]" in x.metadata.get("Article", "") or "[법률]" in x.metadata.get("Title", "") else 1)
            return results[:k]
            
        try:
            from app.llm_factory import LLMFactory
            # Use the cheaper default model
            rerank_llm = LLMFactory.create_llm("openai", temperature=0)
            
            docs_text = ""
            for i, doc in enumerate(results):
                title = doc.metadata.get("Title", "알 수 없음")
                article = doc.metadata.get("Article", "알 수 없음")
                docs_text += f"[{i}] {title} > {article}\n{doc.page_content[:300]}...\n\n"
            
            prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
            chain = prompt | rerank_llm
            
            rerank_response = chain.invoke({
                "query": query,
                "docs_text": docs_text,
                "k": k
            })
            
            # Clean and parse JSON
            content = rerank_response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            indices = data.get("ranked_indices", [])
            
            reranked_results = []
            seen_indices = set()
            for idx in indices:
                if 0 <= idx < len(results) and idx not in seen_indices:
                    reranked_results.append(results[idx])
                    seen_indices.add(idx)
            
            # Fallback if reranker fails to provide enough results
            if len(reranked_results) < k:
                for i in range(len(results)):
                    if i not in seen_indices:
                        reranked_results.append(results[i])
                        if len(reranked_results) >= k: break
            
            print(f"DEBUG: Reranked {len(results)} -> {len(reranked_results[:k])} docs for query: '{query}'")
            return reranked_results[:k]

        except Exception as e:
            print(f"Reranking Error (Falling back to heuristic): {e}")
            return results[:k]

    def _load_categories(self):
        """Lazy load categories and cache their embeddings."""
        if hasattr(self, "categories") and self.categories:
            return

        try:
            with open("judgment/legal_index.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # Assuming '근로기준법' is the main law we care about for now
                self.categories = data["laws"]["근로기준법"]["categories"]
        except Exception as e:
            print(f"Failed to load categories: {e}")
            self.categories = []
            return

        # Pre-calculate embeddings
        texts = []
        for cat in self.categories:
            # Combine relevant fields for semantic matching
            text = f"{cat.get('korean', '')} {cat.get('description', '')} {' '.join(cat.get('search_keywords', []))}"
            texts.append(text)
        
        try:
            self.category_embeddings = self.embeddings.embed_documents(texts)
        except Exception as e:
            print(f"Failed to embed categories: {e}")
            self.category_embeddings = []

    def _get_top_categories(self, query: str, top_k_cats: int = 2) -> List[Dict]:
        """Identify top relevant categories for a query."""
        self._load_categories()
        if not hasattr(self, "category_embeddings") or not self.category_embeddings:
            return []

        import numpy as np
        query_vec = self.embeddings.embed_query(query)
        
        # Calculate cosine similarity
        similarities = []
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        for idx, cat_vec in enumerate(self.category_embeddings):
            score = cosine_similarity(query_vec, cat_vec)
            similarities.append((score, idx))
        
        # Sort by score desc
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        # Select top K categories
        top_cats = []
        for score, idx in similarities:
            cat = self.categories[idx]
            name = cat.get('korean', '')
            # Filter out 'General Provisions' (총칙) and 'Penalties' (벌칙)
            if "총칙" in name or "벌칙" in name:
                continue
            top_cats.append(cat)
            if len(top_cats) >= top_k_cats:
                break
        return top_cats

    def _get_article_numbers_for_category(self, cat: Dict) -> List[str]:
        """Return article numbers associated with a category."""
        allowed_nums = []
        start = cat.get("start_num")
        end = cat.get("end_num")
        if start and end:
            for i in range(int(start), int(end) + 1):
                allowed_nums.append(str(i))
        
        for core in cat.get("core_articles", []):
            num = str(core["num"])
            if num not in allowed_nums:
                allowed_nums.append(num)
        return allowed_nums

    def _get_relevant_article_numbers(self, query: str, top_k_cats: int = 2) -> List[str]:
        """Identify top relevant categories and return their article number ranges."""
        top_cats = self._get_top_categories(query, top_k_cats=top_k_cats)
        print(f"DEBUG: Top Categories for '{query}': {[c['korean'] for c in top_cats]}")

        allowed_nums = []
        for cat in top_cats:
            allowed_nums.extend(self._get_article_numbers_for_category(cat))
        return list(set(allowed_nums))

    def retrieve(self, query: str, tier: str = None, k: int = 5, use_llm_rerank: bool = True) -> List[Any]:
        vs = self._get_vectorstore()
        
        # 1. Category Filtering logic
        # First, try to narrow down the search space using semantic category matching
        allowed_articles = self._get_relevant_article_numbers(query)
        
        search_filter = {}
        if tier:
            search_filter["tier"] = tier

        # Explicit Article Match Override (e.g. user types "제23조")
        import re
        article_match = re.search(r"제?\s*(\d+)\s*조", query)
        
        if article_match:
            # If user explicitly asks for an article, ignore category filtering
            article_num = article_match.group(1)
            article_filter = {"ArticleNumber": article_num}
            if tier:
                article_filter = {"$and": [article_filter, {"tier": tier}]}
            results = vs.similarity_search(query, k=k*3, filter=article_filter)
            if not results:
                results = vs.similarity_search(query, k=k*3, filter=search_filter if search_filter else None)
        elif allowed_articles:
            # Apply Category Filter
            # Chroma 'in' filter: "field": {"$in": [list]}
            cat_filter = {"ArticleNumber": {"$in": allowed_articles}}
            
            # Combine with tier filter if exists
            if tier:
                final_filter = {"$and": [search_filter, cat_filter]}
            else:
                final_filter = cat_filter
                
            print(f"DEBUG: Applying Category Filter: {final_filter}")
            results = vs.similarity_search(query, k=k*2, filter=final_filter) # Fetch a candidate pool
            print(f"DEBUG: Filtered Search Results Count: {len(results)}")
            
            # If category filtering yields too few results, fallback to full search
            if len(results) < k:
                print("DEBUG: Category filter too restrictive, falling back to full search.")
                results = vs.similarity_search(query, k=k*3, filter=search_filter if search_filter else None)
        else:
            # Fallback / No filter
            results = vs.similarity_search(query, k=k*3, filter=search_filter if search_filter else None)
            
        if not results:
            return []

        if not use_llm_rerank:
            # Heuristic sort for Act/Statute preference
            results.sort(key=lambda x: 0 if "[법률]" in x.metadata.get("Article", "") or "[법률]" in x.metadata.get("Title", "") else 1)
            return results[:k]
            
        try:
            from app.llm_factory import LLMFactory
            # Use the cheaper default model
            rerank_llm = LLMFactory.create_llm("openai", temperature=0)
            
            docs_text = ""
            for i, doc in enumerate(results):
                title = doc.metadata.get("Title", "알 수 없음")
                article = doc.metadata.get("Article", "알 수 없음")
                docs_text += f"[{i}] {title} > {article}\n{doc.page_content[:300]}...\n\n"
            
            prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
            chain = prompt | rerank_llm
            
            rerank_response = chain.invoke({
                "query": query,
                "docs_text": docs_text,
                "k": k
            })
            
            # Clean and parse JSON
            content = rerank_response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            indices = data.get("ranked_indices", [])
            
            reranked_results = []
            seen_indices = set()
            for idx in indices:
                if 0 <= idx < len(results) and idx not in seen_indices:
                    reranked_results.append(results[idx])
                    seen_indices.add(idx)
            
            # Fallback if reranker fails to provide enough results
            if len(reranked_results) < k:
                for i in range(len(results)):
                    if i not in seen_indices:
                        reranked_results.append(results[i])
                        if len(reranked_results) >= k: break
            
            print(f"DEBUG: Reranked {len(results)} -> {len(reranked_results[:k])} docs for query: '{query}'")
            return reranked_results[:k]

        except Exception as e:
            print(f"Reranking Error (Falling back to heuristic): {e}")
            return results[:k]

    def retrieve_grouped(self, query: str, k_per_cat: int = 3, top_k_cats: int = 3) -> Dict[str, List[Any]]:
        """Perform separate vector searches for each identified legal category."""
        vs = self._get_vectorstore()
        top_cats = self._get_top_categories(query, top_k_cats=top_k_cats)
        
        grouped_results = {}
        for cat in top_cats:
            name = cat.get('korean', '기타')
            allowed_articles = self._get_article_numbers_for_category(cat)
            
            if allowed_articles:
                cat_filter = {"ArticleNumber": {"$in": allowed_articles}}
                results = vs.similarity_search(query, k=k_per_cat, filter=cat_filter)
                if results:
                    grouped_results[name] = results
            
        # Fallback if no categories found or no results in categories
        if not grouped_results:
            results = self.retrieve(query, k=k_per_cat * top_k_cats, use_llm_rerank=False)
            if results:
                grouped_results["일반 결과"] = results
                
        return grouped_results


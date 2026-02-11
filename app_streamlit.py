# Streamlit App
import streamlit as st
import os
import sys
import json
import time

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.retriever import LawRetriever
from dotenv import load_dotenv

# Load env - Load this before any other logic
load_dotenv()

# --- Streamlit Cloud Compatibility ---
# LangChain needs os.environ['OPENAI_API_KEY'], but Streamlit Cloud stores it in st.secrets.
# We manually bridge them if needed.
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# --- Page Config (Must be first) ---
st.set_page_config(
    page_title="AI 법률 조항 추천기",
    layout="wide",  # Use full width
    initial_sidebar_state="expanded"
)

# --- Bypass Streamlit's Email Prompt ---
if "user_email" not in st.session_state:
    st.session_state.user_email = "test@example.com"

def main():
    st.title("⚖️ AI 법률 조항 추천기")
    st.markdown("---")

    # --- Initialize Retriever (Cached) ---
    if "retriever" not in st.session_state:
        try:
            st.session_state.retriever = LawRetriever(
                persist_directory="data/chroma",
                collection_name="statutes"
            )
        except Exception as e:
            st.error(f"Retriever 초기화 실패: {e}")
            return

    retriever = st.session_state.retriever

    # --- Global 2-Column Layout ---
    # Left: Input & Articles
    # Right: AI Analysis
    # We use a [1, 1] split to give equal real estate, or [4, 5] for slightly wider analysis
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.subheader("1. 상황 설명 및 조항 검색")
        user_input = st.text_area(
            "법적 상황을 자세히 묘사해 주세요:", 
            height=200,
            placeholder="예: 월급을 3달째 못 받고 있는데 회사가 망할 것 같아요."
        )
        
        search_clicked = st.button("🔍 관련 법안 찾기", use_container_width=True)
        
        st.markdown("### 📜 관련 법률 조항")
        # Placeholder for articles
        article_container = st.container()

    with right_col:
        st.subheader("2. 👨‍⚖️ AI 변호사 분석")
        # Placeholder for analysis
        analysis_container = st.empty()
        analysis_container.info("👈 좌측에서 상황을 입력하고 검색하면, 법률 전문가의 분석 결과가 이곳에 표시됩니다.")

    # --- Logic ---
    if search_clicked:
        if not user_input.strip():
            st.warning("상황을 입력해 주세요.")
            return
        
        with st.spinner("법률 조항을 검색하고 분석 중입니다..."):
            try:
                # 1. Retrieve
                # Increased k=5 to cover multiple issues (e.g., Wages + Dismissal)
                results = retriever.retrieve(user_input, k=5, use_llm_rerank=True)
                
                # 2. Display Articles (Left)
                with article_container:
                    if not results:
                        st.error("관련된 법률 조항을 찾지 못했습니다.")
                    else:
                        st.success(f"가장 관련성 높은 {len(results)}개의 조항을 찾았습니다.")
                        for i, doc in enumerate(results):
                            meta = doc.metadata
                            title = meta.get("Title", "법률")
                            article_full = meta.get("Article", "조항")
                            
                            with st.expander(f"{i+1}. {title} > {article_full}", expanded=True):
                                st.markdown(f"**{article_full}**")
                                st.code(doc.page_content, language="text")
                
                # 3. Generate Analysis (Right)
                if results:
                    with analysis_container:
                        try:
                            from app.llm_factory import LLMFactory
                            from langchain_core.prompts import ChatPromptTemplate
                            
                            docs_context = ""
                            for doc in results:
                                docs_context += f"- {doc.metadata.get('Article', '')}: {doc.page_content}\n"
                            
                            lawyer_prompt = ChatPromptTemplate.from_template("""
                            너는 20년 경력의 따뜻하고 유능한 노동법 전문 변호사다. 의뢰인의 [상황]과 [관련 조항]을 바탕으로 아래 형식에 맞춰 상담 내용을 작성하라.

                            [의뢰인 상황]
                            {user_input}

                            [관련 법률 조항]
                            {docs_context}

                            [작성 형칙 (반드시 준수)]
                            1. **💕 따뜻한 위로**: 의뢰인의 힘든 상황에 대해 진심 어린 공감과 위로의 말을 건네라. (1-2문장)
                            2. **⚖️ 법률 요약 (쟁점별 구분)**: 상황에 복합적인 문제(예: 부당해고 + 임금체불)가 있다면, **1. 부당해고, 2. 임금체불** 과 같이 번호를 매겨 각각 명확히 진단하라.
                            3. **🛡️ 조언 및 대처**: 각 쟁점별로 의뢰인이 당장 취해야 할 행동(증거 확보, 신고 절차 등)을 구체적으로 안내하라.
                            4. **✅ 스스로 체크하기**: 승소 가능성을 판단하기 위한 핵심 질문 5가지를 리스트로 나열하라.
                            5. **📜 근거 법령**: 위 상담의 근거가 되는 법률 조항 번호와 명칭을 명시하라.

                            [어조]
                            전문적이지만, 의뢰인을 가족처럼 걱정하는 따뜻하고 정중한 존댓말을 사용하라.
                            """)
                            
                            llm = LLMFactory.create_llm("openai", temperature=0.3)
                            chain = lawyer_prompt | llm
                            
                            # Streaming the response
                            message_placeholder = st.empty()
                            full_response = ""
                            
                            # Use chain.stream for token-by-token update
                            for chunk in chain.stream({
                                "user_input": user_input,
                                "docs_context": docs_context
                            }):
                                if chunk.content:
                                    full_response += chunk.content
                                    message_placeholder.markdown(full_response + "▌")
                            
                            # Final update without cursor
                            message_placeholder.markdown(full_response)
                            
                        except Exception as e:
                            st.error(f"분석 중 오류 발생: {e}")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()

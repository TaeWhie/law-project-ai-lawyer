import streamlit as st
import os
import json
import uuid
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.orchestrator import Orchestrator
from app.state import ConversationState

# Page Configuration
st.set_page_config(
    page_title="AI 근로기준법 법률 상담",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
    }
    .status-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4facfe;
        margin-bottom: 10px;
    }
    .requirement-item {
        font-size: 0.9em;
        margin-bottom: 5px;
    }
    .check-yes { color: #28a745; font-weight: bold; }
    .check-no { color: #dc3545; font-weight: bold; }
    .check-unknown { color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# Determine environment and DB path early
is_streamlit_cloud = os.path.exists("/mount/src")
if is_streamlit_cloud:
    import tempfile
    default_db_path = os.path.join(tempfile.gettempdir(), "chroma")
else:
    default_db_path = "data/chroma"

if "db_path" not in st.session_state:
    st.session_state.db_path = default_db_path

# --- Session State Initialization ---
if "orchestrator" not in st.session_state:
    # On first load, check if local data exists. If not, don't force refresh yet
    refresh = os.path.exists(st.session_state.db_path)
    st.session_state.orchestrator = Orchestrator(persist_directory=st.session_state.db_path, refresh_index=refresh)

if "conversation_state" not in st.session_state:
    st.session_state.conversation_state = ConversationState()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper Functions ---
def reset_conversation():
    st.session_state.conversation_state = ConversationState()
    st.session_state.messages = []
    st.rerun()

def get_issue_icon(issue_key: str) -> str:
    icons = {
        "cat3": "💰", # Wages
        "cat6": "🚪", # Dismissal
        "cat4": "⏱️", # Working Hours
        "cat7": "🛡️", # Safety/Health
        "cat7_harassment": "🗣️", # Harassment
        "others": "⚖️"
    }
    return icons.get(issue_key, "📄")

# --- Sidebar: Dashboard & Admin Tools ---
with st.sidebar:
    st.title("⚖️ 상담 대시보드")
    
    if st.button("🔄 상담 초기화", use_container_width=True, type="primary"):
        reset_conversation()
    
    st.divider()
    
    # 1. Detected Issues & Progress
    if st.session_state.conversation_state.detected_issues:
        st.subheader("📍 감지된 쟁점")
        for issue in st.session_state.conversation_state.detected_issues:
            key = issue["key"]
            name = issue["korean"]
            progress = st.session_state.conversation_state.issue_progress.get(key, 0)
            
            with st.expander(f"{get_issue_icon(key)} {name} ({progress}%)", expanded=True):
                st.progress(progress / 100.0)
                
                # Render Checklist for this issue
                checklist = st.session_state.conversation_state.issue_checklist.get(key, [])
                if checklist:
                    for item in checklist:
                        status = item["status"]
                        req = item["requirement"]
                        
                        if status == "YES":
                            st.write(f"✅ {req}")
                        elif status == "NO":
                            st.write(f"❌ {req}")
                        else:
                            st.write(f"⚪ {req}")
    else:
        st.info("상담을 시작하면 이곳에 법적 쟁점과 분석 진행 상황이 표시됩니다.")

    st.divider()
    
    # 2. Admin Tools (Re-indexing)
    with st.expander("🛠️ 관리자 도구"):
        # Detect environment
        is_streamlit_cloud = os.path.exists("/mount/src")
        
        if is_streamlit_cloud:
            import tempfile
            default_db_path = os.path.join(tempfile.gettempdir(), "chroma")
        else:
            default_db_path = "data/chroma"
            
        if "db_path" not in st.session_state:
            st.session_state.db_path = default_db_path

        st.text(f"DB 경로: {st.session_state.db_path}")

        if st.button("🔄 데이터베이스 재인덱싱"):
            from scripts.ingest import ingest_statutes
            import shutil
            
            with st.spinner("데이터 인덱싱 중... (약 1~2분 소요)"):
                try:
                    # Clear existing index if it exists
                    if os.path.exists(st.session_state.db_path):
                        shutil.rmtree(st.session_state.db_path)
                    os.makedirs(st.session_state.db_path, exist_ok=True)
                    
                    # Run Ingestion
                    ingest_statutes(persist_directory=st.session_state.db_path)
                    
                    # Force recreate orchestrator/retriever
                    st.session_state.orchestrator = Orchestrator(persist_directory=st.session_state.db_path)
                    st.success("인덱싱 완료! 새로운 정보를 기반으로 상담이 가능합니다.")
                except Exception as e:
                    st.error(f"인덱싱 실패: {e}")

# --- Main Interface: Chat ---
st.header("🤖 AI 노무사 상담 서비스")
st.caption("근로기준법에 기반하여 여러분의 상황을 분석하고 법적 권리를 안내해 드립니다.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("상황을 말씀해 주세요 (예: 3개월간 월급을 못 받았어요)"):
    # Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate Response
    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
            try:
                # Use orchestrator to process input
                state = st.session_state.conversation_state
                response_text = st.session_state.orchestrator.process_input(prompt, state)
                
                # Update Message Log in state (Orchestrator needs this for context)
                # Note: Orchestrator already appends to state.message_log inside process_input,
                # but let's ensure consistency if it doesn't.
                # Actually server.py does it, but Orchestrator.process_input doesn't always.
                # Looking at Orchestrator.process_input, it DOES NOT append to state.message_log.
                # The caller (server.py) does it.
                if not state.message_log or state.message_log[-1]["content"] != prompt:
                     state.message_log.append({"role": "user", "content": prompt})
                
                if not state.message_log or state.message_log[-1]["content"] != response_text:
                     state.message_log.append({"role": "ai", "content": response_text})

                # Display Response
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # Check for Terminal State (Final Report)
                if state.judgment_ready:
                    st.balloons()
                    st.success("상담이 완료되었습니다. 위 요약 리포트를 확인해 주세요.")
                
                # Auto-rerun to update sidebar with new state
                st.rerun()
                
            except Exception as e:
                import traceback
                st.error("상담 도중 오류가 발생했습니다.")
                st.expander("오류 상세 내용").code(traceback.format_exc())

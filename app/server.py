from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uuid
from dotenv import load_dotenv

load_dotenv()

from app.orchestrator import Orchestrator
from app.state import ConversationState

app = FastAPI(title="Legal AI Consultant API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Static Files
from fastapi.staticfiles import StaticFiles
import os


# Static file mounting moved to end to avoid blocking API routes

# In-memory session store: {client_id: {session_id: ConversationState}}
client_sessions: Dict[str, Dict[str, ConversationState]] = {}
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str
    client_id: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    detected_issues: List[dict] # Update type to support {"key": "...", "korean": "..."}
    issue_progress: Dict[str, int]
    issue_checklist: Dict[str, List[Dict[str, Any]]]
    current_step: str
    is_terminal: bool
    title: str

@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """SSE streaming endpoint for progressive UI updates"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def event_generator():
        try:
            sid = req.session_id
            client_id = req.client_id
            user_input = req.message
            
            if client_id not in client_sessions:
                client_sessions[client_id] = {}
            
            # Session limit check for NEW sessions
            if not sid and len(client_sessions[client_id]) >= 3:
                # Yield an error event instead of raising HTTPException
                error_event = {
                    "type": "error",
                    "payload": {"message": "Session limit reached (max 3)"}
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return # Stop the generator
            
            sid = sid or str(uuid.uuid4()) # Generate new SID if not provided
            
            if sid not in client_sessions[client_id]:
                client_sessions[client_id][sid] = ConversationState()
            
            state = client_sessions[client_id][sid]
            
            # Set title from first message
            if not state.message_log:
                state.session_title = user_input[:20] + ("..." if len(user_input) > 20 else "")
            
            # Process input
            response_text = orchestrator.process_input(user_input, state)
            
            # Save to log
            state.message_log.append({"role": "user", "content": user_input})
            state.message_log.append({"role": "ai", "content": response_text})
            
            # Event 1: Send checklist update FIRST
            checklist_event = {
                "type": "checklist_update",
                "payload": {
                    "detected_issues": state.detected_issues,
                    "issue_checklist": state.issue_checklist,
                    "issue_progress": state.issue_progress,
                    "current_step": state.current_step
                }
            }
            yield f"data: {json.dumps(checklist_event, ensure_ascii=False)}\n\n"
            
            # Event 2: Send AI message
            message_event = {
                "type": "message",
                "payload": {
                    "text": response_text,
                    "session_id": sid
                }
            }
            yield f"data: {json.dumps(message_event, ensure_ascii=False)}\n\n"
            
            # Event 3: Send completion signal
            done_event = {
                "type": "done",
                "payload": {
                    "is_terminal": state.judgment_ready,
                    "title": state.session_title
                }
            }
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            print(f"CRITICAL SERVER ERROR: {e}")
            traceback.print_exc()
            error_event = {
                "type": "error",
                "payload": {"message": str(e)}
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.get("/api/history/{client_id}")
async def get_history(client_id: str):
    if client_id not in client_sessions:
        return []
    
    history = []
    for sid, state in client_sessions[client_id].items():
        history.append({
            "session_id": sid,
            "title": state.session_title,
            "issues": state.detected_issues,
            "is_terminal": state.judgment_ready
        })
    return history

@app.get("/api/chat-history/{client_id}/{session_id}")
async def get_chat_history(client_id: str, session_id: str):
    if client_id not in client_sessions or session_id not in client_sessions[client_id]:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = client_sessions[client_id][session_id]
    return {
        "messages": state.message_log,
        "detected_issues": state.detected_issues,
        "is_terminal": state.judgment_ready
    }

@app.post("/api/reset")
async def reset_session(request: ChatRequest):
    cid = request.client_id
    sid = request.session_id
    if cid in client_sessions and sid in client_sessions[cid]:
        del client_sessions[cid][sid]
    return {"status": "success", "message": "Session reset"}

# Mount Static Files (Must be last to avoid catching API routes)
web_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(web_path):
    app.mount("/", StaticFiles(directory=web_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

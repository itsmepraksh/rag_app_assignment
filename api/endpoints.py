import logging
import os
import shutil
import time
import uuid
from typing import Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, status
from pydantic import BaseModel, Field
from core.rag import rag_manager
from core.graph import app_graph
from core.memory import memory_store
from core.mcp import doc_processing_mcp

router = APIRouter()
UPLOAD_DIR = "uploads"
logger = logging.getLogger(__name__)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="default", min_length=1, max_length=128)
    debug: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are official work hours?",
                    "session_id": "demo-session-1",
                    "debug": False,
                },
                {
                    "query": "Explain section 2 in simple words.",
                    "session_id": "demo-session-1",
                    "debug": True,
                },
            ]
        }
    }


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "sample_policy_handbook.pdf",
                "chunks": 18,
                "status": "processed",
            }
        }
    }


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    supporting_chunks: list[dict[str, Any]] | None = None
    agent_trace_id: str
    session_id: str
    latency_ms: float
    # Backward compatibility for current frontend.
    response: str
    sources: list[dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "Official work hours are 9:00 AM to 5:00 PM.",
                "citations": ["sample_policy_handbook.pdf (Page 2)"],
                "supporting_chunks": None,
                "agent_trace_id": "f2a1d208-e9a8-4443-8cdc-9f4067284760",
                "session_id": "demo-session-1",
                "latency_ms": 321.7,
                "response": "Official work hours are 9:00 AM to 5:00 PM.",
                "sources": [{"content": "...", "metadata": {"filename": "sample_policy_handbook.pdf"}}],
            }
        }
    }


class ConversationHistoryResponse(BaseModel):
    session_id: str
    summary: str
    recent_turns: list[dict[str, str]]
    archived_turns: list[dict[str, str]]
    all_turns: list[dict[str, str]]
    total_turns: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "demo-session-1",
                "summary": "Q: What are work hours? | A: Work hours are 9-5.",
                "recent_turns": [{"question": "Explain section 2", "answer": "Section 2 covers security controls."}],
                "archived_turns": [],
                "all_turns": [{"question": "Explain section 2", "answer": "Section 2 covers security controls."}],
                "total_turns": 1,
            }
        }
    }


class ResetConversationResponse(BaseModel):
    session_id: str
    reset: bool
    had_existing_session: bool

    model_config = {
        "json_schema_extra": {
            "example": {"session_id": "demo-session-1", "reset": True, "had_existing_session": True}
        }
    }


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        400: {"description": "Validation error for unsupported file type."},
        500: {"description": "Upload/processing failure."},
    },
)
async def upload_file(file: UploadFile = File(...)):
    started = time.perf_counter()
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")
    if not filename.lower().endswith((".pdf", ".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and MD files are supported")

    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        mcp_chunks = doc_processing_mcp.process(file_path)
        if mcp_chunks is None:
            chunks = rag_manager.process_file(file_path)
        else:
            chunks = mcp_chunks
        latency_ms = (time.perf_counter() - started) * 1000
        logger.info("upload_success file=%s chunks=%d latency_ms=%.2f", filename, len(chunks), latency_ms)
        return {"filename": filename, "chunks": len(chunks), "status": "processed"}
    except Exception as e:
        latency_ms = (time.perf_counter() - started) * 1000
        logger.exception("upload_failed file=%s latency_ms=%.2f error=%s", filename, latency_ms, str(e))
        raise HTTPException(status_code=500, detail="Upload processing failed")


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        422: {"description": "Invalid request body."},
        500: {"description": "Query processing failure."},
    },
)
async def query_docs(request: QueryRequest) -> QueryResponse:
    started = time.perf_counter()
    trace_id = str(uuid.uuid4())
    try:
        session_id = (request.session_id or "default").strip() or "default"
        mem_ctx = memory_store.build_context(session_id=session_id, recent_limit=3)
        inputs = {
            "query": request.query,
            "agent_trace_id": trace_id,
            "documents": [],
            "response": "",
            "conversation_history": mem_ctx["recent_history"],
            "conversation_summary": mem_ctx["summary"],
        }
        result = app_graph.invoke(inputs)
        answer = (result.get("answer") or result.get("response") or "").strip()
        citations = result.get("citations") or []
        docs = result.get("documents") or []
        memory_store.add_turn(session_id=session_id, question=request.query, answer=answer)
        latency_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "query_success trace_id=%s session_id=%s latency_ms=%.2f docs=%d citations=%d",
            trace_id,
            session_id,
            latency_ms,
            len(docs),
            len(citations),
        )
        return {
            "answer": answer,
            "citations": citations,
            "supporting_chunks": docs[:5] if request.debug else None,
            "agent_trace_id": trace_id,
            "session_id": session_id,
            "latency_ms": round(latency_ms, 2),
            "response": answer,
            "sources": docs[:3],
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "query_failed trace_id=%s session_id=%s latency_ms=%.2f error=%s",
            trace_id,
            getattr(request, "session_id", "unknown"),
            latency_ms,
            str(e),
        )
        raise HTTPException(status_code=500, detail="Query processing failed")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    responses={500: {"description": "History fetch failure."}},
)
async def get_conversation_history(conversation_id: str):
    try:
        sid = (conversation_id or "default").strip() or "default"
        return memory_store.get_history(sid)
    except Exception as e:
        logger.exception("history_fetch_failed session_id=%s error=%s", conversation_id, str(e))
        raise HTTPException(status_code=500, detail="Conversation history fetch failed")


@router.post(
    "/conversations/{conversation_id}/reset",
    response_model=ResetConversationResponse,
    responses={500: {"description": "Conversation reset failure."}},
)
async def reset_conversation(conversation_id: str):
    try:
        sid = (conversation_id or "default").strip() or "default"
        return memory_store.reset(sid)
    except Exception as e:
        logger.exception("conversation_reset_failed session_id=%s error=%s", conversation_id, str(e))
        raise HTTPException(status_code=500, detail="Conversation reset failed")


# Backward-compatible history route.
@router.get("/sessions/{session_id}/history", response_model=ConversationHistoryResponse)
async def get_session_history(session_id: str):
    return await get_conversation_history(session_id)


# Backward-compatible default-session helper route.
@router.get("/sessions/history", response_model=ConversationHistoryResponse)
async def get_history_default(session_id: str = Query(default="default")):
    return await get_conversation_history(session_id)

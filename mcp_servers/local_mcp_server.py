import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.rag import rag_manager


app = FastAPI(title="Local MCP Server Bundle")


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=12, ge=1, le=50)


class DocProcessRequest(BaseModel):
    file_path: str = Field(min_length=1)


def _safe_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, val in (meta or {}).items():
        if isinstance(val, (str, int, float, bool)) or val is None:
            safe[key] = val
        else:
            safe[key] = str(val)
    return safe


def _normalize_chunk(item: Any) -> dict[str, Any]:
    content = ""
    metadata: dict[str, Any] = {}
    if isinstance(item, dict):
        content = str(item.get("content", ""))
        metadata = _safe_metadata(item.get("metadata", {}) or {})
    else:
        content = str(getattr(item, "page_content", "") or "")
        metadata = _safe_metadata(getattr(item, "metadata", {}) or {})
    return {"content": content, "metadata": metadata}


@app.post("/search")
def web_search(req: WebSearchRequest):
    q = req.query.strip()
    # Local deterministic MCP response suitable for demos and tests.
    items = [
        {
            "title": f"Local Web Result for: {q}",
            "snippet": f"Synthetic MCP search result generated locally for query '{q}'.",
            "url": f"https://local-mcp.invalid/search?q={q.replace(' ', '+')}",
        },
        {
            "title": "MCP Web Search Fallback Notice",
            "snippet": "This local MCP server is a mock web source for offline assignment demos.",
            "url": "https://local-mcp.invalid/about",
        },
    ]
    return {"results": items[: req.top_k]}


@app.post("/vector/hybrid_search")
def vector_hybrid_search(req: VectorSearchRequest):
    results = rag_manager.query_hybrid(req.query, k=req.k, k_dense=max(20, req.k * 2), k_sparse=max(20, req.k * 2))
    normalized = []
    for item in results[: req.k]:
        normalized.append(
            {
                "content": str(item.get("content", "")),
                "metadata": _safe_metadata(item.get("metadata", {}) or {}),
                "dense_score": float(item.get("dense_score", 0.0) or 0.0),
                "sparse_score": float(item.get("sparse_score", 0.0) or 0.0),
                "fused_score": float(item.get("fused_score", 0.0) or 0.0),
                "hybrid_rank": int(item.get("hybrid_rank", 0) or 0),
            }
        )
    return {"results": normalized}


@app.post("/doc/process")
def document_process(req: DocProcessRequest):
    file_path = req.file_path
    if not os.path.exists(file_path):
        return {"chunks": []}
    chunks = rag_manager.process_file(file_path)
    return {"chunks": [_normalize_chunk(c) for c in chunks]}

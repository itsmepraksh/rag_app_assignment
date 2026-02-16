import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args, **_kwargs):
        return False

from core.rag import rag_manager


load_dotenv()
logger = logging.getLogger(__name__)
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


def _mock_web_results(query: str, top_k: int) -> list[dict[str, str]]:
    items = [
        {
            "title": f"Local Web Result for: {query}",
            "snippet": f"Synthetic MCP search result generated locally for query '{query}'.",
            "url": f"https://local-mcp.invalid/search?q={query.replace(' ', '+')}",
        },
        {
            "title": "MCP Web Search Fallback Notice",
            "snippet": "This local MCP server is using mock web results. Set TAVILY_API_KEY for real internet search.",
            "url": "https://local-mcp.invalid/about",
        },
    ]
    return items[:top_k]


def _tavily_search(query: str, top_k: int) -> list[dict[str, str]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    url = os.getenv("TAVILY_API_URL", "https://api.tavily.com/search").strip()
    timeout = int(os.getenv("MCP_TIMEOUT_SECONDS", "8"))
    search_depth = os.getenv("TAVILY_SEARCH_DEPTH", "basic").strip() or "basic"
    include_answer = os.getenv("TAVILY_INCLUDE_ANSWER", "false").strip().lower() == "true"
    include_raw_content = os.getenv("TAVILY_INCLUDE_RAW_CONTENT", "false").strip().lower() == "true"

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": top_k,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_raw_content": include_raw_content,
    }

    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        results = data.get("results", [])
        if not isinstance(results, list):
            return []
        normalized: list[dict[str, str]] = []
        for item in results[:top_k]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "title": str(item.get("title", "") or "Untitled"),
                    "snippet": str(item.get("content", "") or "")[:1200],
                    "url": str(item.get("url", "") or ""),
                }
            )
        return normalized
    except HTTPError as exc:
        logger.warning("tavily_http_error code=%s", exc.code)
        return []
    except URLError as exc:
        logger.warning("tavily_url_error reason=%s", exc.reason)
        return []
    except Exception as exc:
        logger.warning("tavily_unexpected_error error=%s", exc)
        return []


@app.post("/search")
def web_search(req: WebSearchRequest):
    q = req.query.strip()
    provider = os.getenv("MCP_WEB_SEARCH_PROVIDER", "mock").strip().lower()
    if provider == "tavily":
        live_results = _tavily_search(q, req.top_k)
        if live_results:
            return {"results": live_results}
    return {"results": _mock_web_results(q, req.top_k)}


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

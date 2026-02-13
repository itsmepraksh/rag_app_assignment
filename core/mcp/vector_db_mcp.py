import os
from typing import Any

from core.mcp.base import MCP_ENABLED, MCP_FAILOVER_LOCAL, post_json


class VectorDBMCPAdapter:
    def __init__(self):
        self.enabled = os.getenv("MCP_VECTOR_DB_ENABLED", "false").strip().lower() == "true"
        self.url = os.getenv("MCP_VECTOR_DB_URL", "").strip()

    def hybrid_search(self, query: str, k: int = 12) -> list[dict[str, Any]]:
        if not query.strip():
            return []

        if MCP_ENABLED and self.enabled and self.url:
            try:
                payload = {"query": query, "k": k}
                data = post_json(self.url, payload)
                items = data.get("results", [])
                if isinstance(items, list):
                    return items[:k]
            except Exception:
                if not MCP_FAILOVER_LOCAL:
                    raise

        from core.rag import rag_manager

        return rag_manager.query_hybrid(query, k=k, k_dense=max(20, k * 2), k_sparse=max(20, k * 2))


vector_db_mcp = VectorDBMCPAdapter()

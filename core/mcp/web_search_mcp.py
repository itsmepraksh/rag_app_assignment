import os
from typing import Any

from core.mcp.base import MCP_ENABLED, MCP_FAILOVER_LOCAL, post_json


class WebSearchMCPAdapter:
    def __init__(self):
        self.enabled = os.getenv("MCP_WEB_SEARCH_ENABLED", "false").strip().lower() == "true"
        self.url = os.getenv("MCP_WEB_SEARCH_URL", "").strip()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        if not (MCP_ENABLED and self.enabled and self.url):
            return []
        try:
            payload = {"query": query, "top_k": top_k}
            data = post_json(self.url, payload)
            items = data.get("results", [])
            if isinstance(items, list):
                return items[:top_k]
            return []
        except Exception:
            if MCP_FAILOVER_LOCAL:
                return []
            raise


web_search_mcp = WebSearchMCPAdapter()

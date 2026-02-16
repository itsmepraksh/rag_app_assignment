import os
from typing import Any

from core.mcp.base import MCP_ENABLED, MCP_FAILOVER_LOCAL, post_json


class DocProcessingMCPAdapter:
    def __init__(self):
        self.enabled = os.getenv("MCP_DOC_PROCESSING_ENABLED", "false").strip().lower() == "true"
        self.url = os.getenv("MCP_DOC_PROCESSING_URL", "").strip()

    def process(self, file_path: str) -> list[dict[str, Any]] | None:
        if not file_path:
            return []
        if not (MCP_ENABLED and self.enabled and self.url):
            return None
        try:
            payload = {"file_path": file_path}
            data = post_json(self.url, payload)
            chunks = data.get("chunks", [])
            if isinstance(chunks, list):
                return chunks
            return []
        except Exception:
            if MCP_FAILOVER_LOCAL:
                return None
            raise


doc_processing_mcp = DocProcessingMCPAdapter()

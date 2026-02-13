import unittest
from unittest.mock import patch
import types

from fastapi.testclient import TestClient

from main import app
from core.mcp.doc_processing_mcp import DocProcessingMCPAdapter
from core.mcp.vector_db_mcp import VectorDBMCPAdapter
from core.mcp.web_search_mcp import WebSearchMCPAdapter


class TestMCPAdapters(unittest.TestCase):
    def test_web_search_mcp_returns_mocked_results(self):
        adapter = WebSearchMCPAdapter()
        with patch("core.mcp.web_search_mcp.MCP_ENABLED", True), patch.object(
            adapter, "enabled", True
        ), patch.object(adapter, "url", "http://mock"), patch(
            "core.mcp.web_search_mcp.post_json",
            return_value={"results": [{"title": "Latest policy", "snippet": "summary", "url": "https://x"}]},
        ):
            out = adapter.search("latest policy", top_k=3)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Latest policy")

    def test_vector_db_mcp_fallbacks_to_local_hybrid(self):
        adapter = VectorDBMCPAdapter()
        fake_rag_module = types.SimpleNamespace(
            rag_manager=types.SimpleNamespace(
                query_hybrid=lambda *_args, **_kwargs: [{"content": "local result", "metadata": {}, "fused_score": 0.2}]
            )
        )
        with patch("core.mcp.vector_db_mcp.MCP_ENABLED", True), patch.object(
            adapter, "enabled", True
        ), patch.object(adapter, "url", "http://mock"), patch(
            "core.mcp.vector_db_mcp.post_json", side_effect=RuntimeError("down")
        ), patch("core.mcp.vector_db_mcp.MCP_FAILOVER_LOCAL", True), patch.dict("sys.modules", {"core.rag": fake_rag_module}):
            out = adapter.hybrid_search("query", k=3)
        self.assertEqual(out[0]["content"], "local result")

    def test_doc_processing_mcp_returns_none_on_failover(self):
        adapter = DocProcessingMCPAdapter()
        with patch("core.mcp.doc_processing_mcp.MCP_ENABLED", True), patch.object(
            adapter, "enabled", True
        ), patch.object(adapter, "url", "http://mock"), patch(
            "core.mcp.doc_processing_mcp.post_json", side_effect=RuntimeError("down")
        ), patch("core.mcp.doc_processing_mcp.MCP_FAILOVER_LOCAL", True):
            out = adapter.process("/tmp/file.pdf")
        self.assertIsNone(out)


class TestMCPGraphAndAPI(unittest.TestCase):
    def test_graph_uses_web_search_when_query_needs_web(self):
        client = TestClient(app)
        with patch("core.mcp.web_search_mcp.web_search_mcp.search", return_value=[{"title": "News", "snippet": "fresh", "url": "https://n"}]), patch(
            "core.mcp.vector_db_mcp.vector_db_mcp.hybrid_search", return_value=[]
        ), patch("core.graph.RerankingAgent._get_cross_encoder", return_value=None):
            resp = client.post("/api/query", json={"session_id": "mcp-web-1", "query": "latest policy news"})
        self.assertEqual(resp.status_code, 200)
        text = resp.json()["response"].lower()
        self.assertIn("source:", text)

    def test_upload_uses_doc_processing_mcp_then_fallback(self):
        client = TestClient(app)
        with patch("api.endpoints.doc_processing_mcp.process", return_value=[{"id": "c1"}]):
            r1 = client.post(
                "/api/upload",
                files={"file": ("test.md", b"# hello", "text/markdown")},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["chunks"], 1)

        with patch("api.endpoints.doc_processing_mcp.process", return_value=None), patch(
            "api.endpoints.rag_manager.process_file", return_value=[{"id": "c1"}, {"id": "c2"}]
        ):
            r2 = client.post(
                "/api/upload",
                files={"file": ("test.txt", b"hello", "text/plain")},
            )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["chunks"], 2)


if __name__ == "__main__":
    unittest.main()

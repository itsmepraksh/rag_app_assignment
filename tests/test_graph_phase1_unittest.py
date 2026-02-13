import sys
import types
import unittest
from unittest.mock import patch

from core.graph import (
    OrchestratorAgent,
    QueryAnalysisAgent,
    RetrievalAgent,
    RerankingAgent,
    GenerationAgent,
    CitationAgent,
    route_after_query_analysis,
    route_after_orchestrator,
    route_after_web_search,
    route_after_retrieval,
    route_after_generation,
    WebSearchAgent,
    app_graph,
)


class TestGraphPhase1(unittest.TestCase):
    def test_orchestrator_agent_initializes_defaults(self):
        out = OrchestratorAgent.run({"query": "hello"})
        self.assertEqual(out["intent"], "other")
        self.assertFalse(out["needs_web"])
        self.assertEqual(out["retrieved_docs"], [])
        self.assertEqual(out["reranked_docs"], [])
        self.assertEqual(out["citations"], [])

    def test_query_analysis_agent_detects_follow_up_and_web(self):
        out = QueryAnalysisAgent.run({"query": "Explain section 2 and latest changes"})
        self.assertEqual(out["intent"], "follow_up")
        self.assertTrue(out["needs_web"])

    def test_retrieval_agent_maps_docs(self):
        fake_mcp = types.SimpleNamespace(
            vector_db_mcp=types.SimpleNamespace(
                hybrid_search=lambda _q, **_kwargs: [
                    {
                        "content": "alpha content",
                        "metadata": {"source": "a.pdf", "page": 0},
                        "dense_score": 0.7,
                        "sparse_score": 2.4,
                        "fused_score": 0.2,
                        "hybrid_rank": 1,
                    }
                ]
            )
        )
        with patch.dict(sys.modules, {"core.mcp": fake_mcp}):
            out = RetrievalAgent.run({"query": "alpha"})

        self.assertEqual(len(out["retrieved_docs"]), 1)
        self.assertEqual(out["retrieved_docs"][0]["content"], "alpha content")
        self.assertEqual(out["documents"][0]["metadata"]["source"], "a.pdf")
        self.assertEqual(out["documents"][0]["scores"]["dense_score"], 0.7)
        self.assertEqual(out["documents"][0]["scores"]["sparse_score"], 2.4)

    def test_reranking_agent_orders_by_overlap_then_length(self):
        state = {
            "query": "policy leave",
            "retrieved_docs": [
                {"content": "policy policy leave details", "metadata": {"source": "1.pdf", "page": 0}, "scores": {"fused_score": 0.2}},
                {"content": "policy only", "metadata": {"source": "2.pdf", "page": 0}, "scores": {"fused_score": 0.1}},
            ],
        }
        with patch.object(RerankingAgent, "_get_cross_encoder", return_value=None), patch.object(
            RerankingAgent, "_llm_score", side_effect=RuntimeError("llm unavailable")
        ):
            out = RerankingAgent.run(state)
        self.assertEqual(out["reranked_docs"][0]["metadata"]["source"], "1.pdf")
        self.assertIn("rerank_score", out["reranked_docs"][0]["scores"])

    def test_generation_agent_local_fallback_when_no_docs(self):
        out = GenerationAgent.run({"query": "x", "needs_web": False, "reranked_docs": []})
        self.assertIn("couldn't find any relevant information", out["answer"].lower())

    def test_generation_agent_web_fallback_when_flagged_and_no_docs(self):
        out = GenerationAgent.run({"query": "latest stock", "needs_web": True, "reranked_docs": []})
        self.assertIn("web fallback", out["answer"].lower())

    def test_generation_agent_uses_llm(self):
        fake_llm_client = types.SimpleNamespace(generate=lambda _: "Generated answer")
        with patch.dict(sys.modules, {"core.llm_client": fake_llm_client}):
            out = GenerationAgent.run(
                {
                    "query": "What are hours?",
                    "needs_web": False,
                    "conversation_history": [{"question": "Q1", "answer": "A1"}],
                    "reranked_docs": [
                        {"content": "Work hours are 9 to 5", "metadata": {"source": "h.pdf", "page": 1}}
                    ],
                }
            )
        self.assertEqual(out["answer"], "Generated answer")
        self.assertEqual(out["response"], "Generated answer")

    def test_citation_agent_builds_unique_citations(self):
        out = CitationAgent.run(
            {
                "reranked_docs": [
                    {"content": "x", "metadata": {"source": "/tmp/a.pdf", "page": 0}},
                    {"content": "y", "metadata": {"source": "/tmp/a.pdf", "page": 0}},
                ]
            }
        )
        self.assertEqual(out["citations"], ["a.pdf (Page 1)"])

    def test_route_after_query_analysis(self):
        self.assertEqual(route_after_query_analysis({"intent": "factual"}), "orchestrator")

    def test_route_after_orchestrator(self):
        self.assertEqual(route_after_orchestrator({"use_web_search": True}), "web_search")
        self.assertEqual(route_after_orchestrator({"use_web_search": False}), "retrieval")

    def test_route_after_web_search(self):
        self.assertEqual(route_after_web_search({"web_results": [{"url": "x"}]}), "generation")
        self.assertEqual(route_after_web_search({"web_results": []}), "retrieval")

    def test_route_after_retrieval_to_generation_when_empty(self):
        self.assertEqual(route_after_retrieval({"retrieved_docs": []}), "generation")

    def test_route_after_retrieval_to_reranking_when_present(self):
        self.assertEqual(
            route_after_retrieval({"retrieved_docs": [{"content": "x", "metadata": {}}]}), "reranking"
        )

    def test_route_after_generation_to_citation_when_answer_and_docs(self):
        self.assertEqual(
            route_after_generation({"answer": "ok", "reranked_docs": [{"content": "x", "metadata": {}}]}),
            "citation",
        )

    def test_route_after_generation_to_end_when_no_docs(self):
        self.assertEqual(route_after_generation({"answer": "fallback", "reranked_docs": []}), "__end__")

    def test_full_graph_path_with_retrieval_and_citation(self):
        fake_mcp = types.SimpleNamespace(
            vector_db_mcp=types.SimpleNamespace(
                hybrid_search=lambda _q, **_kwargs: [
                    {
                        "content": "hours are 9-5",
                        "metadata": {"source": "policy.pdf", "page": 1},
                        "dense_score": 0.8,
                        "sparse_score": 1.1,
                        "fused_score": 0.25,
                        "hybrid_rank": 1,
                    }
                ]
            ),
            web_search_mcp=types.SimpleNamespace(search=lambda *_args, **_kwargs: []),
        )
        fake_llm_client = types.SimpleNamespace(generate=lambda _: "Work hours are 9 to 5.")
        with patch.dict(sys.modules, {"core.mcp": fake_mcp, "core.llm_client": fake_llm_client}), patch.object(
            RerankingAgent, "_get_cross_encoder", return_value=None
        ), patch.object(
            RerankingAgent, "_llm_score", return_value=0.9
        ):
            out = app_graph.invoke({"query": "What are work hours?", "conversation_history": []})
        self.assertEqual(out["answer"], "Work hours are 9 to 5.")
        self.assertEqual(out["citations"], ["policy.pdf (Page 2)"])

    def test_web_search_agent_returns_results(self):
        fake_mcp = types.SimpleNamespace(web_search_mcp=types.SimpleNamespace(search=lambda *_args, **_kwargs: [{"title": "t"}]))
        with patch.dict(sys.modules, {"core.mcp": fake_mcp}):
            out = WebSearchAgent.run({"query": "latest updates"})
        self.assertEqual(len(out["web_results"]), 1)

    def test_reranking_agent_uses_cross_encoder_when_available(self):
        class DummyCrossEncoder:
            def predict(self, pairs):
                self.last_pairs = pairs
                return [0.1, 0.9]

        state = {
            "query": "mobile workaround",
            "retrieved_docs": [
                {"content": "generic text", "metadata": {"source": "a.pdf"}, "scores": {"fused_score": 0.2}},
                {"content": "mobile issue workaround", "metadata": {"source": "b.pdf"}, "scores": {"fused_score": 0.1}},
            ],
        }
        with patch.object(RerankingAgent, "_get_cross_encoder", return_value=DummyCrossEncoder()):
            out = RerankingAgent.run(state)
        self.assertEqual(out["reranked_docs"][0]["metadata"]["source"], "b.pdf")
        self.assertEqual(out["reranked_docs"][0]["scores"]["rerank_model"], "cross_encoder")


if __name__ == "__main__":
    unittest.main()

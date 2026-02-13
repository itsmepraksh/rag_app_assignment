import sys
import types

from core.graph import (
    OrchestratorAgent,
    QueryAnalysisAgent,
    RetrievalAgent,
    RerankingAgent,
    GenerationAgent,
    CitationAgent,
    route_after_query_analysis,
    route_after_retrieval,
    route_after_generation,
    app_graph,
)


def test_orchestrator_agent_initializes_defaults():
    out = OrchestratorAgent.run({"query": "hello"})
    assert out["intent"] == "other"
    assert out["needs_web"] is False
    assert out["retrieved_docs"] == []
    assert out["reranked_docs"] == []
    assert out["citations"] == []


def test_query_analysis_agent_detects_follow_up_and_web():
    out = QueryAnalysisAgent.run({"query": "Explain section 2 and latest changes"})
    assert out["intent"] == "follow_up"
    assert out["needs_web"] is True


def test_retrieval_agent_maps_docs(monkeypatch):
    class DummyDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata

    fake_rag = types.SimpleNamespace(
        rag_manager=types.SimpleNamespace(
            query=lambda _: [DummyDoc("alpha content", {"source": "a.pdf", "page": 0})]
        )
    )
    monkeypatch.setitem(sys.modules, "core.rag", fake_rag)

    out = RetrievalAgent.run({"query": "alpha"})
    assert len(out["retrieved_docs"]) == 1
    assert out["retrieved_docs"][0]["content"] == "alpha content"
    assert out["documents"][0]["metadata"]["source"] == "a.pdf"


def test_reranking_agent_orders_by_overlap_then_length():
    state = {
        "query": "policy leave",
        "retrieved_docs": [
            {"content": "policy policy leave details", "metadata": {"source": "1.pdf", "page": 0}},
            {"content": "policy only", "metadata": {"source": "2.pdf", "page": 0}},
        ],
    }
    out = RerankingAgent.run(state)
    assert out["reranked_docs"][0]["metadata"]["source"] == "1.pdf"


def test_generation_agent_local_fallback_when_no_docs():
    out = GenerationAgent.run({"query": "x", "needs_web": False, "reranked_docs": []})
    assert "couldn't find any relevant information" in out["answer"].lower()


def test_generation_agent_web_fallback_when_flagged_and_no_docs():
    out = GenerationAgent.run({"query": "latest stock", "needs_web": True, "reranked_docs": []})
    assert "web fallback" in out["answer"].lower()


def test_generation_agent_uses_llm(monkeypatch):
    fake_llm_client = types.SimpleNamespace(generate=lambda _: "Generated answer")
    monkeypatch.setitem(sys.modules, "core.llm_client", fake_llm_client)
    out = GenerationAgent.run(
        {
            "query": "What are hours?",
            "needs_web": False,
            "conversation_history": [{"question": "Q1", "answer": "A1"}],
            "reranked_docs": [{"content": "Work hours are 9 to 5", "metadata": {"source": "h.pdf", "page": 1}}],
        }
    )
    assert out["answer"] == "Generated answer"
    assert out["response"] == "Generated answer"


def test_citation_agent_builds_unique_citations():
    out = CitationAgent.run(
        {
            "reranked_docs": [
                {"content": "x", "metadata": {"source": "/tmp/a.pdf", "page": 0}},
                {"content": "y", "metadata": {"source": "/tmp/a.pdf", "page": 0}},
            ]
        }
    )
    assert out["citations"] == ["a.pdf (Page 1)"]


def test_route_after_query_analysis():
    assert route_after_query_analysis({"intent": "factual"}) == "retrieval"


def test_route_after_retrieval_to_generation_when_empty():
    assert route_after_retrieval({"retrieved_docs": []}) == "generation"


def test_route_after_retrieval_to_reranking_when_present():
    assert route_after_retrieval({"retrieved_docs": [{"content": "x", "metadata": {}}]}) == "reranking"


def test_route_after_generation_to_citation_when_answer_and_docs():
    assert (
        route_after_generation(
            {"answer": "ok", "reranked_docs": [{"content": "x", "metadata": {}}]}
        )
        == "citation"
    )


def test_route_after_generation_to_end_when_no_docs():
    end_label = route_after_generation({"answer": "fallback", "reranked_docs": []})
    assert end_label == "__end__"


def test_full_graph_path_with_retrieval_and_citation(monkeypatch):
    class DummyDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata

    fake_rag = types.SimpleNamespace(
        rag_manager=types.SimpleNamespace(
            query=lambda _: [DummyDoc("hours are 9-5", {"source": "policy.pdf", "page": 1})]
        )
    )
    fake_llm_client = types.SimpleNamespace(generate=lambda _: "Work hours are 9 to 5.")
    monkeypatch.setitem(sys.modules, "core.rag", fake_rag)
    monkeypatch.setitem(sys.modules, "core.llm_client", fake_llm_client)

    out = app_graph.invoke({"query": "What are work hours?", "conversation_history": []})
    assert out["answer"] == "Work hours are 9 to 5."
    assert out["citations"] == ["policy.pdf (Page 2)"]


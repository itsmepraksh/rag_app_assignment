import os
import logging
import re
from typing import Any, Literal, TypedDict
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    query: str
    agent_trace_id: str
    conversation_history: list[dict[str, str]]
    conversation_summary: str
    web_results: list[dict[str, Any]]
    use_web_search: bool
    intent: Literal["factual", "summary", "follow_up", "other"]
    needs_web: bool
    retrieved_docs: list[dict[str, Any]]
    reranked_docs: list[dict[str, Any]]
    answer: str
    citations: list[str]
    # Backward-compatible fields used by API layer.
    response: str
    documents: list[dict[str, Any]]


def _normalize_doc(doc: Any) -> dict[str, Any]:
    if isinstance(doc, dict):
        return {
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}) or {},
        }
    return {
        "content": getattr(doc, "page_content", "") or "",
        "metadata": getattr(doc, "metadata", {}) or {},
    }


def _safe_float(text: str, default: float = 0.0) -> float:
    try:
        return float(text)
    except Exception:
        return default


class OrchestratorAgent:
    @staticmethod
    def run(state: AgentState) -> AgentState:
        needs_web = state.get("needs_web", False)
        has_web_results = bool(state.get("web_results"))
        use_web_search = bool(needs_web and not has_web_results)
        return {
            "intent": state.get("intent", "other"),
            "agent_trace_id": state.get("agent_trace_id", ""),
            "needs_web": needs_web,
            "retrieved_docs": state.get("retrieved_docs", []),
            "reranked_docs": state.get("reranked_docs", []),
            "answer": state.get("answer", ""),
            "citations": state.get("citations", []),
            "response": state.get("response", ""),
            "documents": state.get("documents", []),
            "conversation_summary": state.get("conversation_summary", ""),
            "web_results": state.get("web_results", []),
            "use_web_search": use_web_search,
        }


class QueryAnalysisAgent:
    @staticmethod
    def run(state: AgentState) -> AgentState:
        query = (state.get("query") or "").strip().lower()
        follow_up_markers = ("section ", "that ", "it ", "this ", "those ", "these ")
        web_markers = ("latest", "today", "current", "news", "internet", "web")
        summary_markers = ("summarize", "summary", "explain", "overview")

        if any(marker in query for marker in follow_up_markers):
            intent = "follow_up"
        elif any(marker in query for marker in summary_markers):
            intent = "summary"
        elif query:
            intent = "factual"
        else:
            intent = "other"

        needs_web = any(marker in query for marker in web_markers)
        return {"intent": intent, "needs_web": needs_web}


class RetrievalAgent:
    @staticmethod
    def run(state: AgentState) -> AgentState:
        from core.mcp import vector_db_mcp

        query = state.get("query", "")
        hybrid_results = vector_db_mcp.hybrid_search(query, k=12)
        normalized = [
            {
                "content": item.get("content", ""),
                "metadata": item.get("metadata", {}),
                "scores": {
                    "dense_score": item.get("dense_score", 0.0),
                    "sparse_score": item.get("sparse_score", 0.0),
                    "fused_score": item.get("fused_score", 0.0),
                },
                "hybrid_rank": item.get("hybrid_rank"),
            }
            for item in hybrid_results
        ]
        logger.info("retrieval query=%r chunks=%d", query[:120], len(normalized))
        return {"retrieved_docs": normalized, "documents": normalized}


class WebSearchAgent:
    @staticmethod
    def run(state: AgentState) -> AgentState:
        from core.mcp import web_search_mcp

        query = state.get("query", "")
        results = web_search_mcp.search(query, top_k=5)
        return {"web_results": results}


class RerankingAgent:
    _cross_encoder = None
    _cross_encoder_attempted = False

    @classmethod
    def _get_cross_encoder(cls):
        if cls._cross_encoder_attempted:
            return cls._cross_encoder
        cls._cross_encoder_attempted = True
        try:
            from sentence_transformers import CrossEncoder

            cls._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            cls._cross_encoder = None
        return cls._cross_encoder

    @staticmethod
    def _heuristic_score(query: str, content: str) -> float:
        q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        c_terms = set(re.findall(r"[a-z0-9]+", content.lower()))
        if not q_terms:
            return 0.0
        overlap = len(q_terms.intersection(c_terms))
        return overlap / len(q_terms)

    @staticmethod
    def _llm_score(query: str, content: str) -> float:
        from core.llm_client import generate

        prompt = f"""
Score relevance from 0 to 1 for the passage answering the query.
Return ONLY a decimal number.
Query: {query}
Passage: {content[:1800]}
Score:
"""
        raw = (generate(prompt) or "").strip()
        match = re.search(r"([01](?:\.\d+)?)", raw)
        if not match:
            return 0.0
        return min(1.0, max(0.0, _safe_float(match.group(1), 0.0)))

    @staticmethod
    def run(state: AgentState) -> AgentState:
        query = state.get("query", "")
        docs = state.get("retrieved_docs", [])
        if not docs:
            return {"reranked_docs": [], "documents": []}

        cross_encoder = RerankingAgent._get_cross_encoder()
        reranked: list[dict[str, Any]] = []

        if cross_encoder is not None:
            pairs = [(query, d.get("content", "")) for d in docs]
            try:
                ce_scores = cross_encoder.predict(pairs)
                for doc, ce_score in zip(docs, ce_scores):
                    doc_copy = {**doc}
                    scores = {**(doc.get("scores") or {})}
                    scores["rerank_score"] = float(ce_score)
                    scores["rerank_model"] = "cross_encoder"
                    doc_copy["scores"] = scores
                    reranked.append(doc_copy)
            except Exception:
                reranked = []

        if not reranked:
            for doc in docs:
                doc_copy = {**doc}
                content = doc.get("content", "")
                score = 0.0
                model = "heuristic"
                try:
                    score = RerankingAgent._llm_score(query, content)
                    model = "llm_rerank"
                except Exception:
                    score = RerankingAgent._heuristic_score(query, content)
                    model = "heuristic"
                scores = {**(doc.get("scores") or {})}
                scores["rerank_score"] = float(score)
                scores["rerank_model"] = model
                doc_copy["scores"] = scores
                reranked.append(doc_copy)

        reranked.sort(
            key=lambda d: (
                d.get("scores", {}).get("rerank_score", 0.0),
                d.get("scores", {}).get("fused_score", 0.0),
            ),
            reverse=True,
        )
        top_k = reranked[:5]
        for idx, item in enumerate(top_k, start=1):
            item["rerank_rank"] = idx
        return {"reranked_docs": top_k, "documents": top_k}


class GenerationAgent:
    FALLBACK_LOCAL = "I couldn't find any relevant information in the documents provided."
    FALLBACK_WEB = "I need web fallback for this query, but web retrieval is not configured in this environment."

    @staticmethod
    def run(state: AgentState) -> AgentState:
        from core.llm_client import generate

        docs = state.get("reranked_docs", [])
        web_results = state.get("web_results", [])
        if state.get("needs_web") and web_results:
            top = web_results[0]
            title = top.get("title", "Web result")
            snippet = top.get("snippet", "")
            url = top.get("url", "")
            response = f"{title}: {snippet}".strip()
            if url:
                response = f"{response}\nSource: {url}"
            return {"answer": response, "response": response}
        if state.get("needs_web") and not docs:
            return {"answer": GenerationAgent.FALLBACK_WEB, "response": GenerationAgent.FALLBACK_WEB}
        if not docs:
            return {"answer": GenerationAgent.FALLBACK_LOCAL, "response": GenerationAgent.FALLBACK_LOCAL}

        context_parts = []
        for doc in docs:
            metadata = doc.get("metadata", {})
            source = os.path.basename(metadata.get("source", "Unknown"))
            page = metadata.get("page", 0) + 1
            context_parts.append(f"Source: {source} (Page {page})\nContent: {doc.get('content', '')}")
        context = "\n\n---\n\n".join(context_parts)

        history = state.get("conversation_history", [])[-3:]
        summary_text = (state.get("conversation_summary") or "").strip()
        history_text = "\n\n".join(
            f"Question: {turn.get('question', '').strip()}\nAnswer: {turn.get('answer', '').strip()}"
            for turn in history
            if turn.get("question") or turn.get("answer")
        ) or "No prior conversation."

        prompt = f"""
You are an advanced RAG assistant.

Instruction:
- Answer ONLY using the provided context.
- If context is insufficient, reply exactly:
  "I don't have enough information in the uploaded documents to answer this."
- Use conversation history only to resolve references in follow-up questions.
- Do not use outside knowledge.
- Give a direct answer only.

Conversation History:
{history_text}

Conversation Summary:
{summary_text or "No prior summary."}

Retrieved Context:
{context}

User Question:
{state.get("query", "")}

Final Answer:
"""

        try:
            answer = (generate(prompt) or "").strip()
            if not answer:
                answer = "[GENERATOR_ERROR] code=EMPTY_RESPONSE message=LLM returned an empty response."
        except Exception as exc:
            answer = f"[GENERATOR_ERROR] code=LLM_EXCEPTION message={str(exc)}"

        return {"answer": answer, "response": answer}


class CitationAgent:
    @staticmethod
    def run(state: AgentState) -> AgentState:
        citations: list[str] = []
        for doc in state.get("reranked_docs", []):
            metadata = doc.get("metadata", {})
            source = os.path.basename(metadata.get("source", "Unknown"))
            page = metadata.get("page", 0) + 1
            citations.append(f"{source} (Page {page})")
        unique = list(dict.fromkeys(citations))
        return {"citations": unique, "documents": state.get("reranked_docs", [])}


def route_after_query_analysis(state: AgentState) -> str:
    return "orchestrator"


def route_after_orchestrator(state: AgentState) -> str:
    if state.get("use_web_search"):
        return "web_search"
    return "retrieval"


def route_after_web_search(state: AgentState) -> str:
    if state.get("web_results"):
        return "generation"
    return "retrieval"


def route_after_retrieval(state: AgentState) -> str:
    if not state.get("retrieved_docs"):
        return "generation"
    return "reranking"


def route_after_generation(state: AgentState) -> str:
    if state.get("reranked_docs") and state.get("answer"):
        return "citation"
    return END


workflow = StateGraph(AgentState)
workflow.add_node("query_analysis", QueryAnalysisAgent.run)
workflow.add_node("orchestrator", OrchestratorAgent.run)
workflow.add_node("web_search", WebSearchAgent.run)
workflow.add_node("retrieval", RetrievalAgent.run)
workflow.add_node("reranking", RerankingAgent.run)
workflow.add_node("generation", GenerationAgent.run)
workflow.add_node("citation", CitationAgent.run)

workflow.set_entry_point("query_analysis")
workflow.add_conditional_edges(
    "query_analysis",
    route_after_query_analysis,
    {"orchestrator": "orchestrator"},
)
workflow.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {"web_search": "web_search", "retrieval": "retrieval"},
)
workflow.add_conditional_edges(
    "web_search",
    route_after_web_search,
    {"generation": "generation", "retrieval": "retrieval"},
)
workflow.add_conditional_edges(
    "retrieval",
    route_after_retrieval,
    {"reranking": "reranking", "generation": "generation"},
)
workflow.add_edge("reranking", "generation")
workflow.add_conditional_edges(
    "generation",
    route_after_generation,
    {"citation": "citation", END: END},
)
workflow.add_edge("citation", END)

app_graph = workflow.compile()

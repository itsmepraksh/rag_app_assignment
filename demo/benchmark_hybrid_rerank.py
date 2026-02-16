import os
import sys
from statistics import mean

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.graph import RerankingAgent
from core.rag import rag_manager


EVAL_QUERIES = [
    {
        "query": "What are official work hours?",
        "expect_terms": ["work", "hours"],
    },
    {
        "query": "How many paid annual leave days are allowed?",
        "expect_terms": ["annual", "leave"],
    },
    {
        "query": "What is the known mobile issue workaround?",
        "expect_terms": ["mobile", "workaround"],
    },
]


def _ensure_demo_docs_indexed():
    demo_files = [
        os.path.abspath("demo/sample_policy_handbook.pdf"),
        os.path.abspath("demo/sample_product_release_notes.pdf"),
    ]
    for path in demo_files:
        if os.path.exists(path):
            rag_manager.process_file(path)


def _relevance_score(content: str, expect_terms: list[str]) -> float:
    text = (content or "").lower()
    if not expect_terms:
        return 0.0
    hits = sum(1 for term in expect_terms if term.lower() in text)
    return hits / len(expect_terms)


def _avg_topk_score(items: list[dict], expect_terms: list[str], k: int = 5) -> float:
    if not items:
        return 0.0
    subset = items[:k]
    return mean(_relevance_score(item.get("content", ""), expect_terms) for item in subset)


def run_benchmark():
    _ensure_demo_docs_indexed()
    rows = []
    for case in EVAL_QUERIES:
        query = case["query"]
        expect_terms = case["expect_terms"]

        dense = rag_manager.query_dense(query, k=5)
        hybrid = rag_manager.query_hybrid(query, k=8, k_dense=20, k_sparse=20)
        reranked = RerankingAgent.run({"query": query, "retrieved_docs": hybrid}).get("reranked_docs", [])

        dense_score = _avg_topk_score(dense, expect_terms, k=5)
        hybrid_score = _avg_topk_score(hybrid, expect_terms, k=5)
        rerank_score = _avg_topk_score(reranked, expect_terms, k=5)
        rows.append((query, dense_score, hybrid_score, rerank_score))

    print("\nHybrid Retrieval + Rerank Benchmark")
    print("-" * 78)
    print(f"{'Query':45} {'Dense':>10} {'Hybrid':>10} {'Hybrid+Rerank':>14}")
    print("-" * 78)
    for query, dense_s, hybrid_s, rerank_s in rows:
        print(f"{query[:45]:45} {dense_s:10.3f} {hybrid_s:10.3f} {rerank_s:14.3f}")
    print("-" * 78)
    print(
        f"{'Average':45} "
        f"{mean(r[1] for r in rows):10.3f} "
        f"{mean(r[2] for r in rows):10.3f} "
        f"{mean(r[3] for r in rows):14.3f}"
    )


if __name__ == "__main__":
    run_benchmark()

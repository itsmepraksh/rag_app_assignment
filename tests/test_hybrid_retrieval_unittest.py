import unittest
from unittest.mock import patch

from langchain_core.documents import Document

from core.rag import RAGManager


class DummyFAISS:
    def similarity_search_with_score(self, _query, k=10):
        docs = [
            Document(page_content="policy annual leave details", metadata={"source": "a.pdf", "chunk_id": "a1", "page_number": 1}),
            Document(page_content="mobile upload workaround", metadata={"source": "b.pdf", "chunk_id": "b1", "page_number": 2}),
        ]
        out = [(docs[0], 0.2), (docs[1], 0.7)]
        return out[:k]


class TestHybridRetrieval(unittest.TestCase):
    def setUp(self):
        self.manager = RAGManager.__new__(RAGManager)
        self.manager.db = DummyFAISS()

    def test_query_dense_returns_scores(self):
        out = self.manager.query_dense("annual leave", k=2)
        self.assertEqual(len(out), 2)
        self.assertIn("dense_score", out[0])
        self.assertEqual(out[0]["dense_rank"], 1)

    def test_query_hybrid_fuses_dense_and_sparse_scores(self):
        sparse = [
            (Document(page_content="mobile upload workaround", metadata={"source": "b.pdf", "chunk_id": "b1", "page_number": 2}), 3.4),
            (Document(page_content="policy annual leave details", metadata={"source": "a.pdf", "chunk_id": "a1", "page_number": 1}), 1.0),
        ]
        with patch.object(self.manager, "_sparse_bm25_search", return_value=sparse):
            out = self.manager.query_hybrid("mobile workaround", k=5, k_dense=5, k_sparse=5)

        self.assertGreaterEqual(len(out), 2)
        self.assertIn("fused_score", out[0])
        self.assertIn("sparse_score", out[0])
        self.assertIn("dense_score", out[0])
        self.assertEqual(out[0]["hybrid_rank"], 1)


if __name__ == "__main__":
    unittest.main()

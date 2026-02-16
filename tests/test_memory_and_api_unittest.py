import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.memory import ConversationMemoryStore
from main import app


class TestConversationMemory(unittest.TestCase):
    def test_recent_buffer_and_summary_rollup(self):
        store = ConversationMemoryStore(recent_buffer_size=2)
        store.add_turn("s1", "Q1", "A1")
        store.add_turn("s1", "Q2", "A2")
        store.add_turn("s1", "Q3", "A3")

        ctx = store.build_context("s1", recent_limit=3)
        self.assertEqual(len(ctx["recent_history"]), 2)
        self.assertIn("Q1", ctx["summary"])

        history = store.get_history("s1")
        self.assertEqual(history["total_turns"], 3)
        self.assertEqual(len(history["archived_turns"]), 1)

    def test_pronoun_reference_follow_up_turns_remain_available(self):
        store = ConversationMemoryStore(recent_buffer_size=6)
        store.add_turn("s2", "Tell me the leave policy details.", "Policy says 20 days annual leave.")
        store.add_turn("s2", "Can you summarize section 2?", "Section 2 is about account security.")
        ctx = store.build_context("s2", recent_limit=3)
        recent_questions = [t["question"] for t in ctx["recent_history"]]
        self.assertTrue(any("leave policy" in q.lower() for q in recent_questions))
        self.assertTrue(any("section 2" in q.lower() for q in recent_questions))


class TestConversationAPI(unittest.TestCase):
    def test_query_uses_session_id_and_history_endpoint_returns_turns(self):
        client = TestClient(app)
        with patch("api.endpoints.app_graph.invoke", return_value={"response": "Answer 1", "documents": [], "citations": []}):
            r1 = client.post("/api/query", json={"session_id": "sess-abc", "query": "What is that policy?"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["session_id"], "sess-abc")
        self.assertEqual(r1.json()["answer"], "Answer 1")
        self.assertIn("agent_trace_id", r1.json())
        self.assertIn("latency_ms", r1.json())

        with patch("api.endpoints.app_graph.invoke", return_value={"response": "Answer 2", "documents": [{"content": "x"}], "citations": ["a.pdf (Page 1)"]}):
            r2 = client.post("/api/query", json={"session_id": "sess-abc", "query": "Explain section 2.", "debug": True})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["citations"], ["a.pdf (Page 1)"])
        self.assertIsNotNone(r2.json()["supporting_chunks"])

        rh = client.get("/api/conversations/sess-abc")
        self.assertEqual(rh.status_code, 200)
        payload = rh.json()
        self.assertEqual(payload["session_id"], "sess-abc")
        self.assertGreaterEqual(payload["total_turns"], 2)
        questions = [t.get("question", "") for t in payload["all_turns"]]
        self.assertTrue(any("that policy" in q.lower() for q in questions))
        self.assertTrue(any("section 2" in q.lower() for q in questions))

    def test_reset_conversation_endpoint(self):
        client = TestClient(app)
        with patch("api.endpoints.app_graph.invoke", return_value={"response": "Answer 1", "documents": [], "citations": []}):
            client.post("/api/query", json={"session_id": "sess-reset", "query": "Q1"})
        r = client.post("/api/conversations/sess-reset/reset")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["reset"])
        h = client.get("/api/conversations/sess-reset")
        self.assertEqual(h.status_code, 200)
        self.assertEqual(h.json()["total_turns"], 0)


if __name__ == "__main__":
    unittest.main()

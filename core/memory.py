from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class SessionMemory:
    recent_turns: list[dict[str, str]] = field(default_factory=list)
    summary_text: str = ""
    archived_turns: list[dict[str, str]] = field(default_factory=list)


class ConversationMemoryStore:
    def __init__(self, recent_buffer_size: int = 6):
        self.recent_buffer_size = recent_buffer_size
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = Lock()

    def _get(self, session_id: str) -> SessionMemory:
        sid = (session_id or "default").strip() or "default"
        if sid not in self._sessions:
            self._sessions[sid] = SessionMemory()
        return self._sessions[sid]

    def _summarize_turn(self, turn: dict[str, str]) -> str:
        q = (turn.get("question", "") or "").strip()
        a = (turn.get("answer", "") or "").strip()
        q_short = q[:120]
        a_short = a[:180]
        return f"Q: {q_short} | A: {a_short}"

    def _rollup_if_needed(self, mem: SessionMemory) -> None:
        while len(mem.recent_turns) > self.recent_buffer_size:
            oldest = mem.recent_turns.pop(0)
            mem.archived_turns.append(oldest)
            line = self._summarize_turn(oldest)
            if mem.summary_text:
                mem.summary_text = f"{mem.summary_text}\n{line}"
            else:
                mem.summary_text = line

    def add_turn(self, session_id: str, question: str, answer: str) -> None:
        with self._lock:
            mem = self._get(session_id)
            mem.recent_turns.append({"question": question, "answer": answer})
            self._rollup_if_needed(mem)

    def build_context(self, session_id: str, recent_limit: int = 3) -> dict[str, Any]:
        with self._lock:
            mem = self._get(session_id)
            recent = mem.recent_turns[-recent_limit:] if recent_limit > 0 else []
            return {
                "recent_history": list(recent),
                "summary": mem.summary_text,
            }

    def get_history(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            mem = self._get(session_id)
            all_turns = list(mem.archived_turns) + list(mem.recent_turns)
            return {
                "session_id": (session_id or "default").strip() or "default",
                "summary": mem.summary_text,
                "recent_turns": list(mem.recent_turns),
                "archived_turns": list(mem.archived_turns),
                "all_turns": all_turns,
                "total_turns": len(all_turns),
            }

    def reset(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            sid = (session_id or "default").strip() or "default"
            existed = sid in self._sessions
            self._sessions[sid] = SessionMemory()
            return {"session_id": sid, "reset": True, "had_existing_session": existed}


memory_store = ConversationMemoryStore(recent_buffer_size=6)

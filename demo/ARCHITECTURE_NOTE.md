# Architecture Note (Required Agents)

This project uses a six-agent LangGraph pipeline:

1. `QueryAnalysisAgent`
- Parses user query intent and sets `needs_web`.

2. `OrchestratorAgent`
- Chooses route: WebSearch branch vs local Retrieval branch.

3. `RetrievalAgent`
- Pulls hybrid candidates via Vector DB MCP abstraction (MCP-first, local fallback).

4. `RerankingAgent`
- Reorders candidates using cross-encoder, then LLM fallback, then heuristic fallback.

5. `GenerationAgent`
- Generates final answer from reranked context and session memory (recent + summary).

6. `CitationAgent`
- Formats final citations (`filename`, `page`) from supporting chunks.

MCP adapters:
- `core/mcp/web_search_mcp.py`
- `core/mcp/vector_db_mcp.py`
- `core/mcp/doc_processing_mcp.py`

Conversation memory:
- Session-scoped with recent buffer + summary rollup (`core/memory.py`).

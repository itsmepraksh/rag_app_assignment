# DocuMind AI

DocuMind AI helps you upload documents and ask questions in plain language.
It gives answers with citations, remembers short conversation context, and can optionally use live web search.

## Deliverables

1. Source code repository
- This repository contains the full application code.

2. Documentation
- `/Users/prakashsamanta/workSpace/assignment1/README.md` (this file)
- `/Users/prakashsamanta/workSpace/assignment1/docs/NON_TECH_USER_GUIDE.md`
- `/Users/prakashsamanta/workSpace/assignment1/DELIVERABLES.md`

3. Demo
- Sample documents:
  - `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`
  - `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`
  - `/Users/prakashsamanta/workSpace/assignment1/demo/sample_scanned_text_ocr.pdf`
- Example demo queries:
  - `/Users/prakashsamanta/workSpace/assignment1/demo/EXAMPLE_QUERIES.md`

## Quick Start (Simple)

1. Open Terminal in project folder:
```bash
cd /Users/prakashsamanta/workSpace/assignment1
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Make sure Ollama is running and model exists:
```bash
ollama pull llama3:8b
brew services start ollama
```

5. Start MCP server (second terminal):
```bash
cd /Users/prakashsamanta/workSpace/assignment1
./scripts/start_local_mcp.sh
```

6. Start main app (first terminal):
```bash
cd /Users/prakashsamanta/workSpace/assignment1
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

7. Open in browser:
- `http://localhost:8000`

## How To Use (Non-Technical)

1. Upload one or more files (`.pdf`, `.txt`, `.md`).
2. Ask a question in normal English.
3. Read the answer and citation chips.
4. Ask follow-up questions in the same session.
5. Click `Reset` when you want to clear memory for that session.

## Real Web Search Setup (Tavily)

By default, local MCP can return mock web results.
To enable real web search:

1. Create free API key from [Tavily](https://tavily.com).
2. Update `/Users/prakashsamanta/workSpace/assignment1/.env`:
```env
MCP_ENABLED=true
MCP_FAILOVER_LOCAL=false
MCP_WEB_SEARCH_ENABLED=true
MCP_WEB_SEARCH_URL=http://127.0.0.1:9100/search
MCP_WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-your-key-here
```
3. Restart both servers.

If API key is missing or invalid, system falls back to local mock web results.

## What Each Feature Does

- Document Q&A: Answers from uploaded files.
- Citations: Shows file/page references.
- Memory: Remembers recent turns in the same session.
- Hybrid retrieval + reranking: Improves answer relevance behind the scenes.
- MCP integration: Connects to web search, vector retrieval, and doc processing endpoints.

## API Endpoints (For Developers)

- `POST /api/upload`
- `POST /api/query`
- `GET /api/conversations/{conversation_id}`
- `POST /api/conversations/{conversation_id}/reset`

## Troubleshooting

- `Connection refused` on MCP:
  - Start MCP server with `./scripts/start_local_mcp.sh`.
- Web result shows `local-mcp.invalid`:
  - Tavily key is missing, wrong, or not loaded.
- `500` error on query:
  - Check both terminals for stack trace and restart services.
- Slow response:
  - First query can be slower due to model warmup.

## Project Structure

- `api/` - FastAPI routes
- `core/` - graph, llm, rag, memory, MCP adapters
- `mcp_servers/` - local MCP server implementation
- `static/` - frontend UI
- `demo/` - sample files and demo scripts
- `docs/` - user-friendly documentation


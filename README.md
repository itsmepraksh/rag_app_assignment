# DocuMind AI - Advanced RAG Document Q&A

DocuMind AI is a FastAPI-based RAG system that lets you upload PDF/TXT files and ask questions grounded in those documents.

## Features

- Document upload (`.pdf`, `.txt`)
- Chunking + embeddings + FAISS vector search
- LangGraph workflow with conditional routing
- Context-only generation using local Ollama
- Citation appending (`filename`, `page`)
- Lightweight conversation memory (last 3 turns for follow-ups)
- Short-answer quality check with optional regeneration

## Project Structure

- `main.py`: app entrypoint, CORS, API mounting, static UI hosting
- `api/endpoints.py`: upload/query API routes and conversation memory store
- `core/rag.py`: loaders, chunking, embeddings, FAISS index management
- `core/graph.py`: LangGraph nodes and conditional edges
- `static/`: frontend files (`index.html`, `app.js`, `style.css`)
- `db/faiss_index/`: persisted vector index
- `uploads/`: uploaded user files

## How To Run

1. Create and activate virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start Ollama and pull the model:

```bash
ollama pull llama3:8b
brew services start ollama
```

4. Configure `.env` (no API key needed):

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3:8b
LLM_TIMEOUT_SECONDS=45
```

5. Start server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

6. Open app in browser:

```text
http://localhost:8000
```

You will see startup model pre-warm and inference logs in console, including retrieval chunk count and LLM latency.

## Ollama Setup

1. Install Ollama on your machine.
2. Pull model: `ollama pull llama3:8b`
3. Ensure Ollama service is running.
4. Keep default host (`http://127.0.0.1:11434`) or set `OLLAMA_HOST` in `.env`.
5. Model is configurable via `.env` using `LLM_MODEL` (default: `llama3:8b`).

## Troubleshoot

1. `Failed to connect to Ollama`
- Start service: `brew services start ollama`
- Check service: `ollama list`

2. `model not found`
- Pull model manually: `ollama pull llama3:8b`
- Ensure `.env` model name matches pulled model

3. Slow first response
- First inference may be slower due to model load
- App pre-warms model on startup to reduce this

4. Empty or fallback answer
- Verify documents were uploaded and chunked
- Ask grounded questions based on uploaded text

## LangGraph Architecture Diagram

```mermaid
flowchart TD
    A["User Query"] --> B["Retriever Node<br/>FAISS Similarity Search"]
    B --> C["Validator Node<br/>Docs Found?"]
    C -->|No| Z["Fallback Response<br/>No relevant information"]
    C -->|Yes| D["Generator Node<br/>Ollama (Context + Last 3 Turns)"]
    D --> E["Quality Check Node<br/>Answer too short?"]
    E -->|Yes, retry limit not reached| D
    E -->|No| F["Citation Node<br/>Append filename + page"]
    F --> G["Final Response"]
```

## Notes

- Conversation memory is currently in-process memory (not per-user persistent storage).
- CORS is open for development (`allow_origins=["*"]`).

## Demo Assets

- Sample PDFs: `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`, `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`
- Demo questions and flow: `/Users/prakashsamanta/workSpace/assignment1/demo/DEMO_GUIDE.md`

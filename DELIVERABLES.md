# Deliverables

## 1) Source Code Repository

Repository root:
- `/Users/prakashsamanta/workSpace/assignment1`

Main components:
- Backend API: `/Users/prakashsamanta/workSpace/assignment1/api`
- Core logic (RAG, graph, MCP adapters): `/Users/prakashsamanta/workSpace/assignment1/core`
- Local MCP server: `/Users/prakashsamanta/workSpace/assignment1/mcp_servers`
- Frontend UI: `/Users/prakashsamanta/workSpace/assignment1/static`

## 2) Documentation

- Primary guide: `/Users/prakashsamanta/workSpace/assignment1/README.md`
- Non-technical guide: `/Users/prakashsamanta/workSpace/assignment1/docs/NON_TECH_USER_GUIDE.md`
- This deliverables index: `/Users/prakashsamanta/workSpace/assignment1/DELIVERABLES.md`

## 3) Demo Package

Sample documents for testing:
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_scanned_text_ocr.pdf`

Example query scripts:
- `/Users/prakashsamanta/workSpace/assignment1/demo/EXAMPLE_QUERIES.md`
- `/Users/prakashsamanta/workSpace/assignment1/demo/DEMO_GUIDE.md`

How to run demo quickly:
1. Start MCP server: `./scripts/start_local_mcp.sh`
2. Start app: `./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
3. Open `http://localhost:8000`
4. Upload sample files and run queries from `demo/EXAMPLE_QUERIES.md`


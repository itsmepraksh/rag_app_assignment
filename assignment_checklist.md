# Phase 0 - Baseline and Acceptance Criteria

Date baseline frozen: 2026-02-13
Project: DocuMind AI (`/Users/prakashsamanta/workSpace/assignment1`)

## Scope Freeze (Current Baseline Snapshot)

In scope for this baseline:
- Upload `.pdf` and `.txt` documents
- Chunk documents, embed, and index with FAISS
- Query over indexed documents using LangGraph flow
- Use recent conversation turns for follow-up resolution
- Return answer with citation metadata (source + page) in backend graph state
- Grounded fallback when retrieval is insufficient

Out of scope for this baseline:
- True web-search fallback (calling external web sources when local docs are insufficient)
- Persistent per-user chat memory across restarts
- Automated end-to-end test suite

## Requirement Mapping and Pass/Fail Checklist (Baseline)

Legend:
- Status: `PASS`, `PARTIAL`, `FAIL`
- Test type: `Manual`, `Automated`, or `None`

| Req ID | Requirement | Acceptance Criteria (Pass/Fail) | Code Location | Test Mapping | Status |
|---|---|---|---|---|---|
| R1 | Document upload | `POST /api/upload` accepts `.pdf`/`.txt`; rejects other formats with HTTP 400; returns chunk count on success | `api/endpoints.py` (`upload_file`), `static/app.js` upload flow | Manual: upload one `.pdf`, one `.txt`, and one invalid extension | PASS |
| R2 | Chunking + vector indexing | Uploaded files are split into chunks and persisted into FAISS index | `core/rag.py` (`process_file`, `_init_db`), `db/faiss_index/` | Manual: upload file and verify non-zero `chunks` in API response | PASS |
| R3 | Retrieval-augmented response flow | Query goes through retriever -> validator -> generator -> quality check -> citation path | `core/graph.py` graph construction and nodes | Manual: ask factual question from uploaded doc and verify correct answer | PASS |
| R4 | Follow-up question handling | Follow-up using references like "section 2" is resolved using recent conversation turns | `api/endpoints.py` (`conversation_history[-3:]`), `core/graph.py` prompt history section | Manual: ask base question, then follow-up "Explain section 2 in simple words." | PASS |
| R5 | Citation support | Backend collects unique citations as `filename (Page N)` from retrieved chunks | `core/graph.py` (`citation_node`) | Manual/API: inspect graph output during query execution | PASS (backend) |
| R6 | Citation visibility in UI response | User can clearly see citations in final chat answer | `static/app.js` query rendering, API response contract | Manual: ask question and confirm citations rendered in chat | FAIL (not rendered by current UI/API payload) |
| R7 | Fallback behavior (no relevant local info) | For unrelated question, system does not hallucinate and returns insufficiency/fallback response | `core/graph.py` (`validator_node` + generator instruction), `demo/DEMO_GUIDE.md` | Manual: ask unrelated question (FIFA example) | PASS |
| R8 | Web fallback (external sources) | If local docs are insufficient, system fetches from web and cites web source | N/A (no implementation found) | None | FAIL (out of scope in current baseline) |

## Test Checklist (Execution Sheet)

- [ ] T1 Upload valid PDF from `demo/sample_policy_handbook.pdf` -> expect status `processed` and `chunks > 0`
- [ ] T2 Upload valid PDF from `demo/sample_product_release_notes.pdf` -> expect status `processed` and `chunks > 0`
- [ ] T3 Upload invalid file extension (e.g., `.docx`) -> expect HTTP 400
- [ ] T4 Ask: "What are the official work hours in the handbook?" -> expect grounded answer
- [ ] T5 Ask follow-up: "Explain section 2 in simple words." -> expect contextually linked answer
- [ ] T6 Confirm citation text is visible to user in chat output -> expected fail in current baseline
- [ ] T7 Ask unrelated: "Who won the last FIFA World Cup?" -> expect insufficiency/fallback behavior
- [ ] T8 Trigger web fallback path -> expected fail (not implemented)

## Baseline Acceptance Decision

Phase 0 baseline acceptance should be evaluated as:
- Core local RAG behavior: acceptable (`R1-R4, R7` pass)
- Citation end-user UX: not complete (`R6` fail)
- Web fallback requirement: not implemented (`R8` fail)

Overall: **PARTIAL PASS** for baseline snapshot, with explicit gaps tracked in `R6` and `R8`.

---

## Phase 9 Validation (2026-02-13)

Automated regression run:
- `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python -m unittest -q tests/test_memory_and_api_unittest.py tests/test_mcp_integration_unittest.py tests/test_graph_phase1_unittest.py tests/test_document_processing_unittest.py tests/test_hybrid_retrieval_unittest.py`
- Result: `Ran 32 tests ... OK`

Checklist re-validation against current implementation:

| Req ID | Current Status | Validation Evidence |
|---|---|---|
| R1 | PASS | Upload types now support `.pdf/.txt/.md`; API validation + tests in `tests/test_mcp_integration_unittest.py` |
| R2 | PASS | Chunking/indexing path active in `core/rag.py`; upload tests and retrieval tests pass |
| R3 | PASS | Multi-agent LangGraph route tested in `tests/test_graph_phase1_unittest.py` |
| R4 | PASS | Session memory + follow-up reference tests in `tests/test_memory_and_api_unittest.py` |
| R5 | PASS | Citation agent behavior tested in `tests/test_graph_phase1_unittest.py` |
| R6 | PASS | Citation rendering implemented in `static/app.js` and API returns `citations` field |
| R7 | PASS | Local insufficiency fallback remains in generation logic; covered in graph tests |
| R8 | PARTIAL | Web-search MCP path implemented and tested with mocked MCP responses; default `.env` keeps MCP disabled unless configured |

Final Phase 9 acceptance:
- Automated QA: PASS
- Manual demo checklist: READY (guide and scripts updated in `demo/`)
- Remaining caveat: real external web fallback requires live MCP endpoint configuration.

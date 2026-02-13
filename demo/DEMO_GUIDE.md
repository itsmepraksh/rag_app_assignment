# Demo Guide (Phase 8)

## Demo Files

- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_scanned_text_ocr.pdf`

## Scripted Demo Query Flow

1. **Normal retrieval**
- Query: `What are the official work hours in the handbook?`
- Show: concise answer from uploaded docs + citation chips (`filename (Page N)`).

2. **Follow-up memory**
- Query: `Explain section 2 in simple words.`
- Show: follow-up resolved from prior turn context in same session.

3. **Web-search-assisted answer**
- Query: `What are the latest policy news updates today?`
- Show one of:
  - If web MCP enabled: response includes external source URL.
  - If web MCP disabled: explicit web fallback/unavailable message.

4. **Citation output focus**
- Query: `Which features were introduced in product version 2.4?`
- Show citation output for each answer and optionally enable `Debug` to display supporting chunks + trace id.

## Live Demo Steps

1. Open `http://localhost:8000`
2. Upload all three sample files.
3. Run the four scripted queries above in order.
4. Keep same session id to show continuity.
5. Click `Reset` and ask follow-up again to demonstrate memory reset behavior.

## Narration Pointers

- Mention hybrid retrieval + reranking pipeline.
- Mention session-based memory (`recent` + `summary` rollup).
- Mention MCP adapters and local failover behavior.
- Call out `agent_trace_id` and debug panel as observability features.

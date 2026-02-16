# Demo Guide (Plain English)

This demo is designed for non-technical viewers.

## Goal

Show that the system can:
- answer from uploaded documents
- provide citations
- handle follow-up questions
- optionally use live web search

## Demo setup

1. Open app at `http://localhost:8000`
2. Upload:
- `sample_policy_handbook.pdf`
- `sample_product_release_notes.pdf`
- `sample_scanned_text_ocr.pdf`
3. Keep same session during demo

## Demo flow

1. Ask: `What are the official work hours in the handbook?`
- Explain: answer is grounded in uploaded files.

2. Ask: `Explain section 2 in simple words.`
- Explain: this proves memory/follow-up understanding.

3. Ask: `Which features were introduced in product version 2.4?`
- Explain: this proves retrieval from another file.

4. Ask: `What are the latest policy news updates today?`
- Explain: this tests web-search route.
- If Tavily key is set, you should see real web sources.
- If not, you may see local mock source.

5. Ask: `Who won the last FIFA World Cup?`
- Explain: system should avoid pretending unrelated facts are in your docs.

## What to highlight while speaking

- "The answer includes citations, so we can verify source."
- "The app remembers context inside one session."
- "Web search can be switched on with API key."
- "Reset clears memory for fresh conversation."


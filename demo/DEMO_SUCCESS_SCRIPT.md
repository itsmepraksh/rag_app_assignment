# Demo Success Script (Phase 0 Acceptance)

This script is the pass/fail demo run for current baseline behavior.

## Goal

Demonstrate:
- document upload
- grounded Q&A
- follow-up understanding
- citation behavior
- fallback for irrelevant questions
- explicit note on web fallback gap

## Preconditions

- Server running at `http://localhost:8000`
- Ollama running with configured model
- Demo docs available:
  - `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`
  - `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`

## Live Script

1. Open app in browser at `http://localhost:8000`.
2. Upload `sample_policy_handbook.pdf`.
3. Upload `sample_product_release_notes.pdf`.
4. Ask: `What are the official work hours in the handbook?`
5. Ask follow-up: `Explain section 2 in simple words.`
6. Ask: `Which features were introduced in product version 2.4?`
7. Ask unrelated: `Who won the last FIFA World Cup?`

## What To Show For Success

1. Upload success:
- UI should show each uploaded file with chunk count.

2. Follow-up behavior:
- Step 5 should be interpreted as a follow-up to previous context.

3. Citation behavior:
- Backend currently builds citations (`filename + page`) in graph state.
- If citations are not shown in chat UI, call this out as a known Phase 0 gap (tracked in `R6`).

4. Grounded fallback:
- For unrelated FIFA question, answer should indicate insufficient local document information rather than confident outside knowledge.

5. Web fallback status:
- State clearly that automatic web-source fallback is **not implemented** in this baseline (tracked in `R8`).

## Demo Pass/Fail Rule

- Pass the demo if steps run end-to-end and expected behavior appears for upload, follow-up, and grounded fallback.
- Mark "partial pass" if citation UI or web fallback requirement is missing; reference `assignment_checklist.md`.

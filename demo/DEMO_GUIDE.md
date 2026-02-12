# Demo Guide (Phase 6)

## Sample PDFs

- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_policy_handbook.pdf`
- `/Users/prakashsamanta/workSpace/assignment1/demo/sample_product_release_notes.pdf`

## 5 Example Questions

1. What are the official work hours in the handbook?
2. How many paid annual leave days and sick leave days are allowed?
3. What security controls are mandatory for accounts?
4. Which features were introduced in product version 2.4?
5. What is the known mobile issue and workaround in the release notes?

## Follow-up Question Example

- Follow-up: "Explain section 2 in simple words."
- Why this works: the system uses the recent conversation turns to resolve "section 2" from prior context.

## Irrelevant Question Example

- "Who won the last FIFA World Cup?"
- Expected behavior: system should avoid outside knowledge and say it does not have enough information in uploaded docs.

## Practice Demo Flow

1. Open app: `http://localhost:8000`
2. Upload both PDFs from `demo/`.
3. Ask one factual question (for example Question 1).
4. Ask the follow-up question: "Explain section 2 in simple words."
5. Point out citations in response (`filename` + `Page`).
6. Ask unrelated question (FIFA example) and show grounded fallback behavior.

## Demo Tips

- Keep answers short and ask one question at a time.
- Highlight the citation block after each answer.
- Mention that follow-up works using conversation memory (last 3 turns).

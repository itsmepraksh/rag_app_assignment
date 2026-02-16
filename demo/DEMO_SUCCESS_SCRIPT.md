# Demo Success Script

Use this script for a quick pass/fail demonstration.

## Preconditions

- App running at `http://localhost:8000`
- MCP server running
- Demo files available in `/demo`

## Run steps

1. Upload `sample_policy_handbook.pdf`
2. Upload `sample_product_release_notes.pdf`
3. Ask: `What are the official work hours in the handbook?`
4. Ask: `Explain section 2 in simple words.`
5. Ask: `Which features were introduced in product version 2.4?`
6. Ask: `What are the latest policy news updates today?`
7. Ask: `Who won the last FIFA World Cup?`

## Pass conditions

- Upload succeeds and shows chunk counts.
- Answers are relevant to uploaded files.
- Citation chips are visible for document-grounded answers.
- Follow-up question uses session context.
- Web query returns either:
  - real web links (if Tavily key configured), or
  - clear local fallback result.
- Out-of-scope question does not produce a misleading "document-based" claim.


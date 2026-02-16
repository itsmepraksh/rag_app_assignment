# Example Demo Queries

Use these queries in order for a clean demo.

## Step 0: Upload demo files

Upload these files first:
- `sample_policy_handbook.pdf`
- `sample_product_release_notes.pdf`
- `sample_scanned_text_ocr.pdf`

## Step 1: Basic document Q&A

Query:
`What are the official work hours in the handbook?`

Expected:
- A direct answer from the handbook
- Citation chips with file/page info

## Step 2: Follow-up memory

Query:
`Explain section 2 in simple words.`

Expected:
- Follow-up answer that uses earlier context in same session

## Step 3: Product details retrieval

Query:
`Which features were introduced in product version 2.4?`

Expected:
- Answer from release notes
- Correct citations

## Step 4: Web-search path test

Query:
`What are the latest policy news updates today?`

Expected:
- If Tavily is configured: real web results
- If not configured: local mock/fallback result

## Step 5: Out-of-scope question

Query:
`Who won the last FIFA World Cup?`

Expected:
- System should avoid confident hallucination from unrelated docs


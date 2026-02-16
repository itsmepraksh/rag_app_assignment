# Non-Technical User Guide

This guide is for people who just want to use the app.

## What this app does

- You upload documents.
- You ask questions in normal English.
- The app answers using your documents.
- It also shows citations so you can check where the answer came from.

## Before you start

A technical person should start two services for you:
1. The MCP server
2. The main app server

Once running, open:
- `http://localhost:8000`

## Step-by-step usage

1. Upload a file
- On the left side, click or drag a `.pdf`, `.txt`, or `.md` file.
- Wait until status says the system is ready.

2. Ask a question
- Type your question in the input box.
- Click `Send`.

3. Read the answer
- The app shows answer text.
- Citation chips appear below the answer (example: `sample_policy_handbook.pdf (Page 2)`).

4. Ask follow-up questions
- You can ask things like: `Explain section 2 in simple words.`
- Keep the same session to preserve context.

5. Reset when needed
- Click `Reset` to clear session memory.
- Useful when you want a fresh conversation.

## Good questions to ask

- `What are the official work hours in the handbook?`
- `Which features were introduced in product version 2.4?`
- `Summarize the leave policy in simple terms.`

## Understanding web-search behavior

- If web search is configured correctly, you may see real web sources.
- If not configured, you may see local mock source links.
- This is normal and depends on system setup.

## Common issues (simple)

- I get no answer:
  - Check if document upload succeeded.

- I get a server error:
  - Ask the operator to restart both services.

- I see fake-looking source like `local-mcp.invalid`:
  - Web API key may be missing.


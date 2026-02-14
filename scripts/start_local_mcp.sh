#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PY_BIN="${PY_BIN:-python3}"
PORT="${MCP_LOCAL_PORT:-9100}"

echo "Starting local MCP server on port ${PORT}..."
exec "$PY_BIN" -m uvicorn mcp_servers.local_mcp_server:app --host 127.0.0.1 --port "${PORT}" --reload

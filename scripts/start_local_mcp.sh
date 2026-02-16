#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "./venv/bin/python" ]]; then
  DEFAULT_PY_BIN="./venv/bin/python"
else
  DEFAULT_PY_BIN="python3"
fi

PY_BIN="${PY_BIN:-$DEFAULT_PY_BIN}"
PORT="${MCP_LOCAL_PORT:-9100}"
RELOAD="${MCP_LOCAL_RELOAD:-false}"

echo "Starting local MCP server on port ${PORT}..."
if [[ "$RELOAD" == "true" ]]; then
  exec "$PY_BIN" -m uvicorn mcp_servers.local_mcp_server:app --host 127.0.0.1 --port "${PORT}" --reload
else
  exec "$PY_BIN" -m uvicorn mcp_servers.local_mcp_server:app --host 127.0.0.1 --port "${PORT}"
fi

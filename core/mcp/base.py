import json
import logging
import os
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args, **_kwargs):
        return False

logger = logging.getLogger(__name__)

load_dotenv()

MCP_ENABLED = os.getenv("MCP_ENABLED", "false").strip().lower() == "true"
MCP_TIMEOUT_SECONDS = int(os.getenv("MCP_TIMEOUT_SECONDS", "8"))
MCP_FAILOVER_LOCAL = os.getenv("MCP_FAILOVER_LOCAL", "true").strip().lower() == "true"


def post_json(url: str, payload: dict[str, Any], timeout: int | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t = timeout if timeout is not None else MCP_TIMEOUT_SECONDS
    try:
        with urlopen(req, timeout=t) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raise RuntimeError(f"MCP HTTP error: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"MCP URL error: {exc.reason}") from exc

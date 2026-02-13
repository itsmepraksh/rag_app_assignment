import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from dotenv import load_dotenv
from ollama import Client as OllamaClient

load_dotenv()
logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
_default_model = "llama3:8b"
LLM_MODEL = os.getenv("LLM_MODEL", _default_model).strip()
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip()


def _generate_with_ollama(prompt: str) -> str:
    client = OllamaClient(host=OLLAMA_HOST, timeout=LLM_TIMEOUT_SECONDS)
    result = client.generate(
        model=LLM_MODEL,
        prompt=prompt,
        options={"temperature": 0.2},
    )
    text = result.get("response", "")
    if not text:
        raise RuntimeError("Ollama returned an empty response.")
    return text


def _generate_with_dummy(prompt: str) -> str:
    _ = prompt
    return (
        "Temporary LLM client is active. Set LLM_PROVIDER=ollama to enable local model generation."
    )


def generate(prompt: str) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")

    def _run() -> str:
        if LLM_PROVIDER == "ollama":
            return _generate_with_ollama(prompt)
        if LLM_PROVIDER == "dummy":
            return _generate_with_dummy(prompt)
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    try:
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run)
            response = future.result(timeout=LLM_TIMEOUT_SECONDS)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "llm_inference provider=%s model=%s latency_ms=%.2f",
            LLM_PROVIDER,
            LLM_MODEL,
            elapsed_ms,
        )
        return response
    except FutureTimeoutError as exc:
        raise TimeoutError(
            f"LLM generation timed out after {LLM_TIMEOUT_SECONDS} seconds."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {exc}") from exc


def prewarm_model() -> None:
    if LLM_PROVIDER != "ollama":
        logger.info("llm_prewarm skipped provider=%s", LLM_PROVIDER)
        return

    try:
        start = time.perf_counter()
        client = OllamaClient(host=OLLAMA_HOST, timeout=LLM_TIMEOUT_SECONDS)
        client.generate(
            model=LLM_MODEL,
            prompt="Warm up.",
            options={"temperature": 0, "num_predict": 1},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("llm_prewarm success model=%s latency_ms=%.2f", LLM_MODEL, elapsed_ms)
    except Exception as exc:
        logger.warning("llm_prewarm failed model=%s error=%s", LLM_MODEL, exc)

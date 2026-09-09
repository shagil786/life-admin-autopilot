"""Gateway-backed completion LLM for the LLMExtractor.

Uses the same LIFE_ADMIN_* env config as the agent layer. Falls back to
None when no gateway is configured (extraction stays regex-only).
"""
import os
from typing import Optional

from src.extraction.llm_extractor import CompletionLLM


class GatewayLLM:
    """Minimal complete(prompt) -> str adapter over an OpenAI-compatible API."""

    def __init__(self, base_url: str, api_key: str, model_id: str):
        self._client_kwargs = {"base_url": base_url, "api_key": api_key}
        self._model_id = model_id

    def complete(self, prompt: str) -> str:
        """Complete a prompt, retrying once on empty/error responses."""
        from openai import OpenAI

        client = OpenAI(**self._client_kwargs)
        last_error = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=self._model_id,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                )
                text = resp.choices[0].message.content or ""
                if text.strip():
                    return text
                last_error = ValueError("empty completion")
            except Exception as e:
                last_error = e
        if last_error:
            raise last_error
        return ""


def build_gateway_llm() -> Optional[CompletionLLM]:
    """Return a GatewayLLM if env config exists, else None."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    base_url = os.environ.get("LIFE_ADMIN_BASE_URL")
    api_key = os.environ.get("LIFE_ADMIN_API_KEY")
    model_id = os.environ.get("LIFE_ADMIN_MODEL", "free/deepseek-v4-flash-0731")
    if not (base_url and api_key):
        return None
    return GatewayLLM(base_url=base_url, api_key=api_key, model_id=model_id)

"""Cheaper-alternative finder.

Two modes:
1. Offline/LLM mode (default): build an LLM-backed search_fn from an
   OpenAI-compatible gateway using structured output.
2. Injected search_fn: any callable (product, max_price) -> list of dicts,
   used by tests and future Exa/web-search integrations.
"""
import json
from typing import Callable, Optional

SearchFn = Callable[[str, float], list]


class AlternativeFinder:
    def __init__(self, search_fn: Optional[SearchFn] = None):
        self._search_fn = search_fn

    def find(self, product: str, max_price: float) -> list:
        """Find cheaper alternatives to `product`, each <= max_price.

        Returns list of {name, price, why} sorted by price ascending.
        """
        if not self._search_fn or not product or max_price is None:
            return []
        raw = self._search_fn(product, max_price) or []
        cleaned = [
            {
                "name": a.get("name", ""),
                "price": float(a.get("price", 0)),
                "why": a.get("why", ""),
            }
            for a in raw
            if a.get("name") and a.get("price") is not None
        ]
        under_budget = [a for a in cleaned if a["price"] <= max_price]
        return sorted(under_budget, key=lambda a: a["price"])


def format_alternatives(product: str, alternatives: list) -> str:
    """Render alternatives for CLI/agent display."""
    if not alternatives:
        return f"No cheaper alternatives found for {product} (within budget)."
    lines = [f"Cheaper alternatives to {product}:"]
    for a in alternatives:
        lines.append(f"  - {a['name']} — ${a['price']:.2f} ({a['why']})")
    return "\n".join(lines)


def build_llm_search_fn() -> Optional[SearchFn]:
    """Build a search_fn backed by the configured LLM gateway.

    Returns None if no gateway is configured (graceful degradation).
    """
    import os
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

    def llm_search(product: str, max_price: float) -> list:
        from openai import OpenAI

        client = OpenAI(base_url=base_url, api_key=api_key)
        prompt = (
            f"List 3-5 well-known products that are cheaper alternatives to "
            f"'{product}' with price under ${max_price:.2f}. "
            "Reply with ONLY a JSON array like "
            '[{"name": "...", "price": 79.99, "why": "short reason"}]. '
            "Prices must be realistic street prices in USD."
        )
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            text = resp.choices[0].message.content.strip()
            return _extract_json_array(text)
        except Exception:
            return []

    return llm_search


def _extract_json_array(text: str) -> list:
    """Pull the first JSON array out of an LLM response, tolerating
    markdown fences and stray prose around it."""
    # strip code fences
    if "```" in text:
        for block in text.split("```"):
            candidate = block.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("["):
                text = candidate
                break
    # fall back to bracket span
    if not text.startswith("["):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            text = text[start:end + 1]
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []

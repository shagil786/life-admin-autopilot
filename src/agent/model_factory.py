"""Builds a Strands Agent wired to an OpenAI-compatible endpoint.

Config via environment (or .env):
  LIFE_ADMIN_BASE_URL   - e.g. https://api.apinex.bond/v1  (default)
  LIFE_ADMIN_API_KEY    - gateway key
  LIFE_ADMIN_MODEL      - model id, e.g. deepseek/v4-flash

Gateways we support out of the box: APInex, Token Harbor, Kira AI —
any OpenAI chat-completions-compatible base URL works.
"""
import os

from strands import Agent
from strands.models.openai import OpenAIModel

DEFAULT_BASE_URL = "https://api.apinex.bond/v1"
DEFAULT_MODEL = "free/deepseek-v4-flash-0731"


def _env(name: str, default: str = "") -> str:
    # .env support without hard dependency ordering
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.environ.get(name, default)


def build_agent(system_prompt: str, tools: list) -> Agent:
    """Create a Strands Agent backed by an OpenAI-compatible gateway."""
    base_url = _env("LIFE_ADMIN_BASE_URL", DEFAULT_BASE_URL)
    api_key = _env("LIFE_ADMIN_API_KEY")
    model_id = _env("LIFE_ADMIN_MODEL", DEFAULT_MODEL)

    model = OpenAIModel(
        client_args={"base_url": base_url, "api_key": api_key},
        model_id=model_id,
        params={"max_tokens": 2048},
    )
    return Agent(model=model, tools=tools, system_prompt=system_prompt)

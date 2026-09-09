"""Configuration module for Life Admin Autopilot."""
from dataclasses import dataclass
from pathlib import Path
import tomllib

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.toml"


@dataclass
class AppConfig:
    model_name: str = "claude-3-5-sonnet-20241022"
    max_retries: int = 3
    local_processing: bool = True
    storage_path: str = "./data"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load app config from a TOML file, falling back to defaults."""
    if not path.exists():
        return AppConfig()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return AppConfig(**data.get("app", {}))


def get_model_settings() -> dict:
    """Return model settings dict for LLM clients."""
    config = load_config()
    return {"model": config.model_name, "max_retries": config.max_retries}

"""Tests for configuration module."""
import pytest
from src.config import load_config, get_model_settings


def test_load_config_defaults():
    config = load_config()
    assert config.model_name == "claude-3-5-sonnet-20241022"
    assert config.max_retries == 3
    assert config.local_processing is True
    assert config.storage_path == "./data"


def test_load_config_from_custom_path(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[app]\nmodel_name = "test-model"\nmax_retries = 5\n'
        'local_processing = false\nstorage_path = "/tmp/x"\n'
    )
    config = load_config(config_file)
    assert config.model_name == "test-model"
    assert config.max_retries == 5
    assert config.local_processing is False


def test_get_model_settings():
    settings = get_model_settings()
    assert settings["model"] == "claude-3-5-sonnet-20241022"
    assert settings["max_retries"] == 3

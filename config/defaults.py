"""Load and manage default configuration from defaults.yaml"""

import os
import yaml

_defaults_cache = {}


def get_defaults() -> dict:
    """Load defaults.yaml and return merged config dict"""
    if _defaults_cache:
        return _defaults_cache

    config_path = os.path.join(os.path.dirname(__file__), "defaults.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            _defaults_cache.update(yaml.safe_load(f) or {})
    return _defaults_cache


def update_defaults(updates: dict) -> None:
    """Update defaults at runtime (for hot-reload from Web UI)"""
    _defaults_cache.update(updates)

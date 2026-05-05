"""Load and manage default configuration from defaults.json"""

import json
import os

_defaults_path = os.path.join(os.path.dirname(__file__), "defaults.json")
_defaults_cache = {}


def get_defaults() -> dict:
    """Load defaults.json and return merged config dict."""
    if _defaults_cache:
        return _defaults_cache

    if os.path.exists(_defaults_path):
        with open(_defaults_path, "r", encoding="utf-8") as f:
            _defaults_cache.update(json.load(f))
    return _defaults_cache


def update_defaults(updates: dict) -> None:
    """Update defaults at runtime and persist to defaults.json."""
    _defaults_cache.update(updates)
    with open(_defaults_path, "w", encoding="utf-8") as f:
        json.dump(_defaults_cache, f, indent=2, ensure_ascii=False)

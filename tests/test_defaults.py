"""Tests for config.defaults — JSON persistence."""

import json
import os
import shutil

import pytest

from config.defaults import get_defaults, update_defaults, _defaults_cache


@pytest.fixture(autouse=True)
def isolate_defaults(tmp_path, monkeypatch):
    """Redirect defaults.json to a temp file so tests don't mutate the real one."""
    temp_file = tmp_path / "defaults.json"
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "..", "config", "defaults.json"),
        temp_file,
    )
    monkeypatch.setattr("config.defaults._defaults_cache", {})
    monkeypatch.setattr(
        "config.defaults._defaults_path",
        str(temp_file),
    )
    yield temp_file
    _defaults_cache.clear()


def test_update_defaults_persists_to_json(isolate_defaults):
    """update_defaults must write changes to defaults.json."""
    get_defaults()  # loads cache from temp file
    new_wechat = {
        "wechat": {
            "taskbar_region": [432, 1037, 56, 42],
            "chat_list_region": [1022, 83, 238, 951],
        }
    }

    update_defaults(new_wechat)

    # In-memory cache
    assert get_defaults()["wechat"]["taskbar_region"] == [432, 1037, 56, 42]

    # On-disk file
    with open(isolate_defaults, "r", encoding="utf-8") as f:
        persisted = json.load(f)
    assert persisted["wechat"]["taskbar_region"] == [432, 1037, 56, 42]
    assert persisted["wechat"]["chat_list_region"] == [1022, 83, 238, 951]


def test_update_defaults_preserves_other_sections(isolate_defaults):
    """Updating wechat should not remove other top-level keys."""
    get_defaults()
    update_defaults({"wechat": {"taskbar_region": [1, 2, 3, 4]}})

    with open(isolate_defaults, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "humanize" in data
    assert "vision" in data
    assert "polling" in data
    assert "agent" in data
    assert data["humanize"]["bezier"]["num_points"] == 20


def test_defaults_json_is_valid_json(isolate_defaults):
    """The persisted file must be parseable JSON."""
    get_defaults()
    update_defaults({"wechat": {"taskbar_region": [0, 0, 1, 1]}})

    with open(isolate_defaults, "r", encoding="utf-8") as f:
        raw = f.read()
    json.loads(raw)  # should not raise


def test_get_defaults_is_idempotent(isolate_defaults):
    """Calling get_defaults multiple times returns the cached result."""
    first = get_defaults()
    second = get_defaults()
    assert first is second

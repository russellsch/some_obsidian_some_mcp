"""Unit tests for override file loader."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from some_vault_some_mcp.config import ToolOverride, apply_override, load_overrides


def _write_override_file(data: dict) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(data, f)
        return f.name


def test_empty_file_returns_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    overrides, disabled = load_overrides(path)
    assert overrides == {}
    assert disabled == set()


def test_missing_file_returns_empty():
    overrides, disabled = load_overrides("/tmp/does_not_exist_abc123.yaml")
    assert overrides == {}
    assert disabled == set()


def test_no_path_returns_empty(monkeypatch):
    monkeypatch.delenv("some_vault_some_mcp_OVERRIDES", raising=False)
    overrides, disabled = load_overrides(None)
    assert overrides == {}
    assert disabled == set()


def test_full_override():
    data = {
        "tools": {
            "get_note": {"name": "recall", "description": "Custom desc"},
            "list_notes": {"name": "scan"},
        },
        "disabled": ["vault_reindex"],
    }
    path = _write_override_file(data)
    overrides, disabled = load_overrides(path)
    assert overrides["get_note"].name == "recall"
    assert overrides["get_note"].description == "Custom desc"
    assert overrides["list_notes"].name == "scan"
    assert overrides["list_notes"].description is None
    assert "vault_reindex" in disabled


def test_partial_override():
    data = {"tools": {"search": {"name": "find"}}}
    path = _write_override_file(data)
    overrides, disabled = load_overrides(path)
    assert overrides["search"].name == "find"
    assert overrides["search"].description is None


def test_apply_override_full():
    overrides = {"get_note": ToolOverride(name="recall", description="Custom")}
    name, desc = apply_override("get_note", "Default desc", overrides)
    assert name == "recall"
    assert desc == "Custom"


def test_apply_override_name_only():
    overrides = {"get_note": ToolOverride(name="recall")}
    name, desc = apply_override("get_note", "Default desc", overrides)
    assert name == "recall"
    assert desc == "Default desc"


def test_apply_override_no_match():
    name, desc = apply_override("search", "Default", {})
    assert name == "search"
    assert desc == "Default"


def test_disabled_empty_list():
    data = {"tools": {}, "disabled": []}
    path = _write_override_file(data)
    _, disabled = load_overrides(path)
    assert disabled == set()


def test_malformed_yaml_returns_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: {unclosed")
        path = f.name
    overrides, disabled = load_overrides(path)
    assert overrides == {}
    assert disabled == set()

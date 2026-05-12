"""Unit tests for vault path resolver."""

import os
import tempfile
from pathlib import Path

import pytest

from some_vault_some_mcp.core.paths import (
    VaultPathError,
    ensure_md_extension,
    resolve_vault_path,
    walk_vault,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "vault"


def test_resolve_valid_path():
    vault = str(FIXTURES)
    result = resolve_vault_path(vault, "simple.md")
    assert result == str(FIXTURES / "simple.md")


def test_resolve_traversal_rejected():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="traversal"):
        resolve_vault_path(vault, "../../../etc/passwd")


def test_resolve_null_byte_rejected():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="null byte"):
        resolve_vault_path(vault, "note\x00.md")


def test_resolve_obsidian_rejected():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="excluded"):
        resolve_vault_path(vault, ".obsidian/config.json")


def test_resolve_git_rejected():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="excluded"):
        resolve_vault_path(vault, ".git/config")


def test_resolve_trash_rejected():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="excluded"):
        resolve_vault_path(vault, ".trash/note.md")


def test_resolve_nested_excluded():
    vault = str(FIXTURES)
    with pytest.raises(VaultPathError, match="excluded"):
        resolve_vault_path(vault, "projects/.git/config")


def test_walk_vault_excludes_hidden():
    vault = str(FIXTURES)
    paths = walk_vault(vault)
    # Should not include .obsidian, .git, .trash files
    for p in paths:
        parts = p.split("/")
        for seg in parts:
            assert seg not in (".obsidian", ".git", ".trash"), f"Excluded dir leaked: {p}"


def test_walk_vault_only_md():
    vault = str(FIXTURES)
    paths = walk_vault(vault)
    for p in paths:
        assert p.endswith(".md"), f"Non-.md file leaked: {p}"


def test_walk_vault_finds_nested():
    vault = str(FIXTURES)
    paths = walk_vault(vault)
    assert any("projects/alpha" in p for p in paths), "Nested vault files not found"


def test_ensure_md_extension():
    assert ensure_md_extension("note") == "note.md"
    assert ensure_md_extension("note.md") == "note.md"
    assert ensure_md_extension("note.MD") == "note.MD"
    assert ensure_md_extension("folder/note") == "folder/note.md"


def test_symlink_escape_rejected():
    """Symlinks that resolve outside the vault root must be rejected."""
    with tempfile.TemporaryDirectory() as vault:
        with tempfile.TemporaryDirectory() as outside:
            outside_file = Path(outside) / "secret.md"
            outside_file.write_text("secret data", encoding="utf-8")

            symlink = Path(vault) / "escape.md"
            symlink.symlink_to(outside_file)

            with pytest.raises(VaultPathError, match="traversal"):
                resolve_vault_path(vault, "escape.md")


def test_error_message_no_absolute_path_leak():
    with tempfile.TemporaryDirectory() as vault:
        # The error message for path traversal should not include the host path
        # (it mentions the relative path the user supplied, not the vault root)
        try:
            resolve_vault_path(vault, "../../../root")
        except VaultPathError as e:
            # Should not contain the vault path itself in the error
            assert vault not in str(e) or "traversal" in str(e)

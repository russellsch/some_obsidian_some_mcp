"""Integration tests for list_notes with index-backed metadata filters.

Uses MockProvider (no Ollama needed). Indexes the fixture vault, then queries
list_notes with tag/project/status/area filters against LanceDB.
"""

from pathlib import Path

import pytest

from some_vault_some_mcp.core.embeddings import MockProvider
from some_vault_some_mcp.core.indexer import full_index
from some_vault_some_mcp.tools.read import list_notes

FIXTURES = Path(__file__).parent.parent / "fixtures" / "vault"


@pytest.fixture()
def indexed_vault(tmp_path):
    """Index the fixture vault and return (vault_path, db_path)."""
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    full_index(str(FIXTURES), db_path, provider)
    return str(FIXTURES), db_path


def test_list_notes_filter_by_tag(indexed_vault):
    """Filter by tags=['reference'] returns only notes tagged 'reference'."""
    vault_path, db_path = indexed_vault
    results, total = list_notes(vault_path, db_path=db_path, tags=["reference"])
    assert total > 0, "Expected at least one note with tag 'reference'"
    paths = [r.file_path for r in results]
    # simple.md and linked-note.md both have tags: [reference]
    assert "simple.md" in paths
    assert "linked-note.md" in paths


def test_list_notes_filter_by_project(indexed_vault):
    """Filter by projects=['testproject'] returns matching notes."""
    vault_path, db_path = indexed_vault
    results, total = list_notes(vault_path, db_path=db_path, projects=["testproject"])
    assert total > 0
    paths = [r.file_path for r in results]
    # simple.md and projects/alpha/deep-note.md have projects: [testproject]
    assert "simple.md" in paths


def test_list_notes_filter_by_status(indexed_vault):
    """Filter by status='draft' returns notes with that status."""
    vault_path, db_path = indexed_vault
    results, total = list_notes(vault_path, db_path=db_path, status="draft")
    assert total > 0
    paths = [r.file_path for r in results]
    # projects/alpha/deep-note.md has status: draft
    assert "projects/alpha/deep-note.md" in paths


def test_list_notes_filter_by_area(indexed_vault):
    """Filter by area='Testing' returns notes in that area."""
    vault_path, db_path = indexed_vault
    results, total = list_notes(vault_path, db_path=db_path, area="Testing")
    assert total > 0
    paths = [r.file_path for r in results]
    # simple.md has area: Testing
    assert "simple.md" in paths


def test_list_notes_filter_no_match(indexed_vault):
    """Filter with non-existent tag returns empty results."""
    vault_path, db_path = indexed_vault
    results, total = list_notes(vault_path, db_path=db_path, tags=["nonexistent-tag-xyz"])
    assert total == 0
    assert results == []

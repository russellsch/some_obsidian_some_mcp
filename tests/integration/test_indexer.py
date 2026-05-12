"""Integration tests for indexer — require mock provider (no Ollama needed).

Provider-switch tests use mock-768 and mock-3072 — no Ollama.
Full Ollama tests would use @pytest.mark.integration and pytest.skip if unavailable.
"""

import json
from pathlib import Path

import pytest

from some_vault_some_mcp.core.embeddings import MockProvider, Mock3072Provider
from some_vault_some_mcp.core.indexer import (
    _check_dimension_mismatch,
    _get_db,
    _get_table,
    full_index,
    incremental_index,
    TABLE_NAME,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "vault"
SCHEMA_FIXTURE = Path(__file__).parent.parent / "fixtures" / "lancedb_schema.json"


def test_full_index_creates_table(tmp_path):
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    result = full_index(str(FIXTURES), db_path, provider)
    assert result["chunks_created"] > 0
    assert result["files_indexed"] > 0


def test_schema_parity_with_fixture(tmp_path):
    """Check that indexed table schema matches the captured schema fixture."""
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    full_index(str(FIXTURES), db_path, provider)

    db = _get_db(db_path)
    table = _get_table(db)
    assert table is not None

    schema_data = json.loads(SCHEMA_FIXTURE.read_text())
    expected_cols = {col["name"] for col in schema_data["columns"]}
    actual_cols = {field.name for field in table.schema}
    assert expected_cols == actual_cols


def test_vector_dimensions(tmp_path):
    """Indexed vectors should have 768 dims (MockProvider)."""
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    full_index(str(FIXTURES), db_path, provider)
    db = _get_db(db_path)
    table = _get_table(db)
    schema = table.schema
    vector_field = next(f for f in schema if f.name == "vector")
    assert vector_field.type.list_size == 768


def test_excluded_dirs_not_indexed(tmp_path):
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    full_index(str(FIXTURES), db_path, provider)
    db = _get_db(db_path)
    table = _get_table(db)
    df = table.to_pandas()
    paths = df["file_path"].tolist()
    for p in paths:
        parts = p.split("/")
        for seg in parts:
            assert seg not in (".obsidian", ".git", ".trash"), f"Excluded path leaked: {p}"


def test_incremental_index_detects_changes(tmp_path):
    import shutil
    vault = tmp_path / "vault"
    shutil.copytree(str(FIXTURES), str(vault), ignore=shutil.ignore_patterns(".git", ".trash", ".obsidian"))

    db_path = str(tmp_path / "db.lance")
    provider = MockProvider()
    full_index(str(vault), db_path, provider)

    # Add a new file
    new_note = vault / "new_note.md"
    new_note.write_text("---\ntitle: New Note\n---\n\nBrand new content.", encoding="utf-8")

    result = incremental_index(str(vault), db_path, provider)
    assert result["files_indexed"] >= 1
    assert result["chunks_created"] >= 1


def test_incremental_index_handles_deletion(tmp_path):
    import shutil
    vault = tmp_path / "vault"
    shutil.copytree(str(FIXTURES), str(vault), ignore=shutil.ignore_patterns(".git", ".trash", ".obsidian"))

    db_path = str(tmp_path / "db.lance")
    provider = MockProvider()
    full_index(str(vault), db_path, provider)

    # Delete a file
    (vault / "no-frontmatter.md").unlink()
    result = incremental_index(str(vault), db_path, provider)
    assert result["files_removed"] >= 1


def test_single_file_reindex(tmp_path):
    """Single-file reindex only affects that file (upstream bug fixed)."""
    import shutil
    vault = tmp_path / "vault"
    shutil.copytree(str(FIXTURES), str(vault), ignore=shutil.ignore_patterns(".git", ".trash", ".obsidian"))

    db_path = str(tmp_path / "db.lance")
    provider = MockProvider()
    full_index(str(vault), db_path, provider)

    # Modify one file
    target = vault / "simple.md"
    content = target.read_text(encoding="utf-8")
    target.write_text(content + "\n\nAdded paragraph.", encoding="utf-8")
    import os; os.utime(str(target), None)  # update mtime

    result = incremental_index(str(vault), db_path, provider, single_file="simple.md")
    # Only the one modified file should be reindexed
    assert result["files_indexed"] == 1


def test_provider_switch_mismatch_refuses(tmp_path):
    """Index with 768-dim, switch to 3072-dim — boot must refuse."""
    db_path = str(tmp_path / "vault.lance")
    provider768 = MockProvider()
    full_index(str(FIXTURES), db_path, provider768)

    db = _get_db(db_path)
    provider3072 = Mock3072Provider()
    with pytest.raises(RuntimeError) as exc_info:
        _check_dimension_mismatch(db, provider3072.dimensions)
    assert "3072" in str(exc_info.value)
    assert "768" in str(exc_info.value)


def test_provider_restart_same_dims_ok(tmp_path):
    """Same provider dimensions on restart — boot succeeds, index reused."""
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    result1 = full_index(str(FIXTURES), db_path, provider)

    db = _get_db(db_path)
    _check_dimension_mismatch(db, provider.dimensions)  # should not raise

    table = _get_table(db)
    assert table.count_rows() == result1["chunks_created"]


def test_tags_stored_as_comma_string(tmp_path):
    """tags/projects columns must be comma-separated strings (not Arrow lists)."""
    import pandas as pd
    db_path = str(tmp_path / "vault.lance")
    provider = MockProvider()
    full_index(str(FIXTURES), db_path, provider)
    db = _get_db(db_path)
    table = _get_table(db)
    df = table.to_pandas()
    # tags column should be string type (object in pandas <3, str in pandas 3+), not list
    assert pd.api.types.is_string_dtype(df["tags"]), f"Expected string dtype, got {df['tags'].dtype}"
    # Values should be strings, not lists
    non_empty = df[df["tags"] != ""]["tags"]
    if not non_empty.empty:
        sample = non_empty.iloc[0]
        assert isinstance(sample, str)

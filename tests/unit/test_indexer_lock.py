"""Test that concurrent incremental_index calls don't produce duplicate chunks."""

import threading
from pathlib import Path

import pytest

from some_vault_some_mcp.core.embeddings import MockProvider
from some_vault_some_mcp.core.indexer import full_index, incremental_index, _get_db, _get_table, TABLE_NAME

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "vault"


@pytest.mark.integration
def test_concurrent_reindex_no_duplicates(tmp_path):
    """Two threads calling incremental_index for the same file produce no duplicates."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    note = vault_dir / "note.md"
    note.write_text("# Test\n\nSome content here.", encoding="utf-8")

    db_path = str(tmp_path / "db.lance")
    provider = MockProvider()

    result = full_index(str(vault_dir), db_path, provider)
    assert result["chunks_created"] > 0

    # Touch the file to trigger re-embed
    note.write_text("# Test\n\nUpdated content here.", encoding="utf-8")

    errors = []

    def reindex():
        try:
            incremental_index(str(vault_dir), db_path, provider, single_file="note.md")
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=reindex)
    t2 = threading.Thread(target=reindex)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Reindex raised: {errors}"

    db = _get_db(db_path)
    table = _get_table(db)
    import pandas as pd
    df = table.to_pandas()
    note_chunks = df[df["file_path"] == "note.md"]
    unique_chunks = note_chunks.drop_duplicates(subset=["content"])
    assert len(note_chunks) == len(unique_chunks), (
        f"Found {len(note_chunks)} chunks but only {len(unique_chunks)} unique — duplicates exist"
    )

"""Unit tests for exact_search folder filtering."""

from some_vault_some_mcp.tools.search import exact_search


def test_exact_search_folder_no_prefix_collision(tmp_path):
    """folder='notes' must not match files in 'notes-archive/'."""
    vault = tmp_path / "vault"
    (vault / "notes").mkdir(parents=True)
    (vault / "notes-archive").mkdir(parents=True)
    (vault / "notes" / "a.md").write_text("hello world", encoding="utf-8")
    (vault / "notes-archive" / "b.md").write_text("hello world", encoding="utf-8")

    results = exact_search("hello", str(vault), folder="notes")
    paths = [r.relative_path for r in results]
    assert "notes/a.md" in paths
    assert "notes-archive/b.md" not in paths

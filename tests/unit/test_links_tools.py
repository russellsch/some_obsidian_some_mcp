"""Unit tests for link/graph tools: backlinks, outlinks, orphans, broken, neighbors."""

import shutil
from pathlib import Path

import pytest

from some_vault_some_mcp.tools.links import (
    find_broken_links,
    find_orphans,
    get_backlinks,
    get_graph_neighbors,
    get_outlinks,
)


FIXTURES = Path(__file__).parent.parent / "fixtures" / "vault"


@pytest.fixture()
def vault(tmp_path):
    """Temporary vault copy for link tests."""
    vault_dir = tmp_path / "vault"
    shutil.copytree(
        str(FIXTURES),
        str(vault_dir),
        ignore=shutil.ignore_patterns(".git", ".trash", ".obsidian"),
    )
    (vault_dir / ".trash").mkdir(exist_ok=True)
    return str(vault_dir)


@pytest.fixture()
def linked_vault(tmp_path):
    """Custom vault with a controlled, known link graph for precise assertions."""
    vault_dir = tmp_path / "linked"
    vault_dir.mkdir()

    # a.md links to b.md and c.md
    (vault_dir / "a.md").write_text(
        "---\ntitle: A\n---\n\nLinks to [[b]] and [[c]].", encoding="utf-8"
    )
    # b.md links back to a.md
    (vault_dir / "b.md").write_text(
        "---\ntitle: B\n---\n\nLinks back to [[a]].", encoding="utf-8"
    )
    # c.md links to a broken target
    (vault_dir / "c.md").write_text(
        "---\ntitle: C\n---\n\nBroken link to [[phantom]].", encoding="utf-8"
    )
    # d.md is completely isolated (no in or outlinks)
    (vault_dir / "d.md").write_text(
        "---\ntitle: D\n---\n\nNo links at all.", encoding="utf-8"
    )

    return str(vault_dir)


# --- get_backlinks ---

def test_get_backlinks_finds_referencing_notes(linked_vault):
    """get_backlinks returns notes that link to the given note."""
    backlinks = get_backlinks(linked_vault, "b")
    sources = [bl["source"] for bl in backlinks]
    assert "a.md" in sources


def test_get_backlinks_no_backlinks(linked_vault):
    """d.md has no backlinks — should return empty list."""
    backlinks = get_backlinks(linked_vault, "d")
    assert backlinks == []


def test_get_backlinks_includes_line_and_context(linked_vault):
    """Each backlink entry has source, line, and context fields."""
    backlinks = get_backlinks(linked_vault, "b")
    assert len(backlinks) > 0
    entry = backlinks[0]
    assert "source" in entry
    assert "line" in entry
    assert "context" in entry
    assert isinstance(entry["line"], int)


def test_get_backlinks_fixture_vault(vault):
    """simple.md is linked from linked-note.md in the fixture vault."""
    backlinks = get_backlinks(vault, "simple")
    sources = [bl["source"] for bl in backlinks]
    assert "linked-note.md" in sources


# --- get_outlinks ---

def test_get_outlinks_valid_and_broken(linked_vault):
    """c.md has one valid... wait c.md only has broken. Check correct split."""
    result = get_outlinks(linked_vault, "c")
    # [[phantom]] should be broken
    broken_targets = [e["target"] for e in result["broken"]]
    assert "phantom" in broken_targets
    # No valid links from c.md
    assert result["valid"] == []


def test_get_outlinks_valid_links(linked_vault):
    """a.md links to b.md and c.md — both should appear in valid."""
    result = get_outlinks(linked_vault, "a")
    valid_resolved = [e["resolved_path"] for e in result["valid"]]
    assert "b.md" in valid_resolved
    assert "c.md" in valid_resolved


def test_get_outlinks_returns_correct_fields(linked_vault):
    """Each outlink entry has target, resolved_path, is_valid, is_embed."""
    result = get_outlinks(linked_vault, "a")
    assert len(result["valid"]) > 0
    entry = result["valid"][0]
    assert "target" in entry
    assert "resolved_path" in entry
    assert "is_valid" in entry
    assert "is_embed" in entry


def test_get_outlinks_missing_note_raises(linked_vault):
    with pytest.raises(FileNotFoundError):
        get_outlinks(linked_vault, "does-not-exist-note")


def test_get_outlinks_fixture_vault_broken_link(vault):
    """linked-note.md has a broken link to [[does-not-exist]] in the fixture vault."""
    result = get_outlinks(vault, "linked-note")
    broken_targets = [e["target"] for e in result["broken"]]
    assert "does-not-exist" in broken_targets


# --- find_orphans ---

def test_find_orphans_identifies_isolated(linked_vault):
    """d.md is fully isolated — no links in or out."""
    result = find_orphans(linked_vault)
    assert "d.md" in result["fully_isolated"]


def test_find_orphans_connected_notes_not_isolated(linked_vault):
    """a.md and b.md are connected — should not appear in fully_isolated."""
    result = find_orphans(linked_vault)
    assert "a.md" not in result["fully_isolated"]
    assert "b.md" not in result["fully_isolated"]


def test_find_orphans_has_expected_keys(linked_vault):
    result = find_orphans(linked_vault)
    assert "fully_isolated" in result
    assert "no_backlinks" in result
    assert "no_outlinks" in result
    assert "total_notes" in result


def test_find_orphans_total_count(linked_vault):
    result = find_orphans(linked_vault)
    assert result["total_notes"] == 4


# --- find_broken_links ---

def test_find_broken_links_finds_phantom(linked_vault):
    """c.md has a broken link [[phantom]]."""
    broken = find_broken_links(linked_vault)
    target_links = [e["target_link"] for e in broken]
    assert "phantom" in target_links


def test_find_broken_links_no_broken_for_a(linked_vault):
    """a.md's links to b.md and c.md are valid — no broken links from a.md."""
    broken = find_broken_links(linked_vault)
    a_broken = [e for e in broken if e["source_path"] == "a.md"]
    assert a_broken == []


def test_find_broken_links_has_source_and_line(linked_vault):
    broken = find_broken_links(linked_vault)
    assert len(broken) > 0
    entry = broken[0]
    assert "source_path" in entry
    assert "target_link" in entry
    assert "line" in entry


def test_find_broken_links_fixture_vault(vault):
    """linked-note.md → [[does-not-exist]] is a broken link in fixture vault."""
    broken = find_broken_links(vault)
    targets = [e["target_link"] for e in broken]
    assert "does-not-exist" in targets


# --- get_graph_neighbors ---

def test_get_graph_neighbors_depth1_outbound(linked_vault):
    """From a.md outbound depth=1 reaches b.md and c.md."""
    neighbors = get_graph_neighbors(linked_vault, "a", depth=1, direction="outbound")
    paths = [n["path"] for n in neighbors]
    assert "b.md" in paths
    assert "c.md" in paths


def test_get_graph_neighbors_depth1_inbound(linked_vault):
    """From b.md inbound depth=1 reaches a.md."""
    neighbors = get_graph_neighbors(linked_vault, "b", depth=1, direction="inbound")
    paths = [n["path"] for n in neighbors]
    assert "a.md" in paths


def test_get_graph_neighbors_depth2_reaches_further(linked_vault):
    """From b.md both direction depth=2 can reach c.md via a.md."""
    neighbors = get_graph_neighbors(linked_vault, "b", depth=2, direction="both")
    paths = [n["path"] for n in neighbors]
    assert "a.md" in paths
    # c.md is 2 hops from b: b→a→c
    assert "c.md" in paths


def test_get_graph_neighbors_start_excluded(linked_vault):
    """Start node should not appear in results."""
    neighbors = get_graph_neighbors(linked_vault, "a", depth=1)
    paths = [n["path"] for n in neighbors]
    assert "a.md" not in paths


def test_get_graph_neighbors_isolated_has_no_neighbors(linked_vault):
    """Isolated d.md has no neighbors at depth=1."""
    neighbors = get_graph_neighbors(linked_vault, "d", depth=1)
    assert neighbors == []


def test_get_graph_neighbors_missing_note_raises(linked_vault):
    with pytest.raises(FileNotFoundError):
        get_graph_neighbors(linked_vault, "nonexistent-note")


def test_get_graph_neighbors_entries_have_depth_and_direction(linked_vault):
    neighbors = get_graph_neighbors(linked_vault, "a", depth=1, direction="outbound")
    assert len(neighbors) > 0
    for n in neighbors:
        assert "path" in n
        assert "depth" in n
        assert "direction" in n
        assert n["depth"] == 1

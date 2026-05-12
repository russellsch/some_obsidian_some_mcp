"""Unit tests for wikilink extractor and resolver."""

import pytest

from some_vault_some_mcp.core.wikilinks import extract_wikilinks, resolve_wikilink


def test_extract_simple():
    content = "See [[note-a]] and [[note-b]]."
    links = extract_wikilinks(content)
    targets = [l["target"] for l in links]
    assert "note-a" in targets
    assert "note-b" in targets


def test_extract_embed():
    content = "![[image.png]]"
    links = extract_wikilinks(content)
    assert len(links) == 1
    assert links[0]["is_embed"] is True
    assert links[0]["target"] == "image.png"


def test_extract_with_display_text():
    content = "[[note|Display Text]]"
    links = extract_wikilinks(content)
    assert links[0]["target"] == "note"
    assert links[0]["display_text"] == "Display Text"


def test_extract_skips_code_block():
    content = "```\n[[in-code-block]]\n```\n[[outside]]"
    links = extract_wikilinks(content)
    targets = [l["target"] for l in links]
    assert "in-code-block" not in targets
    assert "outside" in targets


def test_extract_skips_inline_code():
    content = "`[[inline-code]]` and [[real-link]]"
    links = extract_wikilinks(content)
    targets = [l["target"] for l in links]
    assert "real-link" in targets


def test_resolve_exact_match():
    notes = ["folder/note.md", "other.md"]
    result = resolve_wikilink("folder/note", "source.md", notes)
    assert result == "folder/note.md"


def test_resolve_basename():
    notes = ["folder/note.md", "other.md"]
    result = resolve_wikilink("note", "source.md", notes)
    assert result == "folder/note.md"


def test_resolve_case_insensitive():
    notes = ["Folder/Note.md"]
    result = resolve_wikilink("note", "source.md", notes)
    assert result == "Folder/Note.md"


def test_resolve_alias():
    alias_map = {"my alias": "folder/note.md"}
    result = resolve_wikilink("my alias", "source.md", ["folder/note.md"], alias_map)
    assert result == "folder/note.md"


def test_resolve_not_found():
    result = resolve_wikilink("nonexistent", "source.md", ["other.md"])
    assert result is None


def test_resolve_strips_heading():
    notes = ["note.md"]
    result = resolve_wikilink("note#heading", "source.md", notes)
    assert result == "note.md"


def test_resolve_proximity_tiebreak():
    """Nearest note (by shared path prefix) wins when basename is ambiguous."""
    notes = ["a/b/note.md", "x/y/note.md"]
    # Source is in a/b/ — should prefer a/b/note.md
    result = resolve_wikilink("note", "a/b/source.md", notes)
    assert result == "a/b/note.md"

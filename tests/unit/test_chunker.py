"""Unit tests for the markdown chunker with breadcrumb support."""

import pytest

from some_vault_some_mcp.core.chunker import chunk_markdown, _split_by_headings


def test_basic_chunk():
    content = "---\ntitle: Test\n---\n\nSome body text."
    chunks = chunk_markdown("test.md", content, file_mtime=0.0)
    assert len(chunks) >= 1
    assert chunks[0]["file_path"] == "test.md"
    assert "Some body text." in chunks[0]["content"]


def test_no_frontmatter():
    content = "# Heading\n\nBody text."
    chunks = chunk_markdown("note.md", content)
    assert len(chunks) >= 1


def test_empty_body():
    content = "---\ntitle: Empty\n---\n"
    chunks = chunk_markdown("empty.md", content)
    assert chunks == []


def test_breadcrumb_nested_headings():
    content = (
        "# Design\n\nDesign intro.\n\n"
        "## Architecture\n\nArch content.\n\n"
        "### Implementation\n\nImpl content.\n"
    )
    sections = _split_by_headings(content)
    # Find the Implementation section
    impl = next((h for h, _ in sections if h and "Implementation" in h), None)
    assert impl is not None
    assert "Design" in impl
    assert "Architecture" in impl
    assert "Implementation" in impl
    # Verify breadcrumb format
    assert " > " in impl


def test_breadcrumb_in_chunk_heading():
    content = (
        "---\ntitle: BreadcrumbTest\n---\n\n"
        "# A\n\nA content.\n\n"
        "## B\n\nB content.\n\n"
        "### C\n\nC content.\n"
    )
    chunks = chunk_markdown("bc.md", content)
    # Find C's chunk
    c_chunk = next((c for c in chunks if c["heading"] and "C" in c["heading"]), None)
    assert c_chunk is not None
    assert "A" in c_chunk["heading"]
    assert "B" in c_chunk["heading"]
    assert "C" in c_chunk["heading"]


def test_breadcrumb_resets_on_higher_level():
    content = (
        "# A\n\nA content.\n\n"
        "## B\n\nB content.\n\n"
        "# C\n\nC content (new top-level, breadcrumb resets).\n"
    )
    sections = _split_by_headings(content)
    # C should not include A or B in its breadcrumb
    c_section = next((h for h, _ in sections if h and h == "C"), None)
    assert c_section is not None
    assert "A" not in c_section
    assert "B" not in c_section


def test_no_heading_chunk_empty_breadcrumb():
    content = "Body before any heading.\n"
    sections = _split_by_headings(content)
    assert sections[0][0] is None


def test_breadcrumb_in_section_field():
    content = (
        "---\ntitle: Meta\n---\n\n"
        "# Parent\n\nParent content.\n\n"
        "## Child\n\nChild content here.\n"
    )
    chunks = chunk_markdown("meta.md", content)
    child = next((c for c in chunks if "Child" in c.get("heading", "")), None)
    assert child is not None
    assert "Section: Parent > Child" in child["text_to_embed"]


def test_metadata_header_in_text_to_embed():
    content = (
        "---\ntitle: MyNote\ntags:\n  - foo\n---\n\n"
        "# Section\n\nContent.\n"
    )
    chunks = chunk_markdown("meta.md", content)
    assert chunks
    assert "Title: MyNote" in chunks[0]["text_to_embed"]
    assert "Tags: foo" in chunks[0]["text_to_embed"]


def test_chunk_index_sequential():
    content = (
        "---\ntitle: Seq\n---\n\n"
        "# A\n\nA.\n\n"
        "# B\n\nB.\n\n"
        "# C\n\nC.\n"
    )
    chunks = chunk_markdown("seq.md", content)
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_large_section_splits():
    # Create a section with multiple paragraphs totalling > TARGET_CHUNK_SIZE (2000 chars)
    # Paragraph-based splitting requires double-newlines between paragraphs
    para = "word " * 200 + "\n"  # ~1000 chars per para
    long_body = (para + "\n") * 4  # 4 paragraphs, ~4000 chars total
    content = f"---\ntitle: Large\n---\n\n# Big Section\n\n{long_body}"
    chunks = chunk_markdown("large.md", content, file_mtime=0.0)
    assert len(chunks) > 1


def test_html_stripped():
    content = "---\ntitle: T\n---\n\n# S\n\n<b>Bold</b> text.\n"
    chunks = chunk_markdown("html.md", content)
    assert "<b>" not in chunks[0]["content"]
    assert "Bold" in chunks[0]["content"]

"""Semantic quality tests — verify real embeddings produce meaningful search results.

Uses FastEmbedProvider (nomic-embed-text-v1.5-Q) to validate the full pipeline:
chunking, embedding, LanceDB storage, vector search.
"""

from pathlib import Path

import pytest

from some_vault_some_mcp.core.embeddings import FastEmbedProvider
from some_vault_some_mcp.core.indexer import full_index, _get_db
from some_vault_some_mcp.tools.search import semantic_search


@pytest.fixture(scope="session")
def fastembed_provider():
    return FastEmbedProvider()


THEME_DOCS = {
    "python.md": (
        "---\ntitle: Python Programming\n---\n\n"
        "Python is a high-level programming language. "
        "List comprehensions provide a concise way to create lists. "
        "Decorators modify function behavior at definition time. "
        "The GIL limits true parallelism in CPython threads."
    ),
    "cooking.md": (
        "---\ntitle: Italian Cooking\n---\n\n"
        "Pasta should be cooked in salted boiling water until al dente. "
        "A proper ragu bolognese simmers for at least three hours. "
        "Fresh basil and mozzarella make a classic caprese salad."
    ),
    "music.md": (
        "---\ntitle: Music Theory\n---\n\n"
        "A major scale follows the pattern whole-whole-half-whole-whole-whole-half. "
        "Chords are built by stacking thirds above a root note. "
        "The circle of fifths maps key signatures and their relationships."
    ),
    "gardening.md": (
        "---\ntitle: Container Gardening\n---\n\n"
        "Tomatoes need full sun and consistent watering in containers. "
        "Herbs like basil and rosemary thrive in well-drained potting mix. "
        "Raised beds improve drainage and reduce soil compaction."
    ),
}


@pytest.fixture()
def themed_vault(tmp_path, fastembed_provider):
    vault = tmp_path / "vault"
    vault.mkdir()
    for name, content in THEME_DOCS.items():
        (vault / name).write_text(content, encoding="utf-8")

    db_path = str(tmp_path / "vault.lance")
    full_index(str(vault), db_path, fastembed_provider)
    return db_path


def _top_title(results):
    if not results:
        return None
    return results[0].title


def test_python_query_finds_python_doc(themed_vault, fastembed_provider):
    results = semantic_search("list comprehension decorator", themed_vault, fastembed_provider, top_k=4)
    assert _top_title(results) == "Python Programming"


def test_cooking_query_finds_cooking_doc(themed_vault, fastembed_provider):
    results = semantic_search("how to make pasta sauce", themed_vault, fastembed_provider, top_k=4)
    assert _top_title(results) == "Italian Cooking"


def test_music_query_finds_music_doc(themed_vault, fastembed_provider):
    results = semantic_search("chord progressions and scales", themed_vault, fastembed_provider, top_k=4)
    assert _top_title(results) == "Music Theory"


def test_gardening_query_finds_gardening_doc(themed_vault, fastembed_provider):
    results = semantic_search("growing tomatoes in pots", themed_vault, fastembed_provider, top_k=4)
    assert _top_title(results) == "Container Gardening"

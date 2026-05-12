"""Tag tools: get_tags."""

import logging
from pathlib import Path

from some_vault_some_mcp.core.frontmatter import extract_all_tags
from some_vault_some_mcp.core.paths import walk_vault

logger = logging.getLogger(__name__)


def get_tags(vault_path: str, sort_by: str = "count") -> list[dict]:
    """Enumerate all unique tags with usage counts.

    Returns list of {tag: str, count: int} sorted by sort_by.
    count = number of notes (not occurrences) that use the tag.
    """
    all_notes = walk_vault(vault_path)
    tag_map: dict[str, set[str]] = {}  # tag -> set of file paths

    for rel_path in all_notes:
        full_path = Path(vault_path) / rel_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        tags = extract_all_tags(content)
        for tag in tags:
            normalized = tag.lower()
            if normalized not in tag_map:
                tag_map[normalized] = set()
            tag_map[normalized].add(rel_path)

    result = [{"tag": tag, "count": len(files)} for tag, files in tag_map.items()]

    if sort_by == "name":
        result.sort(key=lambda x: x["tag"])
    else:
        result.sort(key=lambda x: (-x["count"], x["tag"]))

    return result

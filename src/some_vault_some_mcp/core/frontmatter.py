"""YAML frontmatter reader/writer — gray-matter equivalent for Python.

Parses the leading ---/--- YAML block and returns (metadata dict, body str).
Round-trips cleanly: parsed metadata can be merged and re-serialized without
losing the body.
"""

import re
from typing import Any

import yaml


_FENCE_RE = re.compile(r"^---\r?\n", re.MULTILINE)
MAX_FRONTMATTER_LINES = 500
MAX_FRONTMATTER_BYTES = 64 * 1024


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return (metadata, body) from markdown content.

    Body is the content after the closing --- delimiter (stripped of leading
    whitespace). If no valid frontmatter, returns ({}, content).
    Malformed YAML returns ({}, content) — a single broken note must not
    abort vault-wide loops.
    """
    if not content.startswith("---"):
        return {}, content

    first_newline = content.find("\n")
    if first_newline == -1:
        return {}, content

    # First line must be exactly "---" (maybe with \r)
    if content[:first_newline].rstrip("\r") != "---":
        return {}, content

    # Scan for closing delimiter, bounded
    offset = first_newline + 1
    lines = 0
    while offset < len(content) and offset < MAX_FRONTMATTER_BYTES:
        if lines >= MAX_FRONTMATTER_LINES:
            return {}, content
        next_newline = content.find("\n", offset)
        line_end = next_newline if next_newline != -1 else len(content)
        line = content[offset:line_end].rstrip("\r")
        if line == "---":
            yaml_str = content[first_newline + 1:offset].strip()
            body_start = line_end + 1 if next_newline != -1 else line_end
            body = content[body_start:].lstrip("\n")
            try:
                metadata = yaml.safe_load(yaml_str) or {}
                if not isinstance(metadata, dict):
                    metadata = {}
            except yaml.YAMLError:
                metadata = {}
            return metadata, body
        if next_newline == -1:
            return {}, content
        offset = next_newline + 1
        lines += 1

    return {}, content


def serialize_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Serialize metadata as YAML frontmatter prepended to body."""
    yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body}"


def update_frontmatter(content: str, updates: dict[str, Any]) -> str:
    """Merge updates into existing frontmatter (or create one) and return new content.

    Keys in updates overwrite existing values; all other keys preserved.
    Body content is unchanged.
    """
    metadata, body = parse_frontmatter(content)
    merged = {**metadata, **updates}
    return serialize_frontmatter(merged, body)


def extract_inline_tags(content: str) -> list[str]:
    """Extract #hashtags from the body (not frontmatter) of a note.

    Skips lines inside code blocks. Returns list without # prefix.
    """
    _, body = parse_frontmatter(content)
    tags: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    tag_re = re.compile(
        r"(?:^|\s)#([a-zA-ZÀ-ɏЀ-ӿ_][a-zA-Z0-9À-ɏЀ-ӿ_/-]*)"
    )
    for line in body.split("\n"):
        # Code fence tracking
        stripped = line.lstrip()
        if in_fence:
            close_re = re.compile(rf"^{re.escape(fence_char)}{{{fence_len},}}\s*$")
            if close_re.match(stripped):
                in_fence = False
            continue
        backtick_m = re.match(r"^(`{3,})", stripped)
        tilde_m = re.match(r"^(~{3,})", stripped)
        if backtick_m:
            in_fence = True
            fence_char = "`"
            fence_len = len(backtick_m.group(1))
            continue
        if tilde_m:
            in_fence = True
            fence_char = "~"
            fence_len = len(tilde_m.group(1))
            continue
        # Skip headings
        if re.match(r"^\s*#{1,6}\s", line):
            continue
        for m in tag_re.finditer(line):
            tags.append(m.group(1))
    return tags


def extract_all_tags(content: str) -> list[str]:
    """Extract tags from both frontmatter and inline body text.

    Returns deduplicated list, lowercase, no # prefix.
    """
    tag_set: set[str] = set()
    metadata, _ = parse_frontmatter(content)
    # Frontmatter tags — check common casings
    fm_tags = (
        metadata.get("tags")
        or metadata.get("Tags")
        or metadata.get("TAGS")
        or metadata.get("tag")
        or metadata.get("Tag")
        or []
    )
    if isinstance(fm_tags, list):
        for t in fm_tags:
            s = str(t).strip()
            if s:
                tag_set.add(s.lower())
    elif isinstance(fm_tags, str):
        for t in fm_tags.split(","):
            s = t.strip()
            if s:
                tag_set.add(s.lower())

    for t in extract_inline_tags(content):
        tag_set.add(t.lower())

    return list(tag_set)


def extract_aliases(content: str) -> list[str]:
    """Extract frontmatter aliases field."""
    metadata, _ = parse_frontmatter(content)
    aliases_raw = (
        metadata.get("aliases")
        or metadata.get("Aliases")
        or metadata.get("ALIASES")
        or metadata.get("alias")
        or metadata.get("Alias")
        or []
    )
    if isinstance(aliases_raw, list):
        return [str(a).strip() for a in aliases_raw if str(a).strip()]
    if isinstance(aliases_raw, str):
        return [a.strip() for a in aliases_raw.split(",") if a.strip()]
    return []

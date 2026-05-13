#!/usr/bin/env python3
"""Bump the version in pyproject.toml: major, minor, or patch."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"


def bump(part: str) -> str:
    text = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text, re.MULTILINE)
    if not match:
        sys.exit("Could not find version in pyproject.toml")

    major, minor, patch = int(match[1]), int(match[2]), int(match[3])

    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        sys.exit(f"Unknown part: {part}. Use major, minor, or patch.")

    new_version = f"{major}.{minor}.{patch}"
    new_text = re.sub(
        r'^(version\s*=\s*")[\d.]+(")',
        rf"\g<1>{new_version}\2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(new_text)
    print(new_version)
    return new_version


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <major|minor|patch>")
    bump(sys.argv[1])

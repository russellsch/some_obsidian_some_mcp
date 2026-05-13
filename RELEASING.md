# Releasing

## Release a new version

```bash
./scripts/release.sh patch   # 0.0.2 → 0.0.3
./scripts/release.sh minor   # 0.0.3 → 0.1.0
./scripts/release.sh major   # 0.1.0 → 1.0.0
```

This bumps the version, updates `uv.lock`, commits, tags, pushes, and creates a GitHub Release. The publish workflow uploads to PyPI automatically via OIDC Trusted Publishing.

Track progress: https://github.com/russellsch/some_obsidian_some_mcp/actions

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth login`)
- On `main` branch with a clean working tree
- PyPI Trusted Publisher configured (one-time setup below)

## One-time setup

### PyPI Trusted Publisher

1. Go to https://pypi.org/manage/project/some-vault-some-mcp/settings/publishing/
2. Add a publisher: owner `russellsch`, repo `some_obsidian_some_mcp`, workflow `publish.yml`, environment `pypi`

### GitHub environment

1. Go to https://github.com/russellsch/some_obsidian_some_mcp/settings/environments
2. Create an environment named `pypi`

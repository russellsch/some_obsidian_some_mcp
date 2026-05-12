# some-vault-some-mcp

MCP server that gives AI models read/write access to Obsidian vaults with semantic search, link graph analysis, canvas manipulation, and incremental indexing.

Built on FastMCP + LanceDB. Embeds notes locally with fastembed (nomic-embed-text-v1.5-Q, 768 dims) by default — no server required. Optionally supports Ollama or OpenAI embeddings. Watches the vault filesystem and re-indexes on change.

Warning: This is a hot vibe coded mess, user beware

## What it does

- Hybrid search - vector similarity (70%) + full-text keyword (30%), with overlap boost
- Semantic search - pure embedding-based retrieval
- Exact search - literal substring matching, optional case sensitivity and regex
- Note CRUD - create, read, append, prepend, move, delete (soft delete to .trash by default)
- Frontmatter parsing - YAML extraction, tag collection (frontmatter + inline #hashtags), property filtering
- Wikilink graph - backlinks, outlinks, orphan detection, broken link detection, BFS neighbor traversal (depth 1-5)
- Canvas CRUD - create, read, add/update/remove nodes and edges, grid auto-layout, dangling edge cleanup
- Daily notes - Moment.js-style date formatting, template support, reads Obsidian's daily-notes config
- Incremental indexing - filesystem watcher with 2s debounce, mtime-based change detection
- Atomic writes - temp file + POSIX rename, per-path asyncio locks
- Tool overrides - rename or disable any tool via YAML config (per-agent customization)

## Requirements

- Python 3.11+

## Install

```bash
uv sync --no-dev                  # default (fastembed CPU)
uv sync --no-dev --extra gpu      # GPU-accelerated embeddings
uv sync --no-dev --extra ollama   # if you prefer Ollama
uv sync --no-dev --extra openai   # if you prefer OpenAI
```

## Run

```bash
VAULT_PATH=/path/to/vault some-vault-some-mcp serve
```

First run does a full index of the vault - takes a few minutes depending on size. Subsequent starts run incremental index only.

### CLI flags

```
some-vault-some-mcp serve [--transport sse|stdio] [--host 0.0.0.0] [--port 3789]
```

CLI flags override env vars.

## MCP client config

For Cursor, Windsurf, Claude Code, or any MCP client that spawns the server as a subprocess:

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/some_obsidian_some_mcp", "some-vault-some-mcp", "serve", "--transport", "stdio"],
      "env": {
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

If running the server separately (Docker, remote, etc), use the SSE URL instead:

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "url": "http://localhost:3789/sse"
    }
  }
}
```

`--project` tells uv where to find the pyproject.toml. Without it, `uv run` only works if cwd is this repo.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `VAULT_PATH` | (required) | Absolute path to Obsidian vault |
| `LANCE_DB_PATH` | `./data/vault.lance` | Where the vector index lives |
| `MCP_TRANSPORT` | `sse` | `sse` or `stdio` |
| `MCP_HOST` | `0.0.0.0` | SSE bind address |
| `MCP_PORT` | `3789` | SSE port |
| `EMBEDDING_PROVIDER` | `fastembed` | `fastembed`, `ollama`, `openai`, or `mock` |
| `FASTEMBED_MODEL` | `nomic-ai/nomic-embed-text-v1.5-Q` | Any fastembed-supported model |
| `FASTEMBED_DIMENSIONS` | (auto-detected) | Override dimension auto-detection |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint (requires `--extra ollama`) |
| `OPENAI_API_KEY` | | Required if provider is `openai` (requires `--extra openai`) |
| `VAULT_API_KEY` | | Enables Bearer token auth on SSE transport |
| `VAULT_SOFT_DELETE_IS_PERMANENT` | `false` | `true` makes delete_note do hard deletes |
| `some_vault_some_mcp_OVERRIDES` | | Path to YAML override file |

## Docker

```bash
docker build -t some-vault-some-mcp .

docker run -p 3789:3789 \
  -v /path/to/vault:/opt/vault:ro \
  -v /data:/opt/data \
  some-vault-some-mcp
```

Runs as non-root user (vault:vault, UID 1000). Index data persists in `/opt/data`. Vault mounted read-only. Container is self-contained — fastembed runs in-process, no Ollama sidecar needed.

To use Ollama instead: `docker run ... -e EMBEDDING_PROVIDER=ollama -e OLLAMA_URL=http://ollama:11434 some-vault-some-mcp`

## Tools (27)

**Search**
- `search` - hybrid, semantic, or exact mode. Filterable by tags and folder.

**Read**
- `get_note` - single note with parsed frontmatter and tags
- `list_notes` - paginated listing with index-backed filtering (tags, projects, status, area) and frontmatter property filtering

**Write**
- `create_note` - fails if exists
- `append_to_note` - adds text at end
- `prepend_to_note` - inserts after frontmatter, before body
- `update_frontmatter` - merges key-value pairs, preserves unlisted keys
- `move_note` - move/rename with vault-wide wikilink rewriting
- `delete_note` - soft delete (.trash) or permanent

**Daily notes**
- `get_daily_note` - today's or a specific date
- `create_daily_note` - with optional template, respects Obsidian daily-notes config

**Tags**
- `get_tags` - all unique tags with counts, sorted

**Link graph**
- `get_backlinks` - notes linking to a given note
- `get_outlinks` - outgoing wikilinks (valid + broken)
- `find_orphans` - disconnected notes (no inbound, no outbound, or both)
- `find_broken_links` - wikilinks pointing at nonexistent notes
- `get_graph_neighbors` - BFS walk, depth 1-5, direction: inbound/outbound/both

**Canvas**
- `list_canvases` - all .canvas files, optional folder filter
- `read_canvas` - node and edge structure of a canvas
- `create_canvas` - new canvas with optional initial nodes/edges
- `add_canvas_node` - add text/file/link/group node, grid auto-layout when position omitted
- `update_canvas_node` - update any property of an existing node by ID
- `remove_canvas_nodes` - remove nodes by ID, auto-removes dangling edges
- `add_canvas_edge` - add edge with full property support (side anchors, arrow ends, color, label)
- `update_canvas_edge` - update edge properties by ID
- `remove_canvas_edges` - remove edges by ID

**Index management**
- `vault_index_status` - index health and stats
- `vault_reindex` - incremental reindex for one note or entire vault

## MCP resources

- `obsidian://note/{path}` - read a note by path
- `obsidian://tags` - all tags
- `obsidian://daily` - today's daily note

## Tool name overrides

When you need to change the tool names and descriotions, a YAML file can be used. Create a YAML file, and set `some_vault_some_mcp_OVERRIDES` to its path:

```yaml
tools:
  search:
    name: "vault_search"
    description: "Custom description for this agent"
  get_note:
    name: "read_note"
disabled:
  - get_tags
  - find_orphans
```

Overrides apply at registration time. Useful for per-agent tool namespacing or disabling tools an agent shouldn't use if your agent doesn't support tool disabling.

## How search works

**Hybrid** (default) - runs both semantic and keyword search at 2x requested top_k, normalizes scores, combines with `semantic * 0.7 + keyword * 0.3`. Results appearing in both get a 1.2x boost. Returns top_k from merged set.

**Semantic** - embeds the query, runs vector similarity search against LanceDB.

**Exact** - scans vault files for literal substring matches. Optional case sensitivity.

All search modes accept tag and folder pre-filters. Tags use SQL LIKE against comma-separated tag strings in the index. Folders use path prefix matching.

## Chunking

Splits markdown by heading hierarchy first, then by paragraph for oversized sections. Tracks heading breadcrumbs through the split - a chunk under `# A / ## B / ### C` gets heading field `"A > B > C"`. Metadata header prepended to embedding text: `[Title: X | Section: A > B | Tags: foo, bar]`.

## Wikilink resolution

Matches Obsidian's behavior in 4 steps:
1. Exact relative-path match (case-insensitive)
2. Path-suffix match (if link contains `/`)
3. Basename match with proximity tie-break (deepest shared path prefix with source)
4. Alias match (frontmatter aliases)

First matching step wins.

## Security boundaries

- All paths validated against vault root - rejects `../`, null bytes, symlink escapes
- `.obsidian`, `.git`, `.trash` excluded from indexing and tool access
- Optional Bearer token auth on SSE transport
- Docker container runs as non-root
- Bounded frontmatter parsing prevents YAML bombs

## Tests

```bash
uv sync
uv run pytest
```

Unit tests cover core logic without external dependencies. Integration tests use MockProvider (deterministic seeded vectors) against real LanceDB. Semantic quality tests use FastEmbedProvider with real embeddings (model downloads to `~/.cache/fastembed/` on first run, ~130MB).

Test fixtures live in `tests/fixtures/vault/` - a minimal vault with frontmatter, wikilinks, nested folders, daily notes, canvas files, and excluded directories.

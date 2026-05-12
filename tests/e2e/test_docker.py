"""E2E: build Docker image, start container, connect via MCP SSE, call tools.

Uses the existing test vault at tests/fixtures/vault (mounted read-only).
EMBEDDING_PROVIDER=mock so no Ollama needed.
"""

import json
import time
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_VAULT = Path(__file__).parent.parent / "fixtures" / "vault"


def _poll_health(url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module")
def mcp_url():
    """Build image and run container with test vault mounted."""
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.image import DockerImage

    with DockerImage(path=str(PROJECT_ROOT), tag="vault-mcp-e2e:latest") as image:
        container = (
            DockerContainer(str(image))
            .with_env("EMBEDDING_PROVIDER", "mock")
            .with_env("VAULT_PATH", "/opt/vault")
            .with_env("LANCE_DB_PATH", "/opt/data/vault.lance")
            .with_env("MCP_TRANSPORT", "sse")
            .with_env("MCP_HOST", "0.0.0.0")
            .with_env("MCP_PORT", "3789")
            .with_volume_mapping(str(TEST_VAULT.resolve()), "/opt/vault", "ro")
            .with_exposed_ports(3789)
        )
        with container:
            host = container.get_container_host_ip()
            port = container.get_exposed_port(3789)
            url = f"http://{host}:{port}"
            assert _poll_health(url), "Container did not become healthy within 60s"
            yield url


async def _mcp_call(url: str, tool: str, args: dict | None = None) -> str:
    """Open a fresh MCP SSE session, call one tool, return text content."""
    from mcp.client.session import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=f"{url}/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=args or {})
            return result.content[0].text


# ── container build + health ─────────────────────────────────────────────


class TestContainerHealth:
    def test_health_returns_ok(self, mcp_url):
        with urllib.request.urlopen(f"{mcp_url}/") as resp:
            assert resp.status == 200
            body = json.loads(resp.read())
            assert body["status"] == "ok"
            assert body["service"] == "some-vault-some-mcp"


# ── MCP protocol ─────────────────────────────────────────────────────────


class TestMCPProtocol:
    async def test_lists_expected_tools(self, mcp_url):
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client

        async with sse_client(url=f"{mcp_url}/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                names = {t.name for t in result.tools}

        expected = {
            "search", "get_note", "list_notes", "create_note",
            "append_to_note", "prepend_to_note", "update_frontmatter",
            "move_note", "delete_note",
            "get_daily_note", "create_daily_note",
            "get_tags", "get_backlinks", "get_outlinks",
            "find_orphans", "find_broken_links", "get_graph_neighbors",
            "vault_index_status", "vault_reindex",
        }
        assert expected <= names, f"Missing tools: {expected - names}"


# ── vault tool operations ────────────────────────────────────────────────


class TestVaultTools:
    async def test_list_notes_finds_fixtures(self, mcp_url):
        text = await _mcp_call(mcp_url, "list_notes")
        assert "simple.md" in text
        assert "linked-note.md" in text
        assert "large-note.md" in text

    async def test_read_note_content(self, mcp_url):
        text = await _mcp_call(mcp_url, "get_note", {"path": "simple.md"})
        assert "Simple Note" in text
        assert "linked-note" in text

    async def test_read_note_not_found(self, mcp_url):
        text = await _mcp_call(mcp_url, "get_note", {"path": "nonexistent.md"})
        assert "not found" in text.lower()

    async def test_tags_from_vault(self, mcp_url):
        text = await _mcp_call(mcp_url, "get_tags")
        assert "reference" in text
        assert "test" in text
        assert "project" in text

    async def test_backlinks(self, mcp_url):
        text = await _mcp_call(mcp_url, "get_backlinks", {"path": "linked-note.md"})
        assert "simple" in text.lower()

    async def test_outlinks(self, mcp_url):
        text = await _mcp_call(mcp_url, "get_outlinks", {"path": "simple.md"})
        assert "linked-note" in text
        assert "deep-note" in text

    async def test_broken_links(self, mcp_url):
        text = await _mcp_call(mcp_url, "find_broken_links")
        assert "does-not-exist" in text

    async def test_exact_search(self, mcp_url):
        text = await _mcp_call(mcp_url, "search", {
            "query": "simple note with frontmatter",
            "mode": "exact",
        })
        assert "simple" in text.lower()

    async def test_semantic_search(self, mcp_url):
        text = await _mcp_call(mcp_url, "search", {
            "query": "deeply nested architecture",
            "mode": "semantic",
        })
        assert "result" in text.lower()

    async def test_index_status(self, mcp_url):
        text = await _mcp_call(mcp_url, "vault_index_status")
        assert "Files indexed:" in text
        assert "Total chunks:" in text

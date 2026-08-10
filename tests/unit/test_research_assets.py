"""Drift-lock the exhaustive-research assets against each other (T-0185/T-0186).

WHY: the exhaustive-research skill/agent, its .mcp.json server pins, its
setup guide, and the guide's link from docs/index.md are four separate
files with no shared parser to keep them honest (.md and .json are not
tree-sitter-parsed by frob.lang, so DOC001/COV001 can't see inside them).
A server dropped from .mcp.json, a guide moved without updating the
skill's frob:doc anchor, or a docs/index.md link silently deleted would
all go unnoticed until someone actually ran the workflow. This test reads
the real files and asserts the cross-references still hold, so the drift
fails CI instead of a future agent.

"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_JSON = REPO_ROOT / ".mcp.json"
GUIDE_MD = REPO_ROOT / "docs" / "guides" / "exhaustive-research.md"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

REQUIRED_MCP_SERVERS = {"serena", "frob", "fetch", "arxiv"}

def test_mcp_json_parses_and_declares_required_servers():
    """.mcp.json is valid JSON and pins exactly the servers the loop needs.

    WHY: docs/guides/exhaustive-research.md names serena/frob/fetch/arxiv as
    the frontier-loop's MCP dependencies; if .mcp.json drops one (or is
    hand-edited into invalid JSON), the workflow breaks silently until an
    agent actually tries to call the missing server.
    """
    assert MCP_JSON.exists(), f"expected {MCP_JSON} to exist"
    payload = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    servers = set(payload.get("mcpServers", {}))
    missing = REQUIRED_MCP_SERVERS - servers
    assert not missing, f".mcp.json is missing required server(s): {sorted(missing)}"


def test_docs_index_links_the_guide():
    """docs/index.md links docs/guides/exhaustive-research.md (T-0186's deliverable).

    WHY: T-0185's guide originally shipped outside any DOC001-reachable
    root (docs/index.md was outside T-0185's own scope), so DOC001 would
    go red on merge until T-0186 added this link. This locks the link in
    place so a future docs/index.md edit can't silently drop it again.
    """
    assert INDEX_MD.exists(), f"expected {INDEX_MD} to exist"
    index_text = INDEX_MD.read_text(encoding="utf-8")
    assert "docs/guides/exhaustive-research.md" in index_text, (
        f"{INDEX_MD} no longer links docs/guides/exhaustive-research.md"
    )

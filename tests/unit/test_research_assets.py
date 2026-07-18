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
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_JSON = REPO_ROOT / ".mcp.json"
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "exhaustive-research" / "SKILL.md"
GUIDE_MD = REPO_ROOT / "docs" / "guides" / "exhaustive-research.md"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

REQUIRED_MCP_SERVERS = {"serena", "frob", "fetch", "arxiv"}

_FROB_DOC_RE = re.compile(r"<!--\s*frob:doc\s+(?P<file>\S+?)#(?P<slug>\S+?)\s*-->")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def _slugify(heading: str) -> str:
    """GitHub-style heading slug: lowercase, non-alnum runs collapsed to '-'.

    WHY: mirrors frob.graph.dsl.slugify exactly so this test checks the
    same anchor resolution the doclink/docanchor gates perform, without
    importing gate internals into a unit test.
    """
    slug = _SLUG_STRIP_RE.sub("-", heading.strip().lower()).strip("-")
    return slug or "top"


def _heading_slugs(text: str) -> set[str]:
    """Every heading slug present in a markdown document's text."""
    return {
        _slugify(match.group(2))
        for line in text.splitlines()
        if (match := _HEADING_RE.match(line)) is not None
    }


def test_mcp_json_parses_and_declares_required_servers():
    """.mcp.json is valid JSON and pins exactly the servers the skill needs.

    WHY: docs/guides/exhaustive-research.md and the exhaustive-researcher
    agent both name serena/frob/fetch/arxiv as the frontier-loop's MCP
    dependencies; if .mcp.json drops one (or is hand-edited into invalid
    JSON), the workflow breaks silently until an agent actually tries to
    call the missing server.
    """
    assert MCP_JSON.exists(), f"expected {MCP_JSON} to exist"
    payload = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    servers = set(payload.get("mcpServers", {}))
    missing = REQUIRED_MCP_SERVERS - servers
    assert not missing, f".mcp.json is missing required server(s): {sorted(missing)}"


def test_skill_frob_doc_anchor_resolves_in_guide():
    """SKILL.md's frob:doc directive points at a heading that exists in the guide.

    WHY: this is exactly what DOC002 (docanchor) checks in the real graph
    for parseable languages; since .md carries no frob.lang grammar, the
    gate can't see this edge at all -- this test is the only thing that
    would catch the guide's title heading drifting out from under the
    skill's anchor.
    """
    assert SKILL_MD.exists(), f"expected {SKILL_MD} to exist"
    assert GUIDE_MD.exists(), f"expected {GUIDE_MD} to exist"
    skill_text = SKILL_MD.read_text(encoding="utf-8")
    match = _FROB_DOC_RE.search(skill_text)
    assert match is not None, f"{SKILL_MD} has no frob:doc directive to check"
    assert match.group("file") == "docs/guides/exhaustive-research.md", (
        f"{SKILL_MD}'s frob:doc directive points at {match.group('file')!r}, "
        "not the exhaustive-research guide"
    )
    guide_slugs = _heading_slugs(GUIDE_MD.read_text(encoding="utf-8"))
    assert match.group("slug") in guide_slugs, (
        f"{SKILL_MD}'s frob:doc anchor #{match.group('slug')} does not match "
        f"any heading slug in {GUIDE_MD} ({sorted(guide_slugs)})"
    )


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

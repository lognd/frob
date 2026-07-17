"""FastMCP stdio server exposing `frob.serve._tools` as MCP tools
(docs/modules/serve.md).

Deferred import of `mcp` -- `frob.serve` must remain importable (for tests
and `frob serve --help`) even in environments where the `mcp` SDK is not
installed; only `build_server`/`run_stdio` require it.
"""

from __future__ import annotations

from pathlib import Path

from frob.logging import get_logger
from frob.serve import _tools

_log = get_logger(__name__)


# frob:doc docs/modules/serve.md#mcp-sdk
class McpUnavailable(Exception):
    """Raised when the `mcp` SDK is not importable; an env/setup bug, not a Result."""


def _require_mcp():  # noqa: ANN202
    """Import `mcp.server.fastmcp.FastMCP`, or raise `McpUnavailable` with a remedy."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        _log.error("serve: mcp SDK not installed: %s", exc)
        raise McpUnavailable(
            "the 'mcp' SDK is not installed; run `uv add mcp` (or `uv sync`) "
            "to enable `frob serve`"
        ) from exc
    return FastMCP


# frob:doc docs/modules/serve.md#mcp-sdk
def build_server(root: Path):  # noqa: ANN201
    """Construct a `FastMCP` server bound to `root`, every read-only tool registered."""
    FastMCP = _require_mcp()  # noqa: N806
    root = root.resolve()
    server = FastMCP("frob")

    @server.tool()
    def frob_doable_tickets() -> list[dict]:
        """List doable tickets (id/title/kind), oldest-first."""
        result = _tools.frob_doable_tickets(root)
        if result.is_err:
            raise RuntimeError(result.danger_err.value)
        return result.danger_ok

    @server.tool()
    def frob_stale_docs() -> dict:
        """DRIFT001 stale acks and DRIFT002 dangling edges from the drift report."""
        result = _tools.frob_stale_docs(root)
        if result.is_err:
            raise RuntimeError(result.danger_err.value)
        return result.danger_ok

    @server.tool()
    def frob_check_scope(ticket_id: str) -> dict:
        """Whether the working diff stays within `ticket_id`'s declared scope."""
        result = _tools.frob_check_scope(root, ticket_id)
        if result.is_err:
            raise RuntimeError(result.danger_err.value)
        return result.danger_ok

    @server.tool()
    def frob_graph_query(symref: str) -> dict:
        """Resolve `symref` and list its outgoing/incoming obligation-graph edges."""
        result = _tools.frob_graph_query(root, symref)
        if result.is_err:
            raise RuntimeError(result.danger_err.value)
        return result.danger_ok

    @server.tool()
    def frob_doc_for(symref: str) -> dict:
        """The doc anchor and describes-edges resolved `symref` is documented by."""
        result = _tools.frob_doc_for(root, symref)
        if result.is_err:
            raise RuntimeError(result.danger_err.value)
        return result.danger_ok

    _log.info("serve: built FastMCP server bound to %s with 5 tools", root)
    return server


# frob:doc docs/modules/serve.md#mcp-sdk
def run_stdio(root: Path) -> None:
    """Build the server and block, serving tool calls over stdio transport."""
    server = build_server(root)
    _log.info("serve: starting stdio transport, root=%s", root)
    server.run(transport="stdio")


__all__ = ["McpUnavailable", "build_server", "run_stdio"]

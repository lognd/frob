"""FastMCP stdio server exposing `frob.serve._tools` as MCP tools
(docs/modules/serve.md).

Deferred import of `mcp` -- `frob.serve` must remain importable (for tests
and `frob serve --help`) even in environments where the `mcp` SDK is not
installed; only `build_server`/`run_stdio` require it.
"""

# frob:waive TEST005 reason="module line coverage 76.6%, debt T-0160"

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
            "the 'mcp' SDK is not installed; run `uv sync --extra serve` "
            '(or `uv pip install "frob[serve]"`) to enable `frob serve`'
        ) from exc
    return FastMCP


def _unwrap(result):  # noqa: ANN001, ANN202
    """A tool's `Result.danger_ok`, or raise `RuntimeError(err.value)` for MCP."""
    if result.is_err:
        raise RuntimeError(result.danger_err.value)
    return result.danger_ok


def _register_query_tools(server, root: Path) -> None:  # noqa: ANN001
    """Register the doable-tickets/stale-docs/graph-query/doc-for read-only tools."""

    @server.tool()
    def frob_doable_tickets() -> list[dict]:
        """List doable tickets (id/title/kind), oldest-first."""
        return _unwrap(_tools.frob_doable_tickets(root))

    @server.tool()
    def frob_stale_docs() -> dict:
        """DRIFT001 stale acks and DRIFT002 dangling edges from the drift report."""
        return _unwrap(_tools.frob_stale_docs(root))

    @server.tool()
    def frob_graph_query(symref: str) -> dict:
        """Resolve `symref` and list its outgoing/incoming obligation-graph edges."""
        return _unwrap(_tools.frob_graph_query(root, symref))

    @server.tool()
    def frob_doc_for(symref: str) -> dict:
        """The doc anchor and describes-edges resolved `symref` is documented by."""
        return _unwrap(_tools.frob_doc_for(root, symref))


def _register_scope_tool(server, root: Path) -> None:  # noqa: ANN001
    """Register the `frob_check_scope` tool."""

    @server.tool()
    def frob_check_scope(ticket_id: str) -> dict:
        """Whether the working diff stays within `ticket_id`'s declared scope."""
        return _unwrap(_tools.frob_check_scope(root, ticket_id))


def _register_incremental_tools(server, root: Path) -> None:  # noqa: ANN001
    """Register the T-0177 `frob_check_delta`/`frob_run_touched_tests`
    tools, both backed by `frob.serve._warm`'s warm graph/baseline/test
    cache."""

    @server.tool()
    def frob_check_delta(
        ticket_id: str | None = None, base: str = "main", verify: bool = False
    ) -> dict:
        """New-since-baseline gate violations for `ticket_id` (all tickets
        if omitted), against `base`; `verify=True` also cross-checks a
        fully cold re-run."""
        return _unwrap(_tools.frob_check_delta(root, ticket_id, base, verify=verify))

    @server.tool()
    def frob_run_touched_tests(base: str = "main") -> dict:
        """Select and run the touched-set tests for `base` (the MCP
        counterpart of `frob test --base <base>`)."""
        return _unwrap(_tools.frob_run_touched_tests(root, base))


# frob:doc docs/modules/serve.md#mcp-sdk
# frob:invariant INV-021
def build_server(root: Path):  # noqa: ANN201
    """Construct a `FastMCP` server bound to `root`, every read-only tool registered."""
    FastMCP = _require_mcp()  # noqa: N806
    root = root.resolve()
    server = FastMCP("frob")

    _register_query_tools(server, root)
    _register_scope_tool(server, root)
    _register_incremental_tools(server, root)

    _log.info("serve: built FastMCP server bound to %s with 7 tools", root)
    return server


# frob:doc docs/modules/serve.md#mcp-sdk
# frob:waive TEST005 reason="run_stdio 50.0% branch cover, debt T-0160"
def run_stdio(root: Path) -> None:
    """Build the server and block, serving tool calls over stdio transport."""
    server = build_server(root)
    _log.info("serve: starting stdio transport, root=%s", root)
    server.run(transport="stdio")


__all__ = ["McpUnavailable", "build_server", "run_stdio"]

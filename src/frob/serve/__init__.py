"""frob.serve -- MCP adapter exposing frob's enforcement queries
(docs/modules/serve.md).

The tool layer (`_tools`) is plain functions over `Result[dict, ServeError]`
and has no dependency on the `mcp` SDK, so it stays importable and testable
even when `mcp` is absent; only `frob.serve.server` (the FastMCP transport)
requires it, imported lazily at call time.
"""

from __future__ import annotations

from frob.serve._tools import (
    ServeError,
    frob_check_scope,
    frob_doable_tickets,
    frob_doc_for,
    frob_graph_query,
    frob_stale_docs,
)


def __getattr__(name: str):  # noqa: ANN201
    """Lazily re-export `frob.serve.server`'s `McpUnavailable`/`build_server`/
    `run_stdio` (T-0362): `server.py` imports the optional `mcp` SDK at
    module scope, so it must stay import-lazy the way the module docstring
    above already promises -- a top-level `from frob.serve.server import
    ...` here would defeat that and make `mcp` a hard dependency of every
    `import frob.serve`.
    """
    if name in {"McpUnavailable", "build_server", "run_stdio"}:
        from frob.serve import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "McpUnavailable",
    "ServeError",
    "build_server",
    "frob_check_scope",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_graph_query",
    "frob_stale_docs",
    "run_stdio",
]

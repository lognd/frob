"""frob.serve -- MCP adapter exposing frob's enforcement queries (docs/serve.md).

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

__all__ = [
    "ServeError",
    "frob_check_scope",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_graph_query",
    "frob_stale_docs",
]

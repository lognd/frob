"""frob.serve -- MCP adapter exposing frob's enforcement queries
(docs/modules/serve.md).

The tool layer (`_tools`) is plain functions over `Result[dict, ServeError]`
and has no dependency on the `mcp` SDK, so it stays importable and testable
even when `mcp` is absent; only `frob.serve.server` (the FastMCP transport)
requires it, imported lazily at call time.
"""

from __future__ import annotations

from frob.serve._events import CoverageWatcher, subscribe_and_wait
from frob.serve._leases import ResourceLeaseManager
from frob.serve._socketd import (
    DaemonError,
    SocketDaemonConfig,
    acquire_singleton_lock,
    daemon_version,
    dispatch_request,
    lock_path,
    run_socket_daemon,
    send_request,
    socket_path,
)
from frob.serve._tools import (
    ServeError,
    frob_affects,
    frob_check_delta,
    frob_check_scope,
    frob_daemon_status,
    frob_doable_tickets,
    frob_doc_for,
    frob_exports,
    frob_graph_query,
    frob_perf_hot,
    frob_run_touched_tests,
    frob_stale_docs,
    frob_stats,
)
from frob.serve._watch import WatchThread, watch_tick


# frob:waive OPAQUE001 reason="T-1038: this module-level __getattr__ only lazily \
# re-exports one of three literal, statically-declared names (the 'in' check below) \
# from frob.serve.server -- not an arbitrary attribute-interception surface; any name \
# outside that closed set raises AttributeError immediately"
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
    "CoverageWatcher",
    "DaemonError",
    "McpUnavailable",
    "ResourceLeaseManager",
    "ServeError",
    "SocketDaemonConfig",
    "WatchThread",
    "acquire_singleton_lock",
    "build_server",
    "daemon_version",
    "dispatch_request",
    "frob_affects",
    "frob_check_delta",
    "frob_check_scope",
    "frob_daemon_status",
    "frob_doable_tickets",
    "frob_doc_for",
    "frob_exports",
    "frob_graph_query",
    "frob_perf_hot",
    "frob_run_touched_tests",
    "frob_stale_docs",
    "frob_stats",
    "lock_path",
    "run_socket_daemon",
    "run_stdio",
    "send_request",
    "socket_path",
    "subscribe_and_wait",
    "watch_tick",
]

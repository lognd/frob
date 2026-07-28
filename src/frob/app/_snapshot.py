"""Shared graph-snapshot load-or-build helper (T-1085 extraction): several
`frob.app` runners (`debt_runner`, `deprecated_runner`, `release_runner`)
each carried their own byte-identical (bar the log message) copy of "try a
cached `frob.graph.load_graph`, build fresh via `frob.graph.build_graph` on
a stale/missing cache, exit(1) on a hard build failure" -- an abstraction-
opportunity finding (T-0393/T-1067's arch-package sweep). `perf_runner`'s
own `_load_snapshot` is a DIFFERENT shape (always rebuilds, never tries
`load_graph` first) and is deliberately NOT folded in here; see this
module's own `load_or_build_snapshot` docstring for why.
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/app.md#shared-graph-snapshot-helper-t-1085
# frob:ticket T-1085
#: The `.frob/cache.db` relative path every graph-backed runner resolves
#: its snapshot cache against -- shared so a future cache-layout change
#: has a single literal to update.
CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/modules/app.md#shared-graph-snapshot-helper-t-1085
# frob:ticket T-1085
# frob:tests tests/test_debt_runner.py::TestDebtRunner.test_json_mode_lists_debt_entries
def load_or_build_snapshot(root: Path, *, log_context: str) -> GraphSnapshot:
    """Load `root`'s cached graph snapshot (`CACHE_REL`), building it fresh
    when the cache is missing/stale -- the load-then-build-fallback shape
    `debt_runner`/`deprecated_runner`/`release_runner` each duplicated
    verbatim before T-1085's extraction. Exits the process (`sys.exit(1)`)
    on a hard build failure, logging `log_context` (e.g. `"debt"`,
    `"deprecated"`, `"release"`) in the error message so the caller's own
    identity survives the shared code path -- the one genuine difference
    the three duplicates had. NOT reused by `perf_runner`'s own
    `_load_snapshot`: that one always rebuilds unconditionally (never
    tries `load_graph` first), a deliberately different caching posture
    for `heat`'s own freshness needs, not an overlooked fourth duplicate.

    `build_graph`/`load_graph` are imported HERE, not at module level --
    mirrors the three original duplicates' own lazy-import shape exactly
    (each did `from frob.graph import build_graph, load_graph` inside the
    function body), which existing tests rely on: they `monkeypatch.
    setattr(frob.graph, "build_graph", ...)` and expect the NEXT call into
    this helper to see the patched attribute, not a name already bound at
    this module's own import time."""
    from frob.graph import build_graph, load_graph

    cache = root / CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded.danger_ok
    built = build_graph(root, cache)
    if built.is_err:
        _log.error("%s: graph build failed: %s", log_context, built.danger_err)
        sys.exit(1)
    return built.danger_ok

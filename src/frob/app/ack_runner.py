"""CLI wiring for `frob ack <ref...> [--facet]` (docs/graph.md)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def run(cfg: AppConfig) -> None:
    """Load (building if the cache is stale), acknowledge refs, and write the lock."""
    from frob.graph import build_graph, load_graph
    from frob.graph.lock import acknowledge, load_lock, write_lock

    if not cfg.ack_refs:
        _log.error("frob ack requires at least one <ref>")
        sys.exit(1)

    root = (cfg.ack_path or Path(".")).resolve()
    cache = root / _CACHE_REL

    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("ack: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.error("ack: graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    snapshot = loaded.danger_ok

    lock_path = root / "frob.lock"
    lock_result = load_lock(lock_path)
    if lock_result.is_err:
        _log.error("ack: frob.lock: %s", lock_result.danger_err)
        sys.exit(1)
    lock = lock_result.danger_ok

    # NOTE: frob.graph.lock.acknowledge derives the facet per-ref from the
    # DESCRIBES edge (docs/graph.md); it does not take a facet override.
    # --facet is accepted for forward-compat / documentation parity but has
    # no effect on which facet gets acked today.
    if cfg.ack_facet != "sig":
        _log.debug(
            "ack: --facet=%s is informational; facet is graph-derived", cfg.ack_facet
        )
    acked = acknowledge(lock, snapshot, cfg.ack_refs)
    if acked.is_err:
        _log.error("ack failed: %s", acked.danger_err)
        sys.exit(1)
    new_lock = acked.danger_ok

    written = write_lock(new_lock, lock_path)
    if written.is_err:
        _log.error("ack: could not write frob.lock: %s", written.danger_err)
        sys.exit(1)

    for ref in cfg.ack_refs:
        _log.info("acked %s", ref)

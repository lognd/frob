"""CLI wiring for `frob ack <ref...> [--facet]` (docs/modules/graph.md)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _load_snapshot_for_ack(root: Path, cache: Path):  # noqa: ANN201
    """Load (building if stale) the graph snapshot `ack` resolves refs against."""
    from frob.graph import build_graph, load_graph

    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("ack: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.error("ack: graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    return loaded.danger_ok


def _warn_facet_informational(cfg: AppConfig) -> None:
    """Debug-log that `--facet` has no effect (facet is graph-derived), if set."""
    # NOTE: frob.graph.lock.acknowledge derives the facet per-ref from the
    # DESCRIBES edge (docs/modules/graph.md); it does not take a facet override.
    # --facet is accepted for forward-compat / documentation parity but has
    # no effect on which facet gets acked today.
    if cfg.ack_facet != "sig":
        _log.debug(
            "ack: --facet=%s is informational; facet is graph-derived", cfg.ack_facet
        )


def _load_lock_for_ack(lock_path: Path):  # noqa: ANN201
    """Load `frob.lock`, or exit(1) if it cannot be loaded."""
    from frob.graph.lock import load_lock

    lock_result = load_lock(lock_path)
    if lock_result.is_err:
        _log.error("ack: frob.lock: %s", lock_result.danger_err)
        sys.exit(1)
    return lock_result.danger_ok


def _acknowledge_and_write(cfg: AppConfig, lock, snapshot, lock_path: Path) -> None:  # noqa: ANN001
    """Acknowledge `cfg.ack_refs` against `snapshot` and persist the updated lock."""
    from frob.graph.lock import acknowledge, write_lock

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


# frob:doc docs/modules/app.md#runners
# frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
# frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_no_lease_reaches_normal_ack_failure  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_no_refs_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_success_path_builds_cache_and_writes_lock  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_unresolvable_ref_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_graph_unavailable_after_failed_build_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_malformed_lock_file_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_write_lock_failure_exits_with_error  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Load (building if the cache is stale), acknowledge refs, and write the lock.

    T-0507: refuses LOUDLY (exit 1) if `FROB_WORKTREE` names a worktree
    other than `cfg.ack_path`'s resolved root -- the same guard `frob check
    --stamp-baseline`/`--stamp-coverage` and `frob release stamp` enforce
    (T-0431/T-0507)."""
    if not cfg.ack_refs:
        _log.error("frob ack requires at least one <ref>")
        sys.exit(1)

    root = (cfg.ack_path or Path(".")).resolve()
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        _log.error("ack: worktree lease violation: %s", leased.danger_err)
        sys.exit(1)
    snapshot = _load_snapshot_for_ack(root, root / _CACHE_REL)

    lock_path = root / "frob.lock"
    lock = _load_lock_for_ack(lock_path)

    _warn_facet_informational(cfg)
    _acknowledge_and_write(cfg, lock, snapshot, lock_path)

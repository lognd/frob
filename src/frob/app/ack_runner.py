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


# frob:ticket T-1317
def _resolve_ack_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ack`'s `--reason`: `--reason-file` wins if given (read
    verbatim via `frob.app.ticket_runner._mutate.read_reason_file_verbatim`
    -- T-0737, same rationale as `frob ticket scope`'s `_resolve_scope_
    reason`, shared rather than a second fs.read capability-declaration
    site), else the inline `--reason` string. Exits 1 if both are given;
    returns `None` if neither is given (the caller reports the "one is
    required" error)."""
    from frob.app.ticket_runner._mutate import read_reason_file_verbatim

    if cfg.ack_reason_file is not None and cfg.ack_reason:
        _log.error("frob ack: --reason and --reason-file are mutually exclusive")
        sys.exit(1)
    if cfg.ack_reason_file is not None:
        return read_reason_file_verbatim(cfg.ack_reason_file, cli_label="ack")
    return cfg.ack_reason


# frob:ticket T-1317
def _print_ack_log(lock) -> None:  # noqa: ANN001
    """`frob ack --list`: render `lock.ack_log`'s append-only audit trail
    (ref, facet, digest delta, reason, actor, date) -- the surface that
    makes an ack auditable rather than a silent, unaccountable assertion.
    Routed through `frob.render.Renderer` (INV-RENDER-SOLE-STDOUT,
    docs/modules/render.md#renderer) rather than a bare `print`."""
    from frob.render import Renderer

    r = Renderer.for_stream(sys.stdout)
    if not lock.ack_log:
        r.line("frob ack --list: no acks recorded yet")
        return
    for entry in lock.ack_log:
        old = entry.old_digest[:8] if entry.old_digest is not None else "(new)"
        r.line(
            f"{entry.at} {entry.actor} {entry.ref} facet={entry.facet} "
            f"{old}->{entry.new_digest[:8]} reason={entry.reason!r}"
        )


def _acknowledge_and_write(cfg: AppConfig, lock, snapshot, lock_path: Path) -> None:  # noqa: ANN001
    """Resolve `--reason`, acknowledge `cfg.ack_refs` against `snapshot`,
    and persist the updated lock (with its new `AckAuditEntry` rows)."""
    from frob.graph.lock import acknowledge, write_lock

    reason = _resolve_ack_reason(cfg)
    if not reason:
        _log.error(
            "frob ack requires --reason TEXT or --reason-file PATH (T-1317): "
            "what was re-verified and why the doc is still true"
        )
        sys.exit(1)

    acked = acknowledge(lock, snapshot, cfg.ack_refs, reason=reason)
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
# frob:ticket T-1317
# frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
# frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_no_lease_reaches_normal_ack_failure  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_no_refs_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_success_path_builds_cache_and_writes_lock  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_unresolvable_ref_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_graph_unavailable_after_failed_build_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_malformed_lock_file_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_ack_runner.py::TestAckRunnerRun.test_write_lock_failure_exits_with_error  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_cli_requires_reason  # noqa: E501
# frob:tests tests/test_gates_drift_ack.py::TestAckAccountability.test_ack_list_renders_audit_trail  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Load (building if the cache is stale), acknowledge refs, and write the
    lock -- or, with `--list`, render the audit trail instead (T-1317).

    T-0507: refuses LOUDLY (exit 1) if `FROB_WORKTREE` names a worktree
    other than `cfg.ack_path`'s resolved root -- the same guard `frob check
    --stamp-baseline`/`--stamp-coverage` and `frob release stamp` enforce
    (T-0431/T-0507)."""
    root = (cfg.ack_path or Path(".")).resolve()
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        _log.error("ack: worktree lease violation: %s", leased.danger_err)
        sys.exit(1)

    lock_path = root / "frob.lock"
    lock = _load_lock_for_ack(lock_path)

    if cfg.ack_list:
        _print_ack_log(lock)
        return

    if not cfg.ack_refs:
        _log.error("frob ack requires at least one <ref> (or --list)")
        sys.exit(1)

    snapshot = _load_snapshot_for_ack(root, root / _CACHE_REL)
    _warn_facet_informational(cfg)
    _acknowledge_and_write(cfg, lock, snapshot, lock_path)

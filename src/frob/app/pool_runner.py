"""CLI wiring for `frob pool snapshot|clear` (T-0569): the ratchet-pool
baseline commands over `frob.gates._ratchet` -- freeze a warn-rule's
current findings so only NEW findings of that rule error, and clear a
baselined entry only with a disposition reason
(docs/modules/gates.md#ratchet-pools)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0569
def _snapshot(root: Path, cfg: AppConfig) -> None:
    """`frob pool snapshot RULE --key KEY [--key KEY ...]`: baseline every
    given key for `RULE` (T-0569)."""
    from frob.gates._ratchet import snapshot_ratchet

    if cfg.pool_rule is None or not cfg.pool_keys:
        _log.error("frob pool snapshot requires RULE and at least one --key")
        sys.exit(1)
    result = snapshot_ratchet(root, cfg.pool_rule, cfg.pool_keys)
    if result.is_err:
        _log.error("pool snapshot failed: %s", result.danger_err)
        sys.exit(1)
    pool = result.danger_ok
    _log.info(
        "%s: baseline now has %d entr(ies): %s",
        cfg.pool_rule,
        len(pool.entries),
        sorted(pool.keys),
    )


# frob:ticket T-0569
def _clear(root: Path, cfg: AppConfig) -> None:
    """`frob pool clear RULE --key KEY --reason TEXT`: remove one
    baselined entry, always with a disposition reason (T-0569)."""
    from frob.gates._ratchet import clear_ratchet_entry

    if cfg.pool_rule is None or cfg.pool_key is None or not cfg.pool_reason:
        _log.error("frob pool clear requires RULE, --key KEY, and --reason TEXT")
        sys.exit(1)
    result = clear_ratchet_entry(root, cfg.pool_rule, cfg.pool_key, cfg.pool_reason)
    if result.is_err:
        _log.error("pool clear failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s: cleared %s (%s)", cfg.pool_rule, cfg.pool_key, cfg.pool_reason)


# frob:ticket T-0569
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch to `frob pool snapshot|clear` (T-0569)."""
    root = (cfg.pool_path or Path(".")).resolve()
    if cfg.pool_command == "snapshot":
        _snapshot(root, cfg)
    elif cfg.pool_command == "clear":
        _clear(root, cfg)
    else:
        _log.error("usage: frob pool <snapshot|clear> ...")
        sys.exit(1)

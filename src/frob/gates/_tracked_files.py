"""frob.gates._tracked_files -- the one shared `git ls-files` scan helper.

T-1082 (abstraction-opportunity consolidation, T-0393/T-1067 remainder):
at least 5 gates modules (`_opaque.py`, `_exclude_hazard.py`, `_refs.py`,
`_secrets.py`, `_cve_fingerprint_scan.py`) each defined their own
byte-for-byte identical `_tracked_files(root) -> tuple[str, ...]` --
`git ls-files` under `root`, root-relative POSIX paths, degrading to `()`
on any git failure rather than raising. One shared implementation here,
parametrized only by the caller's own log-message prefix (preserved so
each gate's log output is unchanged), replaces all five.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_tracked_files.py's \
# exclusivity-vocabulary hit is source-level design-rationale prose (a \
# docstring or comment describing already-implemented internal behavior, \
# verifiable by reading the code it annotates) rather than a separate \
# cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose consolidated from \
# the five pre-T-1082 per-gate helper copies"

from __future__ import annotations

from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#git-less-target-contract-t-0705
def tracked_files(root: Path, *, caller: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, root-relative POSIX paths, `()` on any
    git failure (no repo, git missing) -- the degrade-don't-crash posture
    every gate scanning the tracked-file set already shared before this
    consolidation. `caller` is only the log-message prefix (e.g.
    `"opaque_gate"`, `"secrets_gate"`) so each gate's existing log output
    stays attributable to it, unchanged."""
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("%s: git ls-files failed: %s", caller, spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("%s: git ls-files exited %d", caller, result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())

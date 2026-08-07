"""frob.gates._fix_engine_shared -- Tier-A auto-fix infra shared by handlers.

Split out of `frob.gates._fix_engine` (T-1646, LARGE001 residue burndown)
to break what would otherwise be a circular import between the graph-
driven handler family (`frob.gates._fix_engine`) and the source-text/
line-level handler family (`frob.gates._fix_engine_text`): both files
need `FixApplied` and the crash-safe `_write_text`/manifest helpers, and
neither handler family depends on the other, so this third module is
their common ancestor rather than either importing the other's handler
code just to reach shared infra. Nothing in here is a "fix" itself --
`FixApplied` is the audit-trail record every handler returns, and the
manifest helpers are the T-1348 killed-mid-write recovery breadcrumb
`apply_tier_a_fixes` (still in `_fix_engine`) writes after every handler
call.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

from frob.tickets._store import atomic_write

_log = logging.getLogger(__name__)


# frob:ticket T-1348
def _write_text(path: Path, text: str) -> bool:
    """Crash-safe replacement for a bare `path.write_text(...)` (T-1348):
    every Tier-A handler that rewrites a file IN PLACE routes through
    this instead, so a process killed mid-write (the T-1338 incident --
    `frob ticket land` timed out during its Tier-A auto-fix phase and
    left `src/frob/gates/_debt_deprecated.py` GARBLED, a half-applied
    rewrite) leaves the ORIGINAL file intact rather than truncated. Reuses
    `frob.tickets._store.atomic_write` (temp file + fsync + `os.replace`
    in the same directory, T-0456) rather than a second copy of the same
    primitive. Returns whether the write actually landed -- callers that
    unconditionally reported `True`/appended a `FixApplied` regardless of
    this outcome would silently claim a rewrite that never happened; logs
    and leaves the original untouched on the (should-never-happen) I/O
    failure path instead of raising, matching every other handler's "no
    rewrite is better than a bad one" posture."""
    result = atomic_write(path, text)
    if result.is_err:
        _log.error(
            "tier-a fixes: atomic write to %s failed, original left untouched: %s",
            path,
            result.danger_err,
        )
        return False
    return True


# frob:ticket T-1348
def _autofix_manifest_path(root: Path) -> Path:
    """Where `write_autofix_manifest`/`clear_autofix_manifest` (T-1348)
    keep the Tier-A auto-fix recovery breadcrumb -- `.frob/` already holds
    every other local, gitignored, cross-run scratch state this repo
    keeps (baseline, cache.db, leases), so a killed-mid-autofix manifest
    lives there rather than inventing a second convention."""
    return root / ".frob" / "land-autofix-manifest.json"


# frob:ticket T-1348
# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:tests tests/test_gates.py::TestAutofixManifest.test_write_then_clear_roundtrip
def write_autofix_manifest(root: Path, applied: list[FixApplied]) -> None:
    """Record `applied`'s distinct file paths, atomically, as the T-1348
    recovery breadcrumb naming every path `apply_tier_a_fixes` has
    rewritten SO FAR in the current run. `apply_tier_a_fixes` calls this
    after every handler completes, not just once at the end, so a process
    killed mid-loop (`frob ticket land`'s pre-land Tier-A phase, T-1175)
    leaves a manifest on disk that is accurate as of the last handler that
    finished -- a recovering agent diffs `git status` against this list
    instead of a blanket `git checkout --` that can silently discard its
    own uncommitted work in some OTHER file (the exact T-1338 incident).
    A no-op write when `applied` is empty still records "a pass started
    and touched nothing yet", which is itself useful signal; the file is
    only ever removed by `clear_autofix_manifest`, on a SUCCESSFUL finish."""
    paths = sorted({entry.file for entry in applied})
    manifest = {
        "rewritten_paths": paths,
        "fix_count": len(applied),
    }
    _write_text(_autofix_manifest_path(root), json.dumps(manifest, indent=2) + "\n")


# frob:ticket T-1348
# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:tests tests/test_gates.py::TestAutofixManifest.test_write_then_clear_roundtrip
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling; the documented breadcrumb-removal behavior is unchanged, so docs/modules/tickets.md#frob-ticket-land needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def clear_autofix_manifest(root: Path) -> None:
    """Remove the T-1348 recovery breadcrumb (`write_autofix_manifest`)
    after a Tier-A auto-fix pass finishes SUCCESSFULLY -- a completed pass
    needs no recovery guidance, its rewrites are now ordinary uncommitted
    changes like any other. A missing file is not an error (nothing to
    clear, e.g. a fresh worktree that never ran Tier-A fixes yet)."""
    path = _autofix_manifest_path(root)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # A permission/locking failure clearing the breadcrumb is not
        # this function's own contract to escalate (EXHAUST001, T-1371):
        # the manifest is a best-effort recovery aid, not load-bearing
        # state -- a leftover file after a successful pass is harmless.
        _log.debug("clear_autofix_manifest: could not remove %s", path)
    except Exception:
        _log.debug("clear_autofix_manifest: could not remove %s", path)


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
class FixApplied(BaseModel):
    """One Tier-A fix `apply_tier_a_fixes` actually made: which rule it
    resolves, where, and a one-line human-readable summary of the
    rewrite -- the disclosed audit trail every fix must leave (T-1137's
    own "no silent auto-discharge" anti-goal, applied to what WAS
    auto-fixed rather than only what was left alone)."""

    model_config = {}

    rule: str
    file: str
    line: int
    detail: str

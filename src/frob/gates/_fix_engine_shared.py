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
import os
from pathlib import Path

from pydantic import BaseModel

from frob.tickets._store import atomic_write

_log = logging.getLogger(__name__)


# frob:ticket T-3526
# frob:waive PLATFORM002 reason="T-3698: this os.kill(pid, 0) is the SAME win32 \
# Ctrl+C-broadcast footgun T-3686 fixed in frob.check._pid_alive, still live here -- \
# disclosed and tracked, not silently ignored; fixing it (delegate to \
# frob.process._pid_liveness.pid_alive, the same fix T-3686 applied) is out of \
# T-3696's detector-only scope and is its own ticket"
def _pid_alive(pid: int) -> bool:
    """Whether `pid` is a live process, best-effort -- a local copy of
    `frob.check._pid_alive` (T-3256's own registry-reaping heuristic):
    `os.kill(pid, 0)` sends no signal, only probes existence. A
    permission error still means the process exists (just not ours to
    signal); any other OSError (e.g. an invalid pid) reads as dead
    rather than raising. Not imported from `frob.check` because that
    package imports `frob.graph`, which imports `frob.check._memo`, and
    `frob.gates` sits below both in this repo's own layering rule
    (`docs/rework.md`) -- importing back up would cycle, the same
    reasoning `_origin_site` in `_fix_engine.py` already documents for
    its own local copy."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


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
# frob:doc docs/modules/tickets-landing.md#frob-ticket-land
# frob:tests \
# tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_write_then_clear_round\
# trip
def write_autofix_manifest(root: Path, applied: list[FixApplied]) -> None:
    """Record `applied`'s distinct file paths, atomically, as the T-1348
    recovery breadcrumb naming every path `apply_tier_a_fixes` has
    rewritten SO FAR in the current run. `apply_tier_a_fixes` calls this
    BEFORE the first handler runs (an empty `applied`, T-3526 -- see
    `AutofixManifest`'s own docstring for why a pre-first-mutation write
    is required, not merely an optimization) and again after every
    handler completes, so a process killed at ANY point in the loop
    (`frob ticket land`'s pre-land Tier-A phase, T-1175, or a bare `frob
    check --fix`) leaves a manifest on disk that is accurate as of the
    last handler that finished -- a recovering agent diffs `git status`
    against this list instead of a blanket `git checkout --` that can
    silently discard its own uncommitted work in some OTHER file (the
    exact T-1338 incident). T-3526: also records `os.getpid()`, so
    `read_abandoned_autofix_manifest` can tell "a DIFFERENT, still-live
    `--fix` process owns this journal" (not abandoned) from "the process
    that wrote this is gone" (abandoned) rather than treating every
    manifest found mid-run as abandoned. The file is only ever removed by
    `clear_autofix_manifest`, on a SUCCESSFUL finish."""
    paths = sorted({entry.file for entry in applied})
    manifest = {
        "rewritten_paths": paths,
        "fix_count": len(applied),
        "pid": os.getpid(),
    }
    _write_text(_autofix_manifest_path(root), json.dumps(manifest, indent=2) + "\n")


# frob:ticket T-1348
# frob:doc docs/modules/tickets-landing.md#frob-ticket-land
# frob:tests \
# tests/gates_suite/test_fix_engine.py::TestAutofixManifest.test_write_then_clear_round\
# trip
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling; the documented breadcrumb-removal behavior is unchanged, so docs/modules/tickets-landing.md#frob-ticket-land needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
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


# frob:ticket T-3526
# frob:tests tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal.test_dead_pid_manifest_is_abandoned kind="unit"  # noqa: E501
# frob:waive COV001 reason="this model is a plain data-carrier for \
# read_abandoned_autofix_manifest's own return value, three fields already fully \
# described by its own docstring (rewritten_paths/fix_count/pid); the natural anchor \
# is docs/modules/gates.md's existing \
# --fix-tier-a-deterministic-auto-fix-handlers-t-1138 section, but that file is under \
# a concurrent T-3492 lease this ticket cannot take, so even a no-op touch is blocked \
# -- filed as a disclosed gap (T-3534), same T-1371/T-1372/T-2466 precedent \
# src/frob/gates/_wire.py already carries elsewhere"
class AutofixManifest(BaseModel):
    """An abandoned T-1348 autofix journal `read_abandoned_autofix_manifest`
    found on disk: `apply_tier_a_fixes` was killed (or otherwise never
    reached `clear_autofix_manifest`) partway through a Tier-A rewrite
    pass, and the process that wrote it (`pid`) is no longer alive."""

    model_config = {}

    rewritten_paths: tuple[str, ...] = ()
    fix_count: int = 0
    pid: int | None = None


# frob:ticket T-3526
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal.test_dead_pid_mani\
# fest_is_abandoned kind="unit"
# frob:tests \
# tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal.test_live_pid_mani\
# fest_is_not_abandoned kind="unit"
# frob:tests \
# tests/unit/test_fix_engine_journal.py::TestAbandonedAutofixJournal.test_absent_manife\
# st_is_not_abandoned kind="unit"
def read_abandoned_autofix_manifest(root: Path) -> AutofixManifest | None:
    """`None` if there is no T-1348 autofix journal at all
    (`_autofix_manifest_path`), or if there is one but its `pid` is a
    still-live process (`_pid_alive`) -- a concurrently RUNNING `--fix`
    pass in another process, not an abandoned one. Otherwise (the file
    exists and its `pid` is dead, missing, or the JSON itself is
    unparseable/malformed) returns the `AutofixManifest` describing the
    abandoned state: this is the T-3526 fix for the incident this
    module's own docstring links to -- a killed `frob check --fix`/pre-
    land Tier-A pass used to leave files half-rewritten with no marker
    at all distinguishing that from an operator's own uncommitted edits.
    A malformed/unreadable journal (partial write mid-crash, or hand-
    edited) is conservatively treated as abandoned too -- `pid=None`,
    empty `rewritten_paths` -- rather than silently ignored, since an
    unparseable journal is itself exactly the "dirty, undetectable-by-
    normal-means state" this function exists to surface loudly."""
    path = _autofix_manifest_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        _log.warning("autofix journal at %s exists but is unreadable", path)
        return AutofixManifest()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _log.warning("autofix journal at %s is malformed JSON", path)
        return AutofixManifest()
    pid = data.get("pid")
    if isinstance(pid, int) and _pid_alive(pid):
        return None
    return AutofixManifest(
        rewritten_paths=tuple(data.get("rewritten_paths", ()) or ()),
        fix_count=int(data.get("fix_count", 0) or 0),
        pid=pid if isinstance(pid, int) else None,
    )


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

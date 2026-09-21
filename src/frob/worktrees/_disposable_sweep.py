"""frob.worktrees._disposable_sweep -- sweep leaked disposable `git worktree
add` scratch dirs (T-4437, F-055 class).

MEASURED 2026-09-12 (this ticket's own repro): `git worktree list` in this
checkout accumulated 9 leaked `/tmp/frob-bug002-*/wt` worktrees (BUG002
repro, `frob.gates._bug_repro`) and 3 leaked `/tmp/frob-land-squash-*`
worktrees (`frob.tickets._land_compose`'s squash-and-splice pipeline) --
both pipelines clean their own scratch dir up on the happy path (a
`finally`/`with tempfile.TemporaryDirectory`), but neither survives a
SIGKILL mid-run (a killed land, a killed check run): SIGKILL runs no
Python cleanup code, so the `git worktree add` registration and the
scratch directory both survive the process that made them, and nothing
else ever revisits them -- `frob doctor`/`frob clean` never looked here.

This module is the sweep. It only ever touches paths matching
`DISPOSABLE_WORKTREE_GLOBS` under a scan root (default `/tmp`, overridable
for tests) -- it never touches `.claude/worktrees/<ticket>` agent
worktrees, which are `frob.tickets._worktree_sweep`'s own, unrelated,
lease-aware concern.

Liveness is decided by `OWNER_PID_FILENAME`, a plain text file the two
creator call sites (`frob.gates._bug_repro`, `frob.tickets._land_compose`)
now write via `stamp_owner_pid` right after `git worktree add` succeeds
(T-4437 acceptance criterion 2): a scratch dir with no stamp, or a stamp
naming a dead pid, is dead by definition (a live creator process would
have removed it itself on any normal exit path). A stamp naming a LIVE
pid is left alone -- the creator might just be slow, not gone."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from pydantic import BaseModel

import frob.gitio as gitio
from frob.logging import get_logger

_log = get_logger(__name__)

#: T-4437: the two disposable-worktree shapes this sweep knows about --
#: `frob.gates._bug_repro`'s BUG002 repro scratch dirs and `frob.tickets.
#: _land_compose`'s land-squash scratch dirs. Each scratch dir holds its
#: actual `git worktree add` target one level down, at `<scratch>/wt`.
DISPOSABLE_WORKTREE_GLOBS: tuple[str, ...] = (
    "frob-bug002-*",
    "frob-land-squash-*",
)

#: T-4437: the file a creator stamps its own pid into, at `<scratch>/
#: OWNER_PID_FILENAME`, immediately after `git worktree add` succeeds --
#: read back by `_owner_pid_is_dead` to decide whether a leaked scratch
#: dir's creator is actually gone.
OWNER_PID_FILENAME = ".frob-owner-pid"


# frob:doc docs/modules/clean.md#frob-clean---sweep-disposable-worktrees-t-4437
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_dead_stamped_worktree_is_removed  # noqa: E501
class DisposableWorktreeEntry(BaseModel):
    """One disposable scratch dir this sweep looked at (T-4437): its
    `scratch` root, the nested `worktree` path (`scratch/wt`, may not
    exist if the creator died before `git worktree add` ran), whether it
    was judged dead, and why -- rendered verbatim in `frob clean`'s
    `--sweep-disposable-worktrees` report."""

    scratch: Path
    worktree: Path
    owner_pid: int | None
    dead: bool
    reason: str


# frob:doc docs/modules/clean.md#frob-clean---sweep-disposable-worktrees-t-4437
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_dry_run_reports_without_removing  # noqa: E501
class DisposableSweepReport(BaseModel):
    """The result of one `sweep_disposable_worktrees` call (T-4437):
    every scratch dir it looked at, split into `removed` (dead, and
    `execute=True` was passed) and `kept` (either alive, or `execute=
    False`, a dry-run preview)."""

    removed: tuple[DisposableWorktreeEntry, ...]
    kept: tuple[DisposableWorktreeEntry, ...]


# frob:doc docs/modules/clean.md#frob-clean---sweep-disposable-worktrees-t-4437
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestStampOwnerPid.test_writes_current_pid  # noqa: E501
def stamp_owner_pid(scratch: Path) -> None:
    """Write the CURRENT process's pid into `scratch/OWNER_PID_FILENAME`
    (T-4437 acceptance criterion 2). Called by a disposable-worktree
    creator (`frob.gates._bug_repro`, `frob.tickets._land_compose`)
    immediately after `git worktree add` succeeds, so a later sweep can
    tell a leaked scratch dir's creator is actually dead rather than just
    slow. Best-effort: a write failure (e.g. a read-only `/tmp`) is logged
    and swallowed -- the worst case is this scratch dir falls back to the
    same "no stamp -> treat as dead" rule it had before this ticket, not a
    crash of the pipeline that made it."""
    try:
        (scratch / OWNER_PID_FILENAME).write_text(str(os.getpid()))
    except OSError as exc:
        _log.warning("worktrees: could not stamp owner pid onto %s: %s", scratch, exc)


def _read_owner_pid(scratch: Path) -> int | None:
    """The pid `stamp_owner_pid` recorded for `scratch`, or `None` if no
    stamp exists (a pre-T-4437 leak, or a creator that died before it
    could stamp)."""
    stamp = scratch / OWNER_PID_FILENAME
    try:
        return int(stamp.read_text().strip())
    except (OSError, ValueError):
        return None


def _pid_is_alive(pid: int) -> bool:
    """`True` iff `pid` names a currently-running process (the standard
    `os.kill(pid, 0)` liveness probe, no signal actually sent)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # T-4437: a live pid owned by another user still answers with
        # EPERM, not ESRCH -- that IS aliveness, just not one we can
        # signal, so treat it as alive rather than dead.
        return True
    return True


def _classify_scratch_dir(scratch: Path) -> DisposableWorktreeEntry:
    """Judge one candidate `scratch` dir dead or alive (T-4437): dead iff
    it has no owner-pid stamp (nothing left to be alive) or the stamped
    pid is no longer running."""
    worktree = scratch / "wt"
    owner_pid = _read_owner_pid(scratch)
    if owner_pid is None:
        return DisposableWorktreeEntry(
            scratch=scratch,
            worktree=worktree,
            owner_pid=None,
            dead=True,
            reason="no owner-pid stamp (pre-T-4437 leak or creator died before "
            "stamping) -- nothing left to be alive",
        )
    if _pid_is_alive(owner_pid):
        return DisposableWorktreeEntry(
            scratch=scratch,
            worktree=worktree,
            owner_pid=owner_pid,
            dead=False,
            reason=f"owner pid {owner_pid} is still running",
        )
    return DisposableWorktreeEntry(
        scratch=scratch,
        worktree=worktree,
        owner_pid=owner_pid,
        dead=True,
        reason=f"owner pid {owner_pid} is no longer running",
    )


def _remove_disposable_worktree(
    repo_root: Path, entry: DisposableWorktreeEntry
) -> None:
    """Actually remove `entry` (T-4437 acceptance criterion 1):
    `git worktree remove --force` on the nested worktree (if `git` still
    knows about it), `git worktree prune` to drop any remaining
    registration, then `shutil.rmtree` the scratch dir itself. Each step
    is best-effort in isolation -- a missing/already-gone worktree must
    not stop the scratch dir from still being deleted."""
    if entry.worktree.exists():
        result = gitio.run_argv(
            (
                "git",
                "-C",
                str(repo_root),
                "worktree",
                "remove",
                "--force",
                str(entry.worktree),
            )
        )
        if result.is_err:
            _log.warning(
                "worktrees: git worktree remove --force %s failed: %s",
                entry.worktree,
                result.danger_err,
            )
    gitio.run_argv(("git", "-C", str(repo_root), "worktree", "prune"))
    shutil.rmtree(entry.scratch, ignore_errors=True)


# frob:ticket T-4437
# frob:doc docs/modules/clean.md#frob-clean---sweep-disposable-worktrees-t-4437
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_dead_stamped_worktree_is_removed  # noqa: E501
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_live_stamped_worktree_is_kept  # noqa: E501
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_unstamped_worktree_is_removed  # noqa: E501
# frob:tests tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees.test_dry_run_reports_without_removing  # noqa: E501
def sweep_disposable_worktrees(
    repo_root: Path,
    *,
    execute: bool,
    scan_root: Path | None = None,
) -> DisposableSweepReport:
    """Find every scratch dir under `scan_root` (default `tempfile.
    gettempdir()`, overridable for tests) matching `DISPOSABLE_WORKTREE_
    GLOBS`, classify each dead/alive via its owner-pid stamp, and -- when
    `execute` is `True` -- remove the dead ones with `git worktree remove
    --force` + `git worktree prune` against `repo_root` (T-4437
    acceptance criteria 1/3). `execute=False` is a dry-run preview: every
    dead candidate is reported in `removed` but nothing is deleted."""
    base = scan_root if scan_root is not None else Path(tempfile.gettempdir())
    removed: list[DisposableWorktreeEntry] = []
    kept: list[DisposableWorktreeEntry] = []
    for glob in DISPOSABLE_WORKTREE_GLOBS:
        for scratch in sorted(base.glob(glob)):
            if not scratch.is_dir():
                continue
            entry = _classify_scratch_dir(scratch)
            if not entry.dead:
                kept.append(entry)
                continue
            if execute:
                _remove_disposable_worktree(repo_root, entry)
            removed.append(entry)
    return DisposableSweepReport(removed=tuple(removed), kept=tuple(kept))

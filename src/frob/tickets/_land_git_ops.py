"""`frob ticket land` -- git-plumbing/wip-commit machinery.

See docs/modules/tickets-landing.md#frob-ticket-land.

Split out of `frob.tickets._land_merge` (T-1251, continuing the verbatim-
move discipline T-1186/T-1189/T-1192/T-1194 established): the git-plumbing
and wip-commit family -- main-into-worktree merge staging
(`_merge_main_into_worktree`), out-of-scope conflict auto-resolution
(`_auto_resolve_out_of_scope_conflicts`), the wip-commit trio
(`_wip_commit`/`_wip_add_excluding_frob`/`_do_wip_commit`), ledger/archive
splice-and-stage (`_splice_and_stage`/`_splice_and_stage_archive`,
`_verify_archive_merge`), the deletion-authorization pair
(`_deletion_glob_too_broad`/`_deletion_owned`, moved alongside
`_unowned_deletions` which uses them, per T-1251's own residue note), the
`frob:waive`-deletion laundering guards (T-1323/T-1326), and the small git
primitives this family shares (`_rev_parse`, `_true_merge_base`,
`_land_internal_git_env`, `_describe_git_failure`,
`_is_ignored_path_refusal`, `_verified_reset_root`, `_porcelain_dirty`,
`_diff_is_frob_version_line_only`, `_restore_lock_version_only_drift`,
`_conflicted_files`, `_abort_merge`, `_archived_ids`). Zero caller-visible
behavior change -- every moved function keeps its original body, docstring,
and `frob:ticket`/`frob:tests` directives verbatim; `frob.tickets._land_merge`
and `frob.tickets._land_finalize` import what they still need back from
here.

`_land_merge.py` keeps the closeability-validation family
(`_validate_closeable`/`_validate_acceptance_bound`/
`_validate_evidence_kind_consistency`) and the commit-message helper
(`_commit_message`), plus its re-export of `splice_ledger` for
`frob.tickets.__init__`'s stable public import path.
"""
# frob:waive LARGE001 reason="T-1251 verbatim extraction seam: 1063 lines is the moved \
# git-plumbing family intact, one seam per land; the follow-on split of this family \
# (and _land_finalize.py's) is the T-1251-residue draft ticket filed at close -- \
# waived rather than force-split in the same diff to preserve the byte-identical-move \
# review guarantee"

from __future__ import annotations

import fnmatch
import importlib
import json
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._land_ledger_merge import (
    _merge_ledger_tickets,
    _splice_only_ticket,
    splice_ledger,
)
from frob.tickets._land_merge_zones import (
    _resolve_union_zone_conflicts,
    _zone_for_path,
)
from frob.tickets._leases import LAND_LOCK_REL
from frob.tickets._models import (
    LandError,
    Ticket,
    TicketError,
    _done_report_section_lines,
    scope_matches,
)
from frob.tickets._store import (
    _check_ledger_id_integrity,
    _parse_ledger,
    _render_ledger,
    archive_path,
    ledger_path,
)

_log = get_logger(__name__)

# T-2157: same posix-only degradation as `frob.tickets._land`'s own
# `_land_lock` -- see `reclaim_orphaned_squash_residue`'s docstring for why
# this module reads (never writes) that module's `LAND_LOCK_REL` constant
# instead of inventing a second lock file.
_fcntl: ModuleType | None
try:
    _fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    _fcntl = None


@contextmanager
def _land_internal_git_env() -> Iterator[None]:
    """Set `FROB_LAND_INTERNAL=1` in the process environment for the
    duration of a land-internal git commit spawn (T-0828). The T-0731
    scaffolded `pre-commit` hook refuses a worktree/main commit that
    touches a land-owned file (CHANGELOG.md, uv.lock, pyproject.toml's
    version line) unless this is set -- `land()`'s OWN commits (the
    worktree wip snapshot, the main-into-worktree merge commit, the
    finalize/close commit, and the main-side squash-apply commit, which
    can legitimately carry a REL001 version bump + generated changelog
    entry) must set it around every one of those spawns or the hook
    deadlocks land against itself. Restores the prior value (or absence)
    of the variable on exit rather than leaking it into unrelated spawns
    this process makes afterward."""
    # frob:waive SEC110 reason="internal reentrancy marker, not a secret"
    prior = os.environ.get("FROB_LAND_INTERNAL")
    # frob:waive SEC110 reason="internal reentrancy marker, not a secret"
    os.environ["FROB_LAND_INTERNAL"] = "1"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("FROB_LAND_INTERNAL", None)
        else:
            # frob:waive SEC110 reason="restoring reentrancy marker, not a secret"
            os.environ["FROB_LAND_INTERNAL"] = prior


def _describe_git_failure(argv: Sequence[str], spawned: Result[Any, Any]) -> str:
    """A one-line, diagnosable description of a failed `run_argv` spawn --
    the failing argv plus its stderr (or the spawn-level error if the
    process never even completed) -- so a hook-class refusal (e.g. the
    T-0731 pre-commit guard) is readable from a single log line instead of
    collapsing to a bare `GitFailed` with no context (T-0828)."""
    rendered_argv = " ".join(str(a) for a in argv)
    if spawned.is_err:
        return f"git {rendered_argv} -- spawn error: {spawned.danger_err}"
    result = spawned.danger_ok
    stderr = str(getattr(result, "stderr", "")).strip() or "(no stderr)"
    returncode = getattr(result, "returncode", "?")
    return f"git {rendered_argv} -- exit {returncode}: {stderr}"


# frob:ticket T-1184
def _is_ignored_path_refusal(stderr: str) -> bool:
    """Whether a failed `git add` spawn's stderr is git's "explicitly named
    an ignored path" refusal (T-1184) -- narrowly matched on
    git's own fixed message text so `_do_wip_commit`'s fallback only
    triggers on this exact known failure mode, never masking a genuinely
    different `git add` error as if it were this one."""
    return "ignored by one of your .gitignore files" in stderr


# frob:ticket T-1740
def _unstage_index_only(root: Path) -> Result[None, LandError]:
    """`git reset` (bare, mixed, no target -- defaults to `HEAD`) in
    `root`: clears the INDEX back to matching whatever `root`'s CURRENT
    `HEAD` is, without moving `HEAD` and without touching a single
    working-tree file's content (T-1740).

    This is the "unstage what land staged" primitive `_verified_reset_
    root`'s drift branch was missing (the 2026-08-07 incident: a refused
    `land T-1688` left 14 files staged in root's index -- including
    `_worker.py` and its tests -- with no cleanup at all, and the next
    bare `git commit` anywhere in `root`, run by a human unaware of the
    leftover state, published them under an unrelated message). Safe to
    call even when `root`'s tip has drifted from this run's own `pre_
    land_tip` (the exact case `_verified_reset_root` refuses to `reset
    --hard` for, since a hard reset there could destroy the concurrent
    commit that caused the drift) -- unstaging never touches commits or
    tracked file bytes, only the index, so it cannot destroy anything a
    concurrent write already committed."""
    reset = run_argv(["git", "-C", str(root), "reset"])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-0907
# frob:ticket T-1740
def _refuse_drift_but_unstage(
    root: Path, pre_land_tip: str, current_tip: str, ticket_id: str
) -> LandError:
    """`_verified_reset_root`'s drift-detected branch (T-1740, split out
    to keep that function under the ARCH001 line threshold): unstages
    (`_unstage_index_only`, best-effort -- its own failure only logs, it
    never masks the drift refusal itself) before refusing, so land's own
    staged squash content can never ride into someone else's next `git
    commit` (the 2026-08-07 T-1688 incident) even though a full `reset
    --hard` here is unsafe (it could destroy the concurrent commit that
    caused the drift). Always returns `LandError.GitFailed`."""
    unstaged = _unstage_index_only(root)
    if unstaged.is_err:
        _log.warning(
            "land: %s could not unstage %s's index after detecting drift "
            "(%s) -- staged content may still be present",
            ticket_id,
            root,
            unstaged.danger_err,
        )
    # Name exactly what this refusal leaves behind, rather than a bare
    # pointer to "inspect by hand" -- a prior incident this same
    # disclosure practice already closed once left four files staged
    # with no disclosure of WHICH ones, so the operator had to discover
    # them via a separate `git status` before they could even start
    # cleaning up. T-1740: by this point the index has already been
    # unstaged above, so `leftover_lines` here reports WORKING-TREE
    # state only -- genuinely nothing left staged.
    leftover = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    leftover_lines = (
        [line for line in leftover.danger_ok.stdout.splitlines() if line.strip()]
        if leftover.is_ok and leftover.danger_ok.returncode == 0
        else []
    )
    _log.error(
        "land: %s refused to unwind %s -- current tip is %s but this "
        "run's recorded pre-land tip is %s (drift detected mid-staging, "
        "T-0907) -- NOT hard-resetting (a blind reset here could destroy "
        "the concurrent commit that caused the drift), but the INDEX has "
        "been unstaged (T-1740) so nothing land itself staged can ride "
        "into someone else's next commit; inspect `git -C %s reflog` and "
        "`git -C %s log --oneline -5` by hand before retrying. "
        "Working-tree state remaining in %s (%d path(s), index already "
        "clear): %s",
        ticket_id,
        root,
        current_tip,
        pre_land_tip,
        root,
        root,
        root,
        len(leftover_lines),
        ", ".join(leftover_lines)
        if leftover_lines
        else "(could not list -- run `git status` by hand)",
    )
    return LandError.GitFailed


def _verified_reset_root(
    root: Path, pre_land_tip: str, ticket_id: str
) -> Result[None, LandError]:
    """Unwind `root`'s staged squash-apply back to `pre_land_tip` -- the
    T-0907 replacement for a bare `git reset --hard` (which resolves its
    target from whatever `HEAD` happens to be AT RESET TIME, the exact
    hazard the incident this ticket fixes exploited): resets to an
    EXPLICIT sha captured once at this run's start, and refuses loudly
    (`Err(GitFailed)`) if `root`'s current tip has already drifted from
    `pre_land_tip` by the time this runs -- root's tip must never move
    between this run's start and its own final commit
    (`_commit_squash_apply`), so any drift here means something else
    touched `root` mid-run and blindly `reset --hard`-ing over it would
    risk exactly the T-0907 incident class.

    T-1740: the drift case still UNSTAGES before refusing
    (`_refuse_drift_but_unstage`) -- a refusal that leaves land's own
    staged squash content sitting in the index is not a refusal, it is a
    partial apply with an error message."""
    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)
    if current.danger_ok != pre_land_tip:
        return Err(
            _refuse_drift_but_unstage(root, pre_land_tip, current.danger_ok, ticket_id)
        )
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", pre_land_tip])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-2157
# frob:ticket T-2170
# frob:doc \
# docs/design/land-checkpoint-durability.md#reclaim_orphaned_squash_residue-t-2157t-2170
# frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_reclaims_when_no_live_land_holds_the_lock  # noqa: E501
# frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_does_not_touch_a_live_lands_own_staging  # noqa: E501
# frob:tests \
# tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test\
# _clean_root_is_a_no_op
# frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup.test_land_calls_reclaim_before_acquiring_its_own_lock  # noqa: E501
# frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup.test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal  # noqa: E501
def reclaim_orphaned_squash_residue(
    root: Path, ticket_id: str
) -> Result[bool, LandError]:
    """Safely unwind a SIGKILL-orphaned squash-merge staged in `root`'s real
    index/working tree -- the T-2157 fix for the DirtyMain trap a killed
    land used to leave behind with no safe recovery short of a coordinator
    manually checking `/proc` for the holder pid.

    Every squash-merge onto `root` (`_squash_and_splice_ledger[_v2]`,
    `_land_plan_merge_worktree`) runs strictly inside `frob.tickets._land.
    _land_lock`'s critical section for the WHOLE window between staging and
    the final commit -- so a NON-BLOCKING, exclusive `flock` on that exact
    lock file (`LAND_LOCK_REL`, read here from `frob.tickets._leases` --
    the single home T-1619 already established for this path, never a
    second copy) either:

    - SUCCEEDS, which proves no live land process currently holds it, which
      in turn proves any staged-but-uncommitted content sitting in `root`'s
      index right now belongs to a process that died without releasing the
      lock cleanly (the kernel frees an `flock` the instant its holder
      exits, SIGKILL included -- `_land_lock`'s own docstring, T-1515) --
      i.e. PROVABLY orphaned, never a guess from a recorded pid (pid reuse
      makes a bare pid comparison unsafe in both directions: a dead land's
      pid can later be reused by an unrelated live process, and this
      process never even records or compares one).
    - FAILS, which means a land is genuinely in flight holding the lock
      right now -- this returns `Ok(False)` and touches NOTHING, per this
      ticket's explicit constraint against a later land blindly `git
      reset`-ing residue it cannot tell apart from a live concurrent land's
      own staging.

    Returns `Ok(True)` only in the orphan case (root was dirty, the lock
    was free, and the reset+clean via `_verified_reset_root` succeeded).
    `Ok(False)` covers both "nothing to do" (`root` was already clean) and
    "a live land holds the lock" (nothing to do YET, not an error). `Err`
    only on a genuine git failure during the reset/clean itself.

    Degrades to a documented no-op (`Ok(False)`, logged at WARNING) on a
    platform without `fcntl`, matching `_land_lock`'s own degradation --
    without a real `flock`, this module cannot safely tell a live land's
    staging apart from orphaned residue, so it must refuse to touch `root`
    rather than guess.

    T-2170: `frob.tickets._land.land()` now calls this at the very top of
    its own body -- BEFORE it acquires its own `_land_lock` -- so a dead
    land's orphaned residue is reclaimed automatically at the start of the
    next land attempt, ahead of `_refuse_if_main_dirty`'s own DirtyMain
    check. Prior to T-2170 this function was correct, tested, and had
    ZERO production callers; the fleet-blocking trap it exists to close
    (a killed land's staged residue silently refusing every other agent's
    land until a human clears it by hand) was only closed by this wiring,
    not by the primitive's own existence."""
    dirty = _porcelain_dirty(root)
    if dirty.is_err:
        return Err(dirty.danger_err)
    if not dirty.danger_ok:
        return Ok(False)
    if _fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "land: %s reclaim_orphaned_squash_residue: fcntl unavailable on "
            "this platform -- cannot safely distinguish a live land's own "
            "staging from orphaned residue in %s, refusing to touch it",
            ticket_id,
            root,
        )
        return Ok(False)
    return _reclaim_via_land_lock_probe(root, ticket_id)


def _reclaim_via_land_lock_probe(root: Path, ticket_id: str) -> Result[bool, LandError]:
    """The lock-acquire-then-reset half of `reclaim_orphaned_squash_residue`,
    split out to keep that function's own decision-point count under
    ARCH001/ARCH103's threshold -- pure extraction, no behavior change.
    Assumes `root` is already known dirty and `_fcntl` is available; the
    caller (`reclaim_orphaned_squash_residue`) checks both first."""
    assert _fcntl is not None  # narrows for the type checker; caller already checked
    lock_path = root / LAND_LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
    except OSError:
        _log.warning(
            "land: %s root %s has staged/dirty content but land.lock is "
            "currently HELD by a live process -- this is a live land's own "
            "staging, not orphaned residue; leaving it untouched",
            ticket_id,
            root,
        )
        os.close(fd)
        return Ok(False)
    try:
        return _reset_orphaned_residue_under_lock(root, ticket_id)
    finally:
        _fcntl.flock(fd, _fcntl.LOCK_UN)
        os.close(fd)


def _reset_orphaned_residue_under_lock(
    root: Path, ticket_id: str
) -> Result[bool, LandError]:
    """The actual reset+clean, run only once `_reclaim_via_land_lock_probe`
    has proven `land.lock` is free -- split out for the same ARCH103
    reason as its caller."""
    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)
    pre_land_tip = current.danger_ok
    _log.warning(
        "land: %s reclaiming orphaned squash-merge residue in %s -- "
        "land.lock was free (no live land process holds it) while "
        "root's index/working tree carried uncommitted content; "
        "resetting to HEAD (%s) and cleaning untracked files",
        ticket_id,
        root,
        pre_land_tip,
    )
    reset = _verified_reset_root(root, pre_land_tip, ticket_id)
    if reset.is_err:
        return Err(reset.danger_err)
    return Ok(True)


def _porcelain_dirty(root: Path) -> Result[bool, LandError]:
    """Whether `root`'s working tree has any uncommitted change (tracked or
    not), ignoring `.frob/` (T-0577): `land`'s own `ledger_lock` creates
    `.frob/tickets.lock` in `root` BEFORE this check ever runs (the whole
    `land()` body, `_refuse_if_main_dirty` included, now runs under that
    lock -- see `land`'s docstring), and `.frob/` is frob-local scratch
    state a repo is expected to `.gitignore` anyway (baseline/coverage
    stamps, journal records, this same lock file) -- never a real
    "uncommitted change" a landing should refuse on."""
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.error("land: git status failed in %s", root)
        return Err(LandError.GitFailed)
    dirty_lines = [
        line
        for line in spawned.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    return Ok(bool(dirty_lines))


# frob:ticket T-1698
_DIRTY_PATHS_SHOWN = 10


# frob:ticket T-1698
def _porcelain_dirty_paths(root: Path) -> tuple[str, ...]:
    """The paths making `root` dirty, by the SAME `.frob/`-ignoring rule
    `_porcelain_dirty` decides on -- so what a DirtyMain refusal names can
    never disagree with what made it refuse.

    Exists because `DirtyMain` used to say only "root has uncommitted
    changes" (T-1698): during a three-agent wave, one uncommitted
    one-line file deadlocked every land in the repo, and three agents each
    burned minutes without ever learning which file it was. An error that
    does not name its own cause is a structural defect in a tool whose job
    is enforcement. Empty tuple on a git failure -- the caller has already
    reported that separately and must not turn "cannot tell" into "clean".
    """
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    return tuple(
        line[3:].strip()
        for line in spawned.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    )


# frob:ticket T-1740
def _porcelain_dirty_paths_staged(root: Path) -> tuple[str, ...]:
    """The SUBSET of `_porcelain_dirty_paths(root)` that is STAGED (`git
    status --porcelain`'s first/index column is non-blank/non-`?`) --
    T-1740's distinction: a `DirtyMain` refusal that says only
    "uncommitted changes" reads as working-tree edits and sent an agent
    looking for the wrong thing when the real cause was a PRIOR land's
    leftover staged squash content (`_verified_reset_root`'s drift path).
    Same `.frob/`-ignoring rule and same best-effort-empty-on-git-failure
    posture as `_porcelain_dirty_paths`."""
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    staged: list[str] = []
    for line in spawned.danger_ok.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if path.startswith(".frob/"):
            continue
        index_status = line[0]
        if index_status not in (" ", "?"):
            staged.append(path)
    return tuple(staged)


# frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_paths
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_truncation_declares_itself
# frob:ticket T-1698
def _render_dirty_paths(paths: tuple[str, ...]) -> str:
    """`paths` rendered for a refusal message, capped at
    `_DIRTY_PATHS_SHOWN` with an explicit `(+N more)` -- a truncated list
    that hides its own truncation would send someone to fix one file when
    twenty are dirty."""
    if not paths:
        return "(git status unavailable)"
    shown = ", ".join(paths[:_DIRTY_PATHS_SHOWN])
    extra = len(paths) - _DIRTY_PATHS_SHOWN
    return f"{shown} (+{extra} more)" if extra > 0 else shown


# frob:ticket T-0793
_LOCK_VERSION_LINE = re.compile(r'^[+-]version = "[^"]*"$')


# frob:ticket T-0793
def _diff_is_frob_version_line_only(diff_text: str) -> bool:
    """Whether a unified `git diff` body touches nothing but a single
    `version = "..."` line flip (one removed, one added) inside the
    `name = "frob"` package stanza -- the shape uv.lock's own frob-
    version line takes on every `uv run`/`uv lock` against a pyproject
    whose version was just bumped by a sibling land, with no other lock
    content changed. Used to gate the DirtyMain auto-restore (T-0793) so
    a REAL lock drift (a dependency actually changed) still refuses
    normally instead of being silently discarded."""
    changed = [
        line
        for line in diff_text.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    if len(changed) != 2:
        return False
    if not all(_LOCK_VERSION_LINE.match(line) for line in changed):
        return False
    return 'name = "frob"' in diff_text


# frob:ticket T-0793
def _restore_lock_version_only_drift(root: Path) -> bool:
    """Auto-restore `root`'s `uv.lock` (T-0793) when the ONLY uncommitted
    change in the whole tree is uv.lock's frob-version line flapping on
    every `uv run` against a pyproject bumped by a prior land -- left
    alone, this alone trips `_refuse_if_main_dirty`'s DirtyMain refusal
    on every subsequent land attempt until someone runs `git checkout --
    uv.lock` by hand first (the recurring friction this ticket exists to
    kill). Returns `True` (and restores the file, clearing the drift)
    only when `uv.lock` is the SOLE dirty path AND its diff is exactly
    the version-line-only shape `_diff_is_frob_version_line_only` checks
    for; any other drift (a real lock change, a second dirty file) is
    left completely untouched and this returns `False` so the ordinary
    DirtyMain refusal still fires unchanged."""
    status = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if status.is_err or status.danger_ok.returncode != 0:
        return False
    dirty_lines = [
        line
        for line in status.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    if len(dirty_lines) != 1 or dirty_lines[0][3:].strip() != "uv.lock":
        return False
    diff = run_argv(["git", "-C", str(root), "diff", "--", "uv.lock"])
    if diff.is_err or diff.danger_ok.returncode != 0:
        return False
    if not _diff_is_frob_version_line_only(diff.danger_ok.stdout):
        return False
    restored = run_argv(["git", "-C", str(root), "checkout", "--", "uv.lock"])
    return restored.is_ok and restored.danger_ok.returncode == 0


# frob:ticket T-1699
def _commit_rapid_debt_only_drift(root: Path) -> bool:
    """Auto-commit `root`'s `rapid-debt.jsonl` (T-1699) when it is the
    SOLE dirty path -- the race `_commit_rapid_debt`
    (`frob.app.ticket_runner._rapid_sweep`) leaves open: a rapid land
    appends its debt line and commits it in two separate steps with no
    lock held across them (T-1684 deliberately keeps the post-land phase
    OUTSIDE the land lock), so a second agent's land can observe root
    dirty with exactly that one line between the append and the commit.
    Unlike `_restore_lock_version_only_drift`'s uv.lock precedent, this
    content is real and wanted -- it is COMMITTED, never discarded, since
    any land-owned `rapid-debt.jsonl` append is always safe and correct
    to commit on its own (`_commit_rapid_debt`'s own contract: stages and
    commits that one file, nothing else). Returns `True` (and commits)
    only when `rapid-debt.jsonl` is the SOLE dirty path; any other drift
    (a second dirty file, or `rapid-debt.jsonl` alongside anything else)
    is left completely untouched and this returns `False` so the
    ordinary DirtyMain refusal still fires unchanged."""
    status = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if status.is_err or status.danger_ok.returncode != 0:
        return False
    dirty_lines = [
        line
        for line in status.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    if len(dirty_lines) != 1 or dirty_lines[0][3:].strip() != "rapid-debt.jsonl":
        return False
    staged = run_argv(["git", "-C", str(root), "add", "--", "rapid-debt.jsonl"])
    if staged.is_err or staged.danger_ok.returncode != 0:
        return False
    committed = run_argv(
        [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            "chore(rapid): commit a stray rapid-debt.jsonl append "
            "(T-1699 DirtyMain auto-heal)",
            "--",
            "rapid-debt.jsonl",
        ]
    )
    return committed.is_ok and committed.danger_ok.returncode == 0


# T-1434: the literal path `frob.gates._coverage._LOCK_REL` names -- NOT
# imported from there. `frob.gates` already imports FROM `frob.tickets`
# (e.g. `frob.gates._coverage.enforce_worktree_lease`,
# `frob.gates._todo_fmt.TicketQueue`), so importing `frob.gates._coverage`
# from this module would be circular; a plain string literal is the
# cheapest way to name the one path this module needs to special-case
# without inventing a shared constants module for a single filename.
_COVERAGE_LOCK_PATH = "frob-coverage.lock.json"


# frob:ticket T-1434
# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to dict.items() \
# iteration and dict.get chained twice, plain dict operations the resolver cannot \
# statically bound; the one real raise path (json.loads on malformed input) is caught \
# above"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# every dict access below is dict.get (never raises KeyError by construction), not a \
# bare subscript; a false positive from the gate's syntactic scan"
def _merged_lock_doc(ours_text: str, theirs_text: str) -> dict | None:
    """The elementwise-max merge of two coverage-lock JSON texts
    (`_merge_coverage_lock_conflict`'s pure half): per module, the higher
    of both sides' `module_line` percentage; `source_sha` from whichever
    side carries more modules (proxy for the more complete run). `None`
    when either side fails to parse as the expected
    `{"source_sha": ..., "module_line": {...}}` shape."""
    try:
        ours_doc = json.loads(ours_text)
        theirs_doc = json.loads(theirs_text)
    except ValueError:
        return None
    ours_lines = ours_doc.get("module_line")
    theirs_lines = theirs_doc.get("module_line")
    if not isinstance(ours_lines, dict) or not isinstance(theirs_lines, dict):
        return None
    merged_lines: dict[str, float] = dict(ours_lines)
    for module, theirs_pct in theirs_lines.items():
        ours_pct = merged_lines.get(module)
        if ours_pct is None or theirs_pct > ours_pct:
            merged_lines[module] = theirs_pct
    source_sha = (
        ours_doc.get("source_sha")
        if len(ours_lines) >= len(theirs_lines)
        else theirs_doc.get("source_sha")
    )
    return {
        "source_sha": source_sha,
        "module_line": dict(sorted(merged_lines.items())),
    }


# frob:ticket T-1434
# frob:tests tests/test_ticket_land.py::TestCoverageLockConflictMerges.test_conflicting_lock_merges_to_the_higher_of_both_sides  # noqa: E501
# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to run_argv, a \
# cross-module Result-returning wrapper the resolver cannot see through, and \
# ours.danger_ok.stdout/theirs.danger_ok.stdout attribute access on its own return \
# type; every locally fallible step (path.write_text) is caught below"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# _merged_lock_doc's own dict.get chain, propagated by call, is a false positive per \
# its own EXHAUST002 waiver above; no bare-subscript access is reachable from this \
# function's own source"
def _merge_coverage_lock_conflict(cwd: Path, path: str) -> bool:
    """Resolve a genuine merge conflict on `frob-coverage.lock.json` by
    taking the ELEMENTWISE MAX of both sides' `module_line` percentages,
    rather than blindly keeping one side (T-1434).

    T-1434 confirmed a real defect: `_auto_resolve_out_of_scope_conflicts`
    resolves any out-of-scope conflicted path by unconditionally keeping
    one side (`git checkout --<keep>`) -- correct for an ordinary source
    file (main's side is definitionally authoritative for something the
    landing ticket never touched), but wrong for this file specifically.
    `frob-coverage.lock.json` is a committed coverage-ratchet artifact
    (`write_coverage_lock`/`_apply_lock_ratchet` in
    `frob.gates._coverage`, T-1363): a conflict here means BOTH sides ran
    their own `--stamp-coverage` since diverging, and blindly keeping one
    side silently discards the other's real, freshly measured numbers --
    exactly the "a freshly stamped lock reverted to an older committed
    value" shape T-1270's agent observed. This is the same "never
    silently lower a committed floor" principle `_apply_lock_ratchet`
    already applies to a single side's own write, extended across a
    two-sided merge: for every module present on either side, keep
    whichever side's percentage is HIGHER (a module only on one side
    keeps that side's value unchanged). `source_sha` is taken from
    whichever side has the larger `module_line` (a rough proxy for "more
    complete run"; a real re-stamp is expected to correct it at the next
    `--stamp-coverage` regardless).

    Returns `True` (and stages the merged file) only when BOTH sides
    parse as the expected `{"source_sha": ..., "module_line": {...}}`
    shape; returns `False` (leave conflicted, exactly as before T-1434)
    for anything else -- a malformed side, a missing stage, or a git
    failure -- so this never guesses on data it cannot make sense of.
    """
    ours = run_argv(["git", "-C", str(cwd), "show", f":2:{path}"])
    theirs = run_argv(["git", "-C", str(cwd), "show", f":3:{path}"])
    if ours.is_err or ours.danger_ok.returncode != 0:
        return False
    if theirs.is_err or theirs.danger_ok.returncode != 0:
        return False
    merged_doc = _merged_lock_doc(ours.danger_ok.stdout, theirs.danger_ok.stdout)
    if merged_doc is None:
        return False
    full_path = cwd / path
    try:
        full_path.write_text(
            json.dumps(merged_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return False
    add = run_argv(["git", "-C", str(cwd), "add", "--", path])
    if add.is_err or add.danger_ok.returncode != 0:
        return False
    _log.info(
        "land: merged conflicting %s -- kept the higher of both sides' "
        "module_line percentages for every module (T-1434), never "
        "blindly discarding one side's freshly stamped data",
        path,
    )
    return True


def _conflicted_files(root: Path) -> set[str]:
    """Paths git currently reports unmerged (`U`) in `root`'s index."""
    spawned = run_argv(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=U"]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return set()
    return {
        line.strip() for line in spawned.danger_ok.stdout.splitlines() if line.strip()
    }


def _deletion_glob_too_broad(glob: str) -> bool:
    """Whether a scope glob is too broad to trust for authorizing a
    DELETION (D-12): a bare top-level directory (`src/`, expanded to
    `src/**`) or the whole-tree `.`/`*` pattern. `scope_matches`'s
    ordinary dir-glob expansion (T-0241) is correct for the general
    "is this file in scope" question, but a ticket scoped only to a
    single top-level directory silently authorizes deleting ANYTHING
    under it -- exactly the stale-base incident class this filter exists
    to catch. A more specific glob (`src/frob/`, `src/frob/tickets/**`)
    is still trusted.

    T-1680: breadth is decided by what the pattern MATCHES, not by whether
    it happens to contain a slash. A pattern with no wildcard
    metacharacter is EXACT -- it authorizes precisely one path, the
    narrowest authorization there is, and is trusted whether or not it
    sits at the repo root. The old `"/" not in stripped` test rejected
    `FROBLEMS.md`/`tickets.md`/`README.md` as "over-broad" while trusting
    `src/frob/tickets/**`, which matches hundreds of files, and left
    root-level deletions unlandable: the refusal named the scope entry
    that already authorized the file and told the operator to add it."""
    stripped = glob.removesuffix("/**").removesuffix("/*").rstrip("/")
    if stripped in ("", ".", "*"):
        return True
    if not any(ch in glob for ch in "*?["):
        return False
    return "/" not in stripped


def _deletion_owned(path: str, scope: tuple[str, ...]) -> bool:
    """Whether `path` is authorized as an OWNED deletion by `scope`: matches
    `scope_matches` AND is not matched only via an over-broad glob (D-12).
    Deliberately stricter than plain `scope_matches`, and used only
    by the deletion filter -- every other scope-consulting site (SCOPE001,
    pre-work digests, ordinary in-scope checks) keeps the normal
    `scope_matches` semantics unchanged."""
    from frob.tickets._models import _scope_globs, _split_scope_entries

    narrow_globs = [
        glob
        for glob in _scope_globs(_split_scope_entries(scope))
        if not _deletion_glob_too_broad(glob)
    ]
    return any(fnmatch.fnmatch(path, glob) for glob in narrow_globs)


def _abort_merge(worktree: Path) -> None:
    """Best-effort `git merge --abort` to leave the worktree exactly as found."""
    run_argv(["git", "-C", str(worktree), "merge", "--abort"])


def _archived_ids(root: Path) -> frozenset[str]:
    """Every ticket id in `root`'s `tickets-archive.md` -- the authoritative
    "already archived, must never re-enter the active ledger" set a splice
    guards against (T-0176 reviewer fix). An unreadable/malformed archive
    degrades to empty rather than blocking the land -- archive resurrection
    is a correctness bug worth guarding against, not a reason to hard-fail
    a landing whose archive happens to be unparseable for an unrelated
    reason."""
    path = archive_path(root)
    if not path.exists():
        return frozenset()
    parsed = _parse_ledger(path.read_text(encoding="utf-8"))
    if parsed.is_err:
        _log.warning(
            "land: %s unreadable (%s), archive-resurrection guard degraded to empty",
            path,
            parsed.danger_err,
        )
        return frozenset()
    return frozenset(parsed.danger_ok)


# frob:ticket T-1721
def _splice_and_stage(
    checkout: Path,
    pre_text: str,
    incoming_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    ticket_id: str | None = None,
    base_text: str | None = None,
) -> Result[str, LandError]:
    """Write the ledger splice of `pre_text`/`incoming_text` to `checkout`'s
    tickets.md and `git add` it; overrides whatever git's own textual merge
    produced -- tickets.md is ALWAYS resolved via a splice, never via git's
    line-level algorithm, so a both-sides-append never false-conflicts and a
    same-id divergence always keeps the newest state (T-0176).

    `ticket_id`, when given, scopes the splice to ONLY that ticket's own
    block via `_splice_only_ticket` (T-0479) -- every other id comes from
    `pre_text` untouched BY DEFAULT, so a worktree's stale sibling-ticket
    state can never overlay main's newer one. `ticket_id=None` (the
    default) keeps the original whole-ledger `splice_ledger` merge, used
    only where BOTH sides are pulling in each other's full set of tickets on
    purpose (there is no "one ticket being landed" to scope to). `archived_
    ids` excludes anything main has already archived from ever re-entering
    the merged active ledger, either way.

    T-1721: `base_text` (the true merge-base's ledger text), passed through
    to `_splice_only_ticket` when `ticket_id` is given, lets a SIBLING id's
    edit be carried forward (or a genuine conflict refused loudly) instead
    of T-0479's blanket main-wins default silently discarding it -- see
    `_splice_only_ticket`'s own docstring. Maps its
    `TicketError.SiblingLedgerEditConflict` to the distinct
    `LandError.SiblingLedgerEditConflict` rather than the generic
    `GitFailed`, so the refusal names its own real cause."""
    if ticket_id is not None:
        spliced = _splice_only_ticket(
            pre_text,
            incoming_text,
            ticket_id,
            archived_ids=archived_ids,
            base_text=base_text,
        )
    else:
        spliced = splice_ledger(pre_text, incoming_text, archived_ids=archived_ids)
    if spliced.is_err:
        _log.error(
            "land: tickets.md splice failed (%s) -- resolve manually in %s",
            spliced.danger_err,
            checkout,
        )
        if spliced.danger_err is TicketError.SiblingLedgerEditConflict:
            return Err(LandError.SiblingLedgerEditConflict)
        return Err(LandError.GitFailed)
    ledger_path(checkout).write_text(spliced.danger_ok, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(spliced.danger_ok)


def _read_ledger_text_or_empty(checkout: Path) -> str:
    """`tickets.md`'s text under `checkout`, or `""` if it does not exist."""
    path = ledger_path(checkout)
    return path.read_text(encoding="utf-8") if path.exists() else ""


# frob:ticket T-0959
def _read_archive_text_or_empty(checkout: Path) -> str:
    """`tickets-archive.md`'s text under `checkout`, or `""` if it does not
    exist -- the archive-file twin of `_read_ledger_text_or_empty` (T-0959)."""
    path = archive_path(checkout)
    return path.read_text(encoding="utf-8") if path.exists() else ""


# frob:ticket T-1154
def _read_text_at_ref(worktree: Path, ref: str, relative_path: str) -> str | None:
    """`git show <ref>:<relative_path>` inside `worktree`, or `None` on any
    failure (missing at that ref, non-zero exit) -- used to fetch a ledger/
    archive file's content AT THE TRUE MERGE-BASE commit (T-1154), never a
    hard failure since a merge-base-aware splice is a sharpening of the
    existing `_newer` tiebreak, not a new hard requirement."""
    result = run_argv(["git", "-C", str(worktree), "show", f"{ref}:{relative_path}"])
    if result.is_err or result.danger_ok.returncode != 0:
        return None
    return result.danger_ok.stdout


# frob:ticket T-0959
# frob:tests tests/test_ticket_land.py::TestArchiveSpliceDiscipline.test_splice_and_stage_archive_merges_by_id_never_overwrites  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestArchiveSpliceDiscipline.test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish  # noqa: E501
def _parse_archive_side(
    text: str, side: str, checkout: Path
) -> Result[dict[str, Ticket], LandError]:
    """Parse one side of the archive splice, refusing loudly (T-0959) rather
    than letting an unparseable copy silently fall out of the union merge."""
    parsed = _parse_ledger(text)
    if parsed.is_err:
        _log.error(
            "land: tickets-archive.md splice refused -- %s copy "
            "unparseable (%s), resolve manually in %s",
            side,
            parsed.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    return Ok(parsed.danger_ok)


def _verify_archive_merge(
    authoritative: dict[str, Ticket], merged: dict[str, Ticket], checkout: Path
) -> Result[str, LandError]:
    """Render the merged archive after the T-0959 guards: every id in the
    authoritative (root/main pre-land) archive must survive the merge, and
    the rendered text must round-trip (`_check_ledger_id_integrity`,
    extending the T-0740 pattern to this file)."""
    missing = set(authoritative) - set(merged)
    if missing:
        _log.error(
            "land: tickets-archive.md splice refused -- id(s) %s present in "
            "the archive's pre-land authoritative state vanished from the "
            "merged result (T-0959 archive id-integrity guard); this must "
            "never happen by construction of a union merge -- inspect %s "
            "by hand before retrying",
            sorted(missing),
            checkout,
        )
        return Err(LandError.GitFailed)
    rendered = _render_ledger(merged)
    integrity = _check_ledger_id_integrity(merged, rendered)
    if integrity.is_err:
        _log.error(
            "land: tickets-archive.md splice failed its id-integrity "
            "round-trip check (%s) -- resolve manually in %s",
            integrity.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    return Ok(rendered)


def _splice_and_stage_archive(
    checkout: Path,
    authoritative_text: str,
    other_text: str,
    *,
    base_text: str | None = None,
) -> Result[str, LandError]:
    """Ledger-level splice of `tickets-archive.md` (T-0959): union both
    sides by id via `_merge_ledger_tickets` (never git's raw text merge --
    the T-0703 wholesale-stale-copy incident), verify no authoritative id
    vanishes, then write and `git add` the merged result.

    `authoritative_text` is always root/main's CURRENT copy (only main
    sweeps archives; a worktree copy is equal or stale). T-1154:
    `base_text` (true 3-way merge-base, optional, degrades to `_newer`-only
    when absent/unparseable) sharpens the per-id tiebreak -- see
    `_merge_ledger_tickets`/`_resolve_divergence` for the wrong-side-merge
    class this closes (the T-1145/T-1143 incident)."""
    authoritative_parsed = _parse_archive_side(
        authoritative_text, "authoritative", checkout
    )
    if authoritative_parsed.is_err:
        return Err(authoritative_parsed.danger_err)
    other_parsed = _parse_archive_side(other_text, "worktree", checkout)
    if other_parsed.is_err:
        return Err(other_parsed.danger_err)
    authoritative, other = authoritative_parsed.danger_ok, other_parsed.danger_ok
    base = None
    if base_text is not None:
        base_parsed = _parse_ledger(base_text)
        base = base_parsed.danger_ok if base_parsed.is_ok else None
    merged = _merge_ledger_tickets(authoritative, other, base=base)
    rendered_result = _verify_archive_merge(authoritative, merged, checkout)
    if rendered_result.is_err:
        return Err(rendered_result.danger_err)
    rendered = rendered_result.danger_ok
    archive_path(checkout).write_text(rendered, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets-archive.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(rendered)


# frob:ticket T-1154
# frob:ticket T-1721
def _resolve_merge_base_texts(
    worktree: Path, main_branch: str
) -> tuple[str | None, str | None]:
    """`_merge_main_into_worktree`'s own true-merge-base text resolution
    (ARCH001 split): `(tickets.md, tickets-archive.md)` content at
    `_true_merge_base(worktree, main_branch)`, best-effort -- either or
    both are `None` on any git failure resolving the base or reading the
    file at it, never a hard error (a merge-base-aware splice is a
    sharpening of the existing merge, not a new hard requirement)."""
    base_sha = _true_merge_base(worktree, main_branch)
    if base_sha.is_err:
        return None, None
    sha = base_sha.danger_ok
    return (
        _read_text_at_ref(worktree, sha, "tickets.md"),
        _read_text_at_ref(worktree, sha, "tickets-archive.md"),
    )


# frob:ticket T-1721
# frob:ticket T-2105
_TICKET_DIR_TICKET_MD_RE = re.compile(r"^tickets/([^/]+)/ticket\.md$")


# frob:ticket T-2105
def _ticket_dir_ticket_md_paths(cwd: Path) -> set[str]:
    """Every `tickets/<id>/ticket.md` path tracked at `cwd`'s current HEAD
    (v2-mode ticket store layout, `frob.tickets._store.v2_ticket_dir`)."""
    spawned = run_argv(
        [
            "git",
            "-C",
            str(cwd),
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "--",
            "tickets/",
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return set()
    return {
        line.strip()
        for line in spawned.danger_ok.stdout.splitlines()
        if _TICKET_DIR_TICKET_MD_RE.match(line.strip())
    }


# frob:ticket T-2105
def _read_tracked_text_or_none(cwd: Path, path: str) -> str | None:
    """`git show HEAD:<path>` in `cwd`, or `None` if that path does not
    exist at `cwd`'s current HEAD."""
    spawned = run_argv(["git", "-C", str(cwd), "show", f"HEAD:{path}"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


# frob:ticket T-2105
def _read_text_at_commit_or_none(cwd: Path, commit: str, path: str) -> str | None:
    """`git show <commit>:<path>` in `cwd`, or `None` if that path does not
    exist at `commit` (T-2105's merge-base existence check)."""
    spawned = run_argv(["git", "-C", str(cwd), "show", f"{commit}:{path}"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


# frob:ticket T-2105
# frob:tests \
# tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.te\
# st_flags_id_with_genuinely_different_content_on_both_sides
# frob:tests \
# tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.te\
# st_ignores_the_landing_tickets_own_id
# frob:tests \
# tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.te\
# st_ignores_identical_content_on_both_sides
# frob:tests \
# tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions.te\
# st_ignores_an_id_that_already_existed_at_the_merge_base
# frob:waive COV001 reason="docs/modules/tickets.md (this module's own doc home) was \
# under live contention from multiple concurrent tickets (T-1780's own subject) at fix \
# time and could not be added to this scope -- filed a follow-up (draft T-2116, \
# renumbers to a real id at its own land) to add the frob:doc anchor once the file \
# frees, per the same T-2003/T-1999 precedent \
# (src/frob/tickets/_leases.py::is_effectively_in_progress); not silently dropped"
def detect_duplicate_ticket_id_collisions(
    worktree: Path, root: Path, landing_ticket_id: str, main_branch: str
) -> frozenset[str]:
    """T-2105 (half 2 of T-2092): compare every `tickets/<id>/ticket.md`
    path tracked on BOTH `worktree`'s pre-merge HEAD and `root`'s (main's)
    HEAD, by raw blob content -- BEFORE any `git merge` runs. Exactly one
    writer ever owns a given ticket id's record under normal operation, so
    any such path whose content genuinely differs between the two sides
    means two DISTINCT records were independently written at the same id:
    the T-2083/T-2090 field incident's exact shape, where a landing
    worktree's finalized draft and a concurrent `frob ticket new` direct on
    main collided on the same id and the land machinery's own internal
    merge-main-into-worktree step (`_auto_resolve_out_of_scope_conflicts`,
    treating the other record as out-of-scope) silently discarded one
    side's content entirely -- caught only by grepping ticket CONTENT on
    main post-land, since the id itself looked perfectly fine throughout.

    Checking blob content directly, ahead of the merge, catches this
    regardless of whether git's own line-based merge would ever have
    flagged a textual conflict for it (the two sides' edits need not
    overlap on the same lines to still be two unrelated records).

    An id whose `tickets/<id>/ticket.md` already existed at
    `worktree`/`main_branch`'s merge-base is NOT a collision -- it is an
    ORDINARY ticket that both sides independently edited (e.g. a sibling
    ticket the worktree closed while main also touched it), which is a
    real conflict of a different, already-handled kind (T-1914's sibling-
    state-regression guard, or an ordinary git merge conflict inside the
    landing ticket's own scope). Only a `tickets/<id>/ticket.md` ABSENT at
    the merge-base but present with genuinely different content on both
    sides afterward means two independent id ALLOCATIONS collided --
    exactly this ticket's own subject. Returns the set of colliding ticket
    ids -- never `landing_ticket_id` itself, since that record's
    difference from main is exactly what this land exists to carry
    forward, not a collision."""
    base = _true_merge_base(worktree, main_branch)
    base_commit = base.danger_ok if base.is_ok else None
    collisions: set[str] = set()
    for path in sorted(
        _ticket_dir_ticket_md_paths(worktree) | _ticket_dir_ticket_md_paths(root)
    ):
        match = _TICKET_DIR_TICKET_MD_RE.match(path)
        if match is None:
            continue
        ticket_id = match.group(1)
        if ticket_id == landing_ticket_id:
            continue
        ours = _read_tracked_text_or_none(worktree, path)
        theirs = _read_tracked_text_or_none(root, path)
        if ours is None or theirs is None:
            continue
        if ours == theirs:
            continue
        if base_commit is not None:
            at_base = _read_text_at_commit_or_none(worktree, base_commit, path)
            if at_base is not None:
                # Existed before the two sides diverged -- an ordinary
                # edit conflict on a pre-existing ticket, not a
                # duplicate-id allocation collision.
                continue
        collisions.add(ticket_id)
    return frozenset(collisions)


def _merge_main_into_worktree(
    root: Path, worktree: Path, ticket: Ticket, main_branch: str
) -> Result[bool, LandError]:
    """Stage (`--no-commit`) main into the worktree, resolving any tickets.md
    conflict via `splice_ledger` and any tickets-archive.md conflict via the
    T-0959 archive splice (`_splice_and_stage_archive`); any OTHER
    conflicted file aborts loudly. Returns whether a merge actually happened
    (False = worktree was already up to date with main, a no-op).

    T-1154: also resolves the true 3-way merge-base's tickets-archive.md
    text (`_true_merge_base` + `_read_text_at_ref`, best-effort -- `None`
    on any failure) and threads it into the archive splice as `base_text`,
    so a same-id divergence prefers whichever side made a REAL edit over
    whichever side is merely stale relative to the branch point -- see
    `_merge_ledger_tickets`/`_resolve_divergence` for the wrong-side-merge
    class this closes.

    T-1721 CORRECTION to this docstring's own prior claim: it used to say
    tickets.md's `_splice_and_stage` call "does not need this" because
    `ticket_id`-scoping (T-0479) "already makes every sibling id come from
    `main_text` untouched" -- true as a description of T-0479's mechanism,
    but wrong as a justification: that blanket untouched-default is exactly
    what silently discarded a worktree's genuine SIBLING edit (the T-1637
    field incident -- an evidence rebind on an unrelated ticket, made mid-
    another-ticket's-land, dropped without a trace by every land attempt
    that tried to carry it, three times, before the pattern was diagnosed).
    tickets.md's own splice now ALSO receives `base_text` below, for the
    same reason the archive splice already did: to tell a sibling's genuine
    isolated edit apart from mere staleness instead of assuming every
    sibling id is stale by construction."""
    pre_text = _read_ledger_text_or_empty(worktree)
    main_text = _read_ledger_text_or_empty(root)
    # frob:ticket T-0959
    pre_archive_text = _read_archive_text_or_empty(worktree)
    main_archive_text = _read_archive_text_or_empty(root)
    base_ledger_text, base_archive_text = _resolve_merge_base_texts(
        worktree, main_branch
    )

    # frob:ticket T-2105
    collisions = detect_duplicate_ticket_id_collisions(
        worktree, root, ticket.id, main_branch
    )
    if collisions:
        _log.error(
            "land: %s refusing to merge %s into %s -- ticket id(s) %s have "
            "DIFFERENT tickets/<id>/ticket.md content on the worktree's side "
            "vs %s's (T-2105 duplicate-id collision: two distinct records "
            "were independently written at the same id) -- an ordinary git "
            "merge could resolve this with no textual conflict at all and "
            "silently discard one side's content; resolve by hand (compare "
            "`git -C %s show HEAD:tickets/<id>/ticket.md` against "
            "`git -C %s show HEAD:tickets/<id>/ticket.md` for each id above, "
            "then renumber whichever record should not have this id via "
            "`frob ticket renumber`) before retrying",
            ticket.id,
            main_branch,
            worktree,
            sorted(collisions),
            main_branch,
            worktree,
            root,
        )
        return Err(LandError.MergeConflict)

    merged = run_argv(
        ["git", "-C", str(worktree), "merge", "--no-commit", "--no-ff", main_branch]
    )
    if merged.is_err:
        return Err(LandError.GitFailed)
    if (
        merged.danger_ok.returncode == 0
        and "up to date" in merged.danger_ok.stdout.lower()
    ):
        return Ok(False)

    conflict_check = _check_only_tickets_conflicted(worktree, ticket, main_branch)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    # T-0479/T-0475: base the splice on MAIN's ledger (main_text), not the
    # worktree's, and overlay ONLY the ticket being landed (`ticket.id`)
    # from the worktree's pre-merge copy. This is the exact site of the
    # T-0475 incident: the old whole-ledger merge based the splice on the
    # worktree's stale `pre_text`, so a sibling ticket the worktree still
    # remembered as in-progress (from before it was later requeued back to
    # queued on main) beat main's newer queued state on `_newer`'s state-
    # rank comparison and resurrected it. Scoping to `ticket.id` makes every
    # sibling ticket's state come from main untouched BY DEFAULT -- only
    # the ticket actually being landed is unconditionally taken from the
    # worktree; `base_text` (T-1721) lets a genuine sibling edit still be
    # carried forward (or a real conflict refused) instead of assumed away.
    spliced = _splice_and_stage(
        worktree,
        main_text,
        pre_text,
        archived_ids=_archived_ids(root),
        ticket_id=ticket.id,
        base_text=base_ledger_text,
    )
    if spliced.is_err:
        _abort_merge(worktree)
        return Err(spliced.danger_err)

    # frob:ticket T-0959
    # T-0959: tickets-archive.md used to ride along on whatever git's raw
    # merge produced for it here, unguarded -- splice it the same way, with
    # root/main's copy (freshest, since only main ever archives) as the
    # authoritative side.
    archive_spliced = _splice_and_stage_archive(
        worktree, main_archive_text, pre_archive_text, base_text=base_archive_text
    )
    if archive_spliced.is_err:
        _abort_merge(worktree)
        return Err(archive_spliced.danger_err)
    return Ok(True)


# frob:ticket T-0479
def _auto_resolve_out_of_scope_conflicts(
    cwd: Path, ticket: Ticket, *, keep: str
) -> Result[frozenset[str], LandError]:
    """After a merge/squash leaves paths conflicted in `cwd`, auto-resolve
    every conflicted path OUTSIDE `ticket.scope` by `git checkout --<keep>`
    (`keep` is "ours" or "theirs", matching git's own vocabulary for the
    merge direction in play) and staging it, then return whatever is STILL
    conflicted (i.e. paths inside `ticket.scope`, plus any out-of-scope path
    the checkout itself failed on) for the caller to treat as a real
    conflict (T-0479).

    `ticket.scope` genuinely never authorized the worktree to change a file
    outside it -- a conflict there is definitionally noise from an
    unrelated concurrent main change, not an editorial decision belonging
    to this ticket, so taking `keep`'s side is always correct rather than a
    guess. `tickets.md` and `tickets-archive.md` are excluded unconditionally
    (T-0959 extended this exclusion to the archive file); both are always
    resolved via a ledger splice (`_splice_and_stage`/`_splice_and_stage_
    archive`), never via `git checkout`.

    T-1002: a registered union zone (`_UNION_ZONES`) is resolved via its own
    union-merge strategy FIRST, regardless of whether it is in or out of
    `ticket.scope` -- a zone file is very often IN scope for the ticket that
    is landing (e.g. a ticket editing `frob.toml`'s `[gates.severity]`
    block), so the ordinary in-scope-stays-conflicted rule below would never
    even get a chance to auto-resolve it otherwise."""
    conflicted = _conflicted_files(cwd) - {"tickets.md", "tickets-archive.md"}
    if not conflicted:
        return Ok(frozenset())
    zone_resolved = _resolve_union_zone_conflicts(
        cwd, {f for f in conflicted if _zone_for_path(f) is not None}
    )
    if zone_resolved.is_err:
        return zone_resolved
    non_zone = {f for f in conflicted if _zone_for_path(f) is None}
    conflicted = non_zone | zone_resolved.danger_ok
    if not conflicted:
        return Ok(frozenset())
    still_conflicted = {f for f in conflicted if scope_matches(f, ticket.scope)}
    for path in sorted(conflicted - still_conflicted):
        # T-1434: frob-coverage.lock.json is a coverage-ratchet artifact,
        # not an ordinary source file -- blindly keeping one side of a
        # real conflict here silently discards the other side's freshly
        # stamped data (confirmed root cause of the "reverted to an
        # older committed value" incident T-1270's agent observed). Try
        # the elementwise-max merge FIRST; only fall through to the
        # ordinary blind-checkout behavior if that merge itself declines
        # (a malformed side, a git failure) -- never worse than before
        # T-1434, only better when it succeeds.
        if path == _COVERAGE_LOCK_PATH and _merge_coverage_lock_conflict(cwd, path):
            _log.info(
                "land: %s auto-resolved out-of-scope conflict in %s via "
                "the T-1434 coverage-lock merge (not in scope %s)",
                ticket.id,
                path,
                list(ticket.scope),
            )
            continue
        resolved = _checkout_and_stage(cwd, keep, path)
        if resolved.is_err:
            _log.warning(
                "land: %s auto-resolve of out-of-scope conflict %s (keep=%s) "
                "failed -- leaving it conflicted for manual resolution",
                ticket.id,
                path,
                keep,
            )
            still_conflicted.add(path)
            continue
        _log.info(
            "land: %s auto-resolved out-of-scope conflict in %s by keeping "
            "%s's side (not in scope %s)",
            ticket.id,
            path,
            keep,
            list(ticket.scope),
        )
    return Ok(frozenset(still_conflicted))


def _checkout_and_stage(cwd: Path, keep: str, path: str) -> Result[None, LandError]:
    """`git checkout --<keep> -- <path> && git add <path>` in `cwd`."""
    checkout = run_argv(["git", "-C", str(cwd), "checkout", f"--{keep}", "--", path])
    if checkout.is_err or checkout.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    add = run_argv(["git", "-C", str(cwd), "add", "--", path])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


def _check_only_tickets_conflicted(
    worktree: Path, ticket: Ticket, main_branch: str
) -> Result[None, LandError]:
    """`Err(MergeConflict)` (aborting the merge) if any IN-SCOPE file besides
    tickets.md/tickets-archive.md is still conflicted after
    `_merge_main_into_worktree`'s merge; any OUT-OF-SCOPE conflict is
    auto-resolved by taking main's side
    first (T-0479), since main is `theirs` in this merge direction (main
    merged into the worktree)."""
    resolved = _auto_resolve_out_of_scope_conflicts(worktree, ticket, keep="theirs")
    if resolved.is_err:
        _abort_merge(worktree)
        return Err(resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        _abort_merge(worktree)
        _log.error(
            "land: %s merging %s into %s conflicts in scoped file(s): %s -- "
            "resolve manually (cd %s && git merge %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            main_branch,
            worktree,
            sorted(remaining),
            worktree,
            main_branch,
            ticket.id,
            worktree,
        )
        return Err(LandError.MergeConflict)
    return Ok(None)


def _unowned_deletions(
    root: Path, worktree: Path, scope: tuple[str, ...], main_branch: str
) -> Result[tuple[str, ...], LandError]:
    """Files main has that the worktree (post-merge) deletes, outside `scope`
    -- the stale-base guard: a worktree branched from an old main can end up
    silently deleting a feature main already landed, and this is the check
    that catches it before it reaches main (T-0176)."""
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            main_branch,
            "--diff-filter=D",
            "--name-only",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    deleted = [
        line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
    ]
    unowned = tuple(f for f in deleted if not _deletion_owned(f, scope))
    return Ok(unowned)


#: A single-physical-line `# frob:waive RULE ...` (or `//` for non-Python
#: sources) comment -- mirrors `frob.gates._fix_engine_text._WAIVE_SINGLE_
#: LINE_RE` exactly (same shape, independently defined here since importing
#: `frob.gates` from `frob.tickets` would cycle: `frob.gates` already
#: imports `frob.tickets.TicketQueue`).
_LAND_WAIVE_LINE_RE = re.compile(r"^\s*(#|//)\s*frob:waive\s+(\S+)\b")


def _waive_deletions_in_diff(
    worktree: Path, diff_args: Sequence[str]
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line a `git
    diff <diff_args> --no-color -U0` invocation in `worktree` reports as
    DELETED -- the shared diff-parsing core both `_uncommitted_waive_
    deletions` (T-1323, `diff_args=("HEAD",)`, the worktree's uncommitted
    edits) and `_committed_waive_deletions` (T-1326, `diff_args=
    (f"{merge_base}..HEAD",)`, the branch's already-committed history)
    build on -- the same laundering shape, single-line `frob:waive`
    deletion riding a merge unattributed, differs only in WHICH git rev
    range is being inspected, not in how a deletion is recognized inside
    it.

    Parses 0-context unified-diff hunks (deterministic header shape)
    rather than the porcelain-name-only forms `_unowned_deletions` uses --
    a `frob:waive` line disappearing from an otherwise-modified (not
    wholly deleted) file never shows up in a `--diff-filter=D --name-only`
    listing, only inside the hunk body.

    T-1468 fix: a `frob:waive` comment may wrap its `reason="..."` text
    across several physical lines via a trailing-backslash continuation
    (this repo's own directive convention); `frob fmt`'s line-length
    absorption can RE-WRAP such a comment (change how many physical lines
    it spans, without changing its actual content) as an ordinary side
    effect of a completely unrelated ticket's land. A naive line-based diff
    read sees the old wrap's physical lines as deleted and the new wrap's
    as added -- indistinguishable, at the single-line level, from someone
    actually removing the waiver. `_fold_waive_blocks` reassembles each
    side's physical lines into logical `(rule, normalized_text)` blocks
    (joining continuations, stripping comment leaders/backslashes,
    collapsing whitespace) PER HUNK, and a deleted block is only reported
    as a real deletion if no added block in the SAME hunk normalizes to
    the identical text -- a pure re-wrap normalizes identically on both
    sides and is silently not flagged, while a genuine content change (or
    an outright removal, where no equivalent added block exists at all)
    still is."""
    diff = run_argv(
        ["git", "-C", str(worktree), "diff", *diff_args, "--no-color", "-U0"]
    )
    if diff.is_err or diff.danger_ok.returncode not in (0, 1):
        return Err(LandError.GitFailed)
    return Ok(tuple(_scan_diff_for_waive_deletions(diff.danger_ok.stdout)))


# frob:ticket T-1468
def _scan_diff_for_waive_deletions(stdout: str) -> list[tuple[str, str]]:
    """The real per-hunk scan `_waive_deletions_in_diff` delegates to
    (T-1468): walks `stdout` (a `git diff --no-color -U0` invocation)
    file-header and hunk-header boundaries, buffering each hunk's raw
    `-`/`+` physical lines and flushing them through `_real_waive_
    deletions` at every boundary -- split out from the caller purely to
    keep that function's own body short; behavior is identical to having
    this loop inline."""
    deletions: list[tuple[str, str]] = []
    current_file: str | None = None
    minus_lines: list[str] = []
    plus_lines: list[str] = []

    for line in stdout.splitlines():
        if line.startswith("--- a/") or line.startswith("--- /dev/null"):
            deletions.extend(
                _real_waive_deletions(current_file, minus_lines, plus_lines)
            )
            minus_lines, plus_lines = [], []
            current_file = (
                None if line == "--- /dev/null" else line.removeprefix("--- a/")
            )
        elif line.startswith("@@"):
            deletions.extend(
                _real_waive_deletions(current_file, minus_lines, plus_lines)
            )
            minus_lines, plus_lines = [], []
        elif line.startswith("-") and not line.startswith("---") and current_file:
            minus_lines.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            plus_lines.append(line[1:])
    deletions.extend(_real_waive_deletions(current_file, minus_lines, plus_lines))
    return deletions


# frob:ticket T-1468
def _real_waive_deletions(
    current_file: str | None, minus_lines: Sequence[str], plus_lines: Sequence[str]
) -> list[tuple[str, str]]:
    """One hunk's genuine `(file, rule)` waive deletions (T-1468): folds
    both sides into logical blocks (`_fold_waive_blocks`) and reports a
    deleted block only when no added block in the same hunk normalizes to
    the identical text -- see `_waive_deletions_in_diff`'s docstring for
    why a pure re-wrap must not count as a deletion. Returns `[]` when
    there is no current file (outside any tracked hunk) or nothing was
    deleted in this hunk."""
    if current_file is None or not minus_lines:
        return []
    added_normalized = {text for _rule, text in _fold_waive_blocks(plus_lines)}
    return [
        (current_file, rule)
        for rule, text in _fold_waive_blocks(minus_lines)
        if text not in added_normalized
    ]


# frob:ticket T-1468
def _fold_waive_blocks(lines: Sequence[str]) -> list[tuple[str, str]]:
    """`(rule, normalized_text)` for every `frob:waive` comment block found
    in `lines` (T-1468, one diff hunk's raw physical lines on one side): a
    block starts at a line matching `_LAND_WAIVE_LINE_RE` and continues
    consuming subsequent lines while the PREVIOUS line (right-stripped)
    ends in a trailing backslash continuation -- this repo's own single-
    `\\`-per-physical-line convention for wrapping a long `reason="..."`.
    A line that itself starts a fresh `frob:waive` block ends any
    in-progress one even if the prior line ended in a backslash (a real
    directive is never itself continuation prose). Returns one entry per
    block found, in file order."""
    blocks: list[tuple[str, str]] = []
    current_rule: str | None = None
    current_fragments: list[str] = []
    continuing = False

    def _flush() -> None:
        if current_rule is not None:
            blocks.append((current_rule, _normalize_waive_fragments(current_fragments)))

    for raw in lines:
        match = _LAND_WAIVE_LINE_RE.match(raw)
        if match is not None:
            _flush()
            current_rule = match.group(2)
            current_fragments = [raw]
            continuing = raw.rstrip().endswith("\\")
            continue
        if continuing and current_rule is not None:
            current_fragments.append(raw)
            continuing = raw.rstrip().endswith("\\")
            continue
        _flush()
        current_rule = None
        current_fragments = []
        continuing = False
    _flush()
    return blocks


# frob:ticket T-1468
_WAIVE_COMMENT_LEADER_RE = re.compile(r"^\s*(#|//)\s*")


def _normalize_waive_fragments(fragments: Sequence[str]) -> str:
    """Canonical, wrap-insensitive text for a `frob:waive` comment block
    (T-1468): strips each physical line's comment leader (`#`/`//`) and any
    trailing backslash continuation marker, joins the remaining fragments
    with a single space, and collapses internal whitespace runs to one
    space each -- so two comments carrying byte-identical waiver content
    but wrapped across a different number of physical lines (a `frob fmt`
    re-wrap of an over-long line, say) normalize to the exact same string."""
    parts: list[str] = []
    for frag in fragments:
        text = _WAIVE_COMMENT_LEADER_RE.sub("", frag.strip())
        text = text.rstrip()
        if text.endswith("\\"):
            text = text[:-1].rstrip()
        parts.append(text)
    normalized = " ".join(part for part in parts if part)
    return re.sub(r"\s+", " ", normalized).strip()


def _uncommitted_waive_deletions(
    worktree: Path,
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line the
    worktree's UNCOMMITTED changes (against `HEAD`, i.e. before any
    wip-commit) delete -- the T-1323 incident's own laundering path: a
    dirty worktree's edits get wip-snapshot-committed and ride the merge
    onto main, unattributed. Reading this straight off the working tree,
    BEFORE `_wip_commit` runs, is what makes the refusal below fire
    before the deletion is folded into a commit at all. Thin wrapper
    around `_waive_deletions_in_diff` with `diff_args=("HEAD",)`."""
    return _waive_deletions_in_diff(worktree, ("HEAD",))


def _committed_waive_deletions(
    worktree: Path, base_ref: str
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line the
    branch's own COMMITTED history (`base_ref..HEAD`) deletes -- the
    T-1326 extension of T-1323's guard: `_uncommitted_waive_deletions`
    only ever inspected the dirty worktree state at land time, so a
    `frob:waive` deletion an agent or tool COMMITTED mid-ticket (rather
    than leaving uncommitted) was invisible to it and rode the merge in
    unattributed -- the reviewer-flagged laundering vector T-1323's own
    approval left open. Thin wrapper around `_waive_deletions_in_diff`
    with `diff_args=(f"{base_ref}..HEAD",)`; a deletion that happened
    on `base_ref..HEAD` and was then RE-ADDED by a later commit in the
    same range does not appear here, since a two-endpoint diff (like a
    single uncommitted diff) only ever reports the NET change across the
    whole range, never per-intermediate-commit churn -- exactly mirroring
    how the uncommitted-state check already treats an add-then-remove
    inside a single dirty worktree.

    T-1550: `base_ref` is `main_branch`'s CURRENT tip, not the stale
    `merge_base` this used to diff from. On a shared multi-ticket
    worktree, an already-LANDED sibling ticket's own committed deletion
    still sits in `merge_base..HEAD` (the worktree branch keeps every
    commit it ever made, land squash-applies rather than rewriting
    history), so diffing from the stale `merge_base` re-discovers and
    re-attributes that sibling's already-landed deletion to whichever
    ticket lands next (T-1225, T-1444's re-declare-round incidents).
    Diffing from `main_branch`'s live tip instead means a deletion
    already reflected on main (because the sibling's squash-apply
    already carried it there) shows NO delta at all for that line -- both
    sides lack it -- so it is structurally never reported, no ancestry
    walk or commit-to-ticket attribution required. A deletion still only
    ever present on the worktree branch (not yet landed by anyone) is
    unaffected and is still caught exactly as before."""
    return _waive_deletions_in_diff(worktree, (f"{base_ref}..HEAD",))


# frob:ticket T-1799
def _commits_touching_path(worktree: Path, base_ref: str, file: str) -> tuple[str, ...]:
    """The REAL commit(s) in `base_ref..HEAD` that touched `file` --
    `git log --format=%h %s -- file`, one `"<sha7> <subject>"` string per
    commit, oldest first (git's default `git log` order is newest-first;
    reversed here so a refusal reads as a timeline).

    T-1799: `_check_committed_waive_deletions`'s refusal used to say only
    "revert the offending commit" with no commit named -- an agent
    reading it had to reconstruct which commit that was by hand, exactly
    the same "which one?" gap DirtyMain's T-1795 fix already closed for
    the deferred-sweep case. This is a fact read from `git log` on the
    actual path, never a guess at authorship -- empty on any git failure
    (best-effort, never turns "cannot tell" into a fabricated commit)."""
    spawned = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "log",
            "--format=%h %s",
            f"{base_ref}..HEAD",
            "--",
            file,
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    lines = [line for line in spawned.danger_ok.stdout.splitlines() if line.strip()]
    return tuple(reversed(lines))


def _waive_deletion_declared_in_done_report(body: str, file: str, rule: str) -> bool:
    """Whether `body`'s `## Done report` section (`_done_report_section_
    lines`, the same section-boundary parser `_evidence.py`'s claim-
    replay already trusts) declares THIS `(file, rule)` pair TOGETHER, on
    one line -- the acceptance criterion's "declared by the Done report"
    half of the out-of-scope test.

    T-1323 review fix: the original shape (`file in body or rule in
    body`) searched the ENTIRE ticket body, not just the Done report, and
    accepted either name alone -- in an append-only ledger, a bare rule
    id like `PERF004` can appear incidentally in old Description/Plan
    prose (or a PRIOR Done report entry about an unrelated file) and
    silently satisfy an OR check with no real disclosure ever written.
    Restricting to the Done report section closes the append-only-ledger
    leak; requiring both names on the SAME line closes the OR-vs-AND gap
    -- a line has to actually name the file the deletion happened in
    alongside the rule it removed, not merely mention each somewhere."""
    section_lines = _done_report_section_lines(body)
    if section_lines is None:
        return False
    return any(file in line and rule in line for line in section_lines)


def _uncommitted_out_of_scope_waive_deletions(
    worktree: Path, ticket: Ticket
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs from `_uncommitted_waive_deletions` that are
    NEITHER covered by `ticket.scope` (`_deletion_owned`, the same D-12
    deletion-filter precedent `_unowned_deletions` already uses) NOR
    declared by `ticket.body`'s Done report
    (`_waive_deletion_declared_in_done_report`) -- what `_land_precheck`
    refuses on, before any merge, per the T-1323 incident guard."""
    found = _uncommitted_waive_deletions(worktree)
    if found.is_err:
        return Err(found.danger_err)
    out_of_scope = tuple(
        (file, rule)
        for file, rule in found.danger_ok
        if not _deletion_owned(file, ticket.scope)
        and not _waive_deletion_declared_in_done_report(ticket.body, file, rule)
    )
    return Ok(out_of_scope)


# frob:ticket T-1326
# frob:ticket T-1550
def _committed_out_of_scope_waive_deletions(
    worktree: Path, ticket: Ticket, base_ref: str
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs from `_committed_waive_deletions` that are
    NEITHER covered by `ticket.scope` (`_deletion_owned`, same D-12
    precedent) NOR declared by `ticket.body`'s Done report (`_waive_
    deletion_declared_in_done_report`) -- the committed-history mirror of
    `_uncommitted_out_of_scope_waive_deletions` (T-1323), extended (T-1326)
    to cover a `frob:waive` deletion the branch already COMMITTED before
    land ran, not only one still sitting uncommitted in the worktree.
    Identical ownership/declaration logic, applied against `base_ref..
    HEAD` instead of `HEAD` vs. the working tree.

    T-1550: `base_ref` is `main_branch`'s live tip (see `_committed_
    waive_deletions`'s own T-1550 note), not the stale `merge_base` this
    used to receive -- a deletion an already-landed SIBLING ticket
    committed on this same shared worktree branch is already reflected
    on `main_branch` by the time it lands, so it never shows up in a
    `main_branch..HEAD` diff at all and is never re-attributed to
    whichever ticket lands next off the same branch."""
    found = _committed_waive_deletions(worktree, base_ref)
    if found.is_err:
        return Err(found.danger_err)
    out_of_scope = tuple(
        (file, rule)
        for file, rule in found.danger_ok
        if not _deletion_owned(file, ticket.scope)
        and not _waive_deletion_declared_in_done_report(ticket.body, file, rule)
    )
    return Ok(out_of_scope)


# frob:ticket T-1003
# frob:tests tests/test_ticket_land.py::TestUvLockSync.test_worktree_side_lock_flap_auto_restored_before_wip_commit kind="integration"  # noqa: E501
def _wip_commit(
    worktree: Path, ticket_id: str, *, dry_run: bool
) -> Result[bool, LandError]:
    """Commit any uncommitted worktree changes as a WIP snapshot before
    landing -- the manual "wip-commit in the worktree" step folded into
    `land` so nothing an agent forgot to commit is silently dropped by the
    merge that follows.

    T-1003: `worktree`'s own `uv.lock` frob-version-only flap (T-0793's
    shape, from a prior `uv run`/`uv lock` invocation against a pyproject a
    sibling land already bumped on main) is auto-restored HERE, before the
    dirty check, exactly mirroring `_refuse_if_main_dirty`'s ROOT-side
    restore -- without this, the flap would otherwise get silently
    wip-committed as noise in the worktree and squash-applied into the
    landing commit, instead of the ritual `git checkout -- uv.lock` on
    BOTH sides land's own callers used to have to remember."""
    if _restore_lock_version_only_drift(worktree):
        _log.info(
            "land: %s auto-restored a uv.lock frob-version-only drift in "
            "%s before the wip-commit dirty check (T-1003)",
            ticket_id,
            worktree,
        )
    dirty = _porcelain_dirty(worktree)
    if dirty.is_err:
        return Err(dirty.danger_err)
    if not dirty.danger_ok:
        return Ok(False)
    if dry_run:
        _log.info(
            "land: %s would wip-commit uncommitted changes in %s", ticket_id, worktree
        )
        return Ok(True)
    return _do_wip_commit(worktree, ticket_id)


# frob:ticket T-1006
# frob:ticket T-1184
def _wip_add_excluding_frob(worktree: Path, ticket_id: str) -> Result[None, LandError]:
    """`_do_wip_commit`'s own `git add -A` excluding `.frob/`, split out to
    keep both under the ARCH001 line budget: A repo that has not
    gitignored `.frob/` (e.g. a bare test fixture, T-1006) would otherwise
    let frob's own bookkeeping writes made while computing the dirty check
    get swept into `add -A` as if they were real ticket content, defeating
    the CRLF-normalization-only no-op detection in `_do_wip_commit`.

    T-1184: the negated pathspec below (`"--", ".", ":!.frob"`)
    trips a hard refusal on git 2.34.1 the moment `.frob` IS actually
    gitignored (the normal real-repo case, reproduced against a clean
    checkout with no ticket diff at all: git treats a NEGATED pathspec
    that names an ignored path as if the path had been named directly, and
    aborts the ENTIRE add, not just skipping `.frob`). A bare test fixture
    with no `.gitignore` at all (T-1006's original case) never hits that
    refusal -- `.frob` isn't ignored there, so the pathspec exclusion
    behaves as ordinary path filtering. Try the exclusion pathspec first
    (preserves the exact original behavior/staging semantics for that
    fixture case); only on the specific ignored-path refusal, retry by
    staging everything and then unstaging `.frob` as a separate step,
    which reaches the same end state without ever naming an ignored path
    in a pathspec."""
    add_argv = ["git", "-C", str(worktree), "add", "-A", "--", ".", ":!.frob"]
    fallback_add_argv = ["git", "-C", str(worktree), "add", "-A", "--", "."]
    unstage_frob_argv = ["git", "-C", str(worktree), "reset", "-q", "--", ".frob"]
    add = run_argv(add_argv)
    if (
        add.is_ok
        and add.danger_ok.returncode != 0
        and _is_ignored_path_refusal(add.danger_ok.stderr)
    ):
        _log.warning(
            "land: %s wip add's :!.frob pathspec hit the ignored-path "
            "refusal (T-1184) -- falling back to add-then-unstage",
            ticket_id,
        )
        add = run_argv(fallback_add_argv)
        if add.is_ok and add.danger_ok.returncode == 0:
            unstage_frob = run_argv(unstage_frob_argv)
            if unstage_frob.is_err or unstage_frob.danger_ok.returncode != 0:
                _log.error(
                    "land: %s wip unstage .frob failed: %s",
                    ticket_id,
                    _describe_git_failure(unstage_frob_argv, unstage_frob),
                )
                return Err(LandError.GitFailed)
    if add.is_err or add.danger_ok.returncode != 0:
        _log.error(
            "land: %s wip add failed: %s",
            ticket_id,
            _describe_git_failure(add_argv, add),
        )
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-0847
# frob:tests tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty.test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed  # noqa: E501
def _do_wip_commit(worktree: Path, ticket_id: str) -> Result[bool, LandError]:
    """`git add -A && git commit` a WIP snapshot in `worktree`, under
    `FROB_LAND_INTERNAL=1` (T-0828) so the T-0731 land-owned-files
    `pre-commit` hook does not refuse this land-internal commit if the
    worktree happens to carry an uncommitted land-owned-file edit.

    `_porcelain_dirty` can see a worktree as dirty purely from a line-ending
    normalization status line (WSL/autocrlf phantom-modified) -- `add -A`
    renormalizes to the identical blob, leaving nothing actually staged, and
    a plain `git commit` in that state exits 1 "nothing to commit" with no
    stderr, which used to bubble up as a spurious `GitFailed` (T-0847). After
    staging, re-check with `git diff --cached --quiet`: an empty stage means
    there was nothing real to snapshot, so we treat it as a no-op success
    instead of a land failure."""
    with _land_internal_git_env():
        added = _wip_add_excluding_frob(worktree, ticket_id)
        if added.is_err:
            return Err(added.danger_err)
        staged_argv = ["git", "-C", str(worktree), "diff", "--cached", "--quiet"]
        staged = run_argv(staged_argv)
        if staged.is_ok and staged.danger_ok.returncode == 0:
            _log.info(
                "land: %s wip add staged nothing real (normalization-only"
                " dirty status) -- treating as no-op, not GitFailed",
                ticket_id,
            )
            return Ok(False)
        commit_argv = [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"wip: pre-land snapshot for {ticket_id}",
        ]
        commit = run_argv(commit_argv)
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s wip commit failed: %s",
            ticket_id,
            _describe_git_failure(commit_argv, commit),
        )
        return Err(LandError.GitFailed)
    _log.info("land: %s wip-committed uncommitted worktree changes", ticket_id)
    return Ok(True)


# frob:ticket T-0761
def _rev_parse(worktree: Path, rev: str) -> Result[str, LandError]:
    """The full commit sha `rev` resolves to inside `worktree` (e.g. `HEAD`
    or a branch name) -- a thin `git rev-parse` wrapper shared by
    `_worktree_full_changeset`'s explicit merge-base computation (T-0761)."""
    result = run_argv(["git", "-C", str(worktree), "rev-parse", rev])
    if result.is_err or result.danger_ok.returncode != 0:
        _log.error("land: git rev-parse %s failed in %s", rev, worktree)
        return Err(LandError.GitFailed)
    return Ok(result.danger_ok.stdout.strip())


# frob:ticket T-0761
def _true_merge_base(worktree: Path, main_branch_name: str) -> Result[str, LandError]:
    """The commit sha `git merge-base main_branch_name HEAD` resolves to
    inside `worktree` -- the TRUE common ancestor `_worktree_full_changeset`
    diffs from, computed as its own explicit step (T-0761) rather than left
    implicit inside a triple-dot diff invocation. This is the root-cause fix
    for the T-0640 false-green: when `land()` was invoked with `worktree`
    pointing at the SAME checkout/branch `root` had checked out (no distinct
    feature branch was ever created), `main_branch_name` and `worktree`'s
    `HEAD` were literally the same ref, so a triple-dot diff against itself
    silently resolved to an empty changeset -- the T-0463 completeness
    assertion had nothing to check against and passed vacuously, while the
    squash-apply step degenerated to a no-op the exact same way (`git merge
    --squash` of a branch into itself is a no-op), leaving only the version
    bump and ledger splice to land. Computing the merge-base explicitly here
    lets `_worktree_full_changeset` detect and refuse that exact condition
    (merge-base == HEAD, i.e. zero commits unique to the worktree branch)
    instead of silently reporting nothing to check."""
    result = run_argv(
        ["git", "-C", str(worktree), "merge-base", main_branch_name, "HEAD"]
    )
    if result.is_err or result.danger_ok.returncode != 0:
        _log.error(
            "land: git merge-base %s HEAD failed in %s", main_branch_name, worktree
        )
        return Err(LandError.GitFailed)
    return Ok(result.danger_ok.stdout.strip())


# frob:ticket T-1755
#: Dirty paths the DETACHED post-land sweep (T-1684) is the near-certain
#: author of when they show up in a `DirtyMain` refusal: `rapid-debt.jsonl`
#: (the deferral debt line, T-1699) and `tickets.md` (a filed regression
#: ticket, T-1755 -- `new_ticket`'s own library call has no auto-commit of
#: its own, see `_rapid_sweep._commit_regression_ticket`'s docstring for
#: the confirmed root cause). NOT a v2-store path list (`tickets/T-####/`)
#: -- naming a specific ticket dir here would require parsing WHICH ticket,
#: which `describe_root_dirt` has no way to know from a bare path; the
#: monofile name is the only sweep-owned path this can identify by name
#: alone, so this stays a best-effort hint, not an exhaustive detector.
_SWEEP_OWNED_DIRTY_PATHS = ("rapid-debt.jsonl", "tickets.md")


# frob:ticket T-1821
def _staged_rapid_debt_ticket(root: Path) -> str | None:
    """The real ticket id the detached post-land sweep's own STAGED
    `rapid-debt.jsonl` write names, read from the staged blob's own
    content -- never a guess. `record_rapid_debt` (`frob.tickets._evidence`)
    always writes a `"ticket"` field on every appended line, so the staged
    index content itself carries this fact; reads the LAST JSON line in
    the staged blob (the most recently appended debt entry) and returns
    its `"ticket"` value. Returns `None` (never a plausible-but-wrong
    ticket id) whenever the blob is unreadable, has no staged content, or
    the last line does not parse -- the T-1795/T-1799 incident this exists
    to prevent was exactly a confident wrong guess, so silence here beats
    a fabricated answer."""
    spawned = run_argv(["git", "-C", str(root), "show", ":rapid-debt.jsonl"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    lines = [line for line in spawned.danger_ok.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except (json.JSONDecodeError, ValueError):
        return None
    ticket = payload.get("ticket")
    return ticket if isinstance(ticket, str) and ticket else None


# frob:ticket T-1755
def _likely_sweep_authored(paths: tuple[str, ...]) -> bool:
    """Whether every one of `paths` is a file the detached post-land sweep
    (T-1684) is known to write -- see `_SWEEP_OWNED_DIRTY_PATHS`'s own
    docstring. A MIX of a sweep-owned path and something else is NOT
    called out as sweep-authored (that would misattribute the other,
    genuinely unknown, dirty path to the sweep) -- only an ALL-sweep-owned
    dirty set is confident enough to name."""
    return bool(paths) and all(p in _SWEEP_OWNED_DIRTY_PATHS for p in paths)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_a_real_dirty_file
# frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unavailable_status_is_not_reported_as_clean  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_detached_sweep_as_likely_author  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_names_the_real_ticket_from_a_staged_rapid_debt_line  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDescribeRootDirt.test_unattributed_when_the_true_author_cannot_be_determined  # noqa: E501
# frob:ticket T-1698
# frob:ticket T-1755
# frob:ticket T-1821
def describe_root_dirt(root: Path) -> str:
    """What is making `root` dirty, rendered for a `DirtyMain` refusal.

    Decides by the SAME `.frob/`-ignoring rule `_porcelain_dirty` uses, so
    what a refusal NAMES can never disagree with what made it refuse.

    Exists because `DirtyMain` used to say only "root has uncommitted
    changes" (T-1698): during a three-agent wave, one uncommitted one-line
    file deadlocked every land in the repo, and three agents each burned
    minutes without ever learning which file it was. An error that does
    not name its own cause is a structural defect in a tool whose entire
    job is enforcement.

    T-1740: when any of the dirty paths are STAGED (not merely modified
    in the working tree), that is called out explicitly and first --
    "uncommitted changes" alone reads as working-tree edits, and sent an
    agent looking for the wrong thing when the real cause was a PRIOR
    land's leftover staged squash content.

    T-1755: when EVERY dirty path is one the detached post-land sweep is
    known to write (`_SWEEP_OWNED_DIRTY_PATHS`), that is named too -- an
    agent seeing this refusal is, per T-1755's own incident, structurally
    isolated from root and cannot investigate WHO left it dirty; naming
    the likely author turns "report and wait" into "report the specific,
    actionable cause" without the agent needing to guess."""
    all_paths = _porcelain_dirty_paths(root)
    staged_paths = _porcelain_dirty_paths_staged(root)
    rendered = _render_dirty_paths(all_paths)
    if _likely_sweep_authored(all_paths):
        real_ticket = _staged_rapid_debt_ticket(root)
        author = (
            f"the sweep child working {real_ticket}"
            if real_ticket is not None
            else "unattributed (cannot be determined from staged content)"
        )
        sweep_hint = (
            " (all paths match the detached post-land sweep's own known "
            "writes -- rapid-debt.jsonl/tickets.md, mechanism built by "
            f"T-1699/T-1755 -- likely author: {author}, a sweep child "
            "that filed something and did not commit it -- via detached "
            "post-land sweep)"
        )
    else:
        sweep_hint = ""
    if not staged_paths:
        return rendered + sweep_hint
    return (
        f"{len(staged_paths)} STAGED (likely a prior land's leftover "
        f"index, T-1740): {_render_dirty_paths(staged_paths)} -- plus "
        f"overall: {rendered}{sweep_hint}"
    )

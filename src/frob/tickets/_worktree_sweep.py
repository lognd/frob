"""frob.tickets._worktree_sweep -- the worktree-sweep family (T-2833), split
out of `frob.tickets._leases` following T-1103's per-family extraction
pattern (verbatim moves, directives intact, public surface re-exported via
explicit imports, zero caller-visible behavior change).

`sweep_worktrees`/`remove_worktree` and their shared verdict machinery
(`_WorktreeVerdict`, `_sweep_verdict_for_worktree`, the `_kept_*` gates,
`_worktree_is_clean`/`_worktree_head_age_seconds`, `_list_agent_
worktrees`/`_is_agent_worktree_path`, `_WorktreeSweepError`) are consumed
by a distinct CLI surface (`frob.app.worktree_runner`'s `frob worktree
sweep`/`frob worktree remove`, `frob.app.ticket_runner._rapid_sweep`'s
rapid-profile auto-sweep) than the lease-CRUD/ledger-commit machinery the
rest of `_leases.py` serves (T-2822's own investigated-but-deferred
finding). T-3350: `_leases.py` used to re-import and re-export
`sweep_worktrees`/`remove_worktree` for its two external importers -- that
re-export was the ONE back-edge closing a 2-node `frob.tickets._leases`
<-> `frob.tickets._worktree_sweep` CYCLE001 SCC, so both callers
(`frob.app.worktree_runner`, `frob.app.ticket_runner._rapid_sweep`) now
import these two names directly from this module instead.

Depends on `_leases.py` for its lease-side data (`_LeaseRecord`, `read_all_
leases`, `is_lease_ttl_expired`, `lease_age_seconds`, `_live_lease_for_
worktree`, `scan_for_live_worktree_process`) -- a worktree cannot be judged
safe to remove without knowing whether a live lease or live process still
holds it, so this one-directional dependency on the lease machinery is
inherent to the sweep's own correctness contract, not a leftover coupling.
"""

# frob:ticket T-2833

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

import frob.gitio as gitio
from frob.logging import get_logger
from frob.tickets._leases import (
    _LeaseRecord,
    _live_lease_for_worktree,
    lease_age_seconds,
    read_all_leases,
    scan_for_live_worktree_process,
)

_log = get_logger(__name__)


# frob:ticket T-0836
# frob:ticket T-0601
class _WorktreeSweepError(ErrorSet):
    """Fallible outcomes of `frob worktree sweep` (T-0836)."""

    NotARepo = "root is not inside a git repository"
    ListFailed = "git worktree list --porcelain failed"
    # frob:ticket T-1779
    NotARegisteredWorktree = (
        "path is not a git-registered .claude/worktrees/ agent worktree of root"
    )


# frob:ticket T-0836
# frob:ticket T-0601
# frob:ticket T-1739
class _WorktreeVerdict(BaseModel):
    """One decided outcome for a single dispatched-agent worktree during
    `frob worktree sweep` (T-0836): the worktree's resolved path, the
    verdict tag (`"removed"`, `"kept:live"` [T-1739, a live process is
    cwd'd into it], `"kept:unlanded"` [T-1934, the branch carries
    finished-but-unlanded ticket work], `"kept:lease"`, `"kept:dirty"`, or
    `"kept:age"`), and a human-readable `detail` string (e.g. the pinning
    pid for `"kept:live"`, the unlanded ticket id(s) for
    `"kept:unlanded"`, the pinning ticket id and lease age for
    `"kept:lease"`; empty for the other verdicts unless a `git worktree
    remove` call itself failed)."""

    model_config = {}

    path: str
    verdict: str
    detail: str = ""


# frob:ticket T-0836
# frob:waive DUP001 reason="T-2833: pre-existing cross-file similarity to \
# _lifecycle._root_is_itself_a_nested_worktree that predates this split -- never \
# flagged on main since the clone gate only scans files IN the current diff, and this \
# function's prior home (_leases.py) was untouched by recent diffs until now; moving \
# code, not duplicating it, surfaced the pre-existing pair. The two functions test \
# different structural questions via superficially similar Path.parts loops; a shared \
# extraction touches _lifecycle.py, outside T-2833's declared scope"
def _is_agent_worktree_path(path: Path) -> bool:
    """`True` iff `path` (already resolved) has a `.claude/worktrees`
    segment anywhere in it -- this repo's own dispatch convention for
    where a per-ticket agent worktree lives (see `docs/guides/agent-
    playbook.md`). `frob worktree sweep` only ever considers paths
    matching this convention as sweep candidates, so the repository's own
    primary checkout (and any worktree a human made by hand somewhere
    else on disk) is never a candidate for removal."""
    parts = path.parts
    return any(
        parts[i] == ".claude" and parts[i + 1] == "worktrees"
        for i in range(len(parts) - 1)
    )


# frob:ticket T-0836
# frob:tests tests/test_ticket_leases.py::TestListAgentWorktrees.test_lists_only_dot_claude_worktrees_paths kind="unit"  # noqa: E501
# frob:ticket T-0601
def _list_agent_worktrees(root: Path) -> Result[tuple[Path, ...], _WorktreeSweepError]:
    """Every git-registered worktree of `root`'s repository whose path
    matches the `.claude/worktrees/` dispatch convention (T-0836), parsed
    from `git worktree list --porcelain`'s stable machine-readable format
    (one blank-line-separated record per worktree, a leading `worktree
    <path>` line). Filtering to the convention means the repo's own
    primary checkout, and any worktree living elsewhere on disk, is never
    returned as a sweep candidate. `Err(ListFailed)` if the `git` call
    itself fails; never raises."""
    spawned = gitio.run_argv(
        ("git", "-C", str(root), "worktree", "list", "--porcelain")
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "tickets: worktree sweep: git worktree list --porcelain failed under %s",
            root,
        )
        return Err(_WorktreeSweepError.ListFailed)
    paths: list[Path] = []
    for block in spawned.danger_ok.stdout.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("worktree "):
                candidate = Path(line[len("worktree ") :]).resolve()
                if _is_agent_worktree_path(candidate):
                    paths.append(candidate)
                break
    return Ok(tuple(paths))


# frob:ticket T-0836
def _worktree_is_clean(path: Path) -> bool | None:
    """`True`/`False` iff `path`'s working tree has no modified or
    untracked files (`git status --porcelain` empty vs. non-empty),
    `None` if the `git` call itself failed. A caller MUST treat `None`
    the same as "dirty" -- an unresolvable clean check is never license
    to remove a worktree."""
    spawned = gitio.run_argv(("git", "-C", str(path), "status", "--porcelain"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout.strip() == ""


# frob:ticket T-0836
def _worktree_head_age_seconds(
    path: Path, *, now: datetime | None = None
) -> float | None:
    """Seconds since `path`'s HEAD commit (`git log -1 --format=%ct`), or
    `None` if unresolvable (a worktree with no commits yet, or a `git`
    failure) -- a caller MUST treat `None` conservatively here too, same
    as `_worktree_is_clean`'s `None`."""
    spawned = gitio.run_argv(("git", "-C", str(path), "log", "-1", "--format=%ct"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    try:
        committed = int(spawned.danger_ok.stdout.strip())
    except ValueError:
        return None
    except TypeError:
        # "`None` if unresolvable" (this function's own docstring) covers
        # a surprising subprocess-result shape too, not just `ValueError`
        # (EXHAUST001/EXHAUST002, T-1371).
        return None
    except Exception:
        return None
    current = now if now is not None else datetime.now(UTC)
    return current.timestamp() - committed


# frob:ticket T-0836
# frob:ticket T-1739
# frob:doc docs/guides/agent-playbook.md#12b-coordinator-worktree-cleanup-t-0836
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_no_lease_removed \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_live_lease_kept kind="unit"
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dirty_kept kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_expired_lease_clean_removed \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_dry_run_removes_nothing \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_branches_survive_removal \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_min_age_keeps_recent_worktree \
# kind="unit"
# frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_clean_no_lease_recent_head_live_process_kept  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_force_overrides_the_live_process_keep  # noqa: E501
# frob:ticket T-0601
# frob:waive AFFECT001 reason="T-2833 is a pure verbatim move out of _leases into \
# _worktree_sweep (file-level extraction, T-1103's own precedent) -- behavior, inputs, \
# outputs, and the documented contract in agent-playbook.md#12b are all unchanged; the \
# digest moved only because the function's FILE PATH changed, the same T-1162-shape \
# false positive"
def sweep_worktrees(
    root: Path,
    *,
    min_age_hours: float | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
    force: bool = False,
) -> Result[tuple[_WorktreeVerdict, ...], _WorktreeSweepError]:
    """Decide, and (unless `dry_run`) act on, a removal verdict for every
    dispatched-agent worktree under `root`'s repository (T-0836) -- the
    lease-aware fix for the incident where a raw `git worktree remove`
    hand-sweep destroyed a live agent's CLEAN worktree: git's own dirty
    check cannot see a live agent between writes, only this repo's own
    lease machinery (`read_all_leases`/`is_lease_ttl_expired`) can.

    T-1739: BEFORE any of the below, a candidate is kept (`kept:live`) if
    `scan_for_live_worktree_process` finds a live process cwd'd into it --
    this is the fix for the exactly-inverted dry-run this ticket
    documents (a clean, unleased, recently-committed worktree with a
    live agent still in it used to read as `removed`). This gate is
    UNCONDITIONAL relative to the three below: dirty/lease/age are all
    proxies for liveness, and a well-behaved agent that COMMITS ITS OWN
    WORK-IN-PROGRESS (this repo's own stall-insurance guidance) defeats
    the dirty proxy specifically -- following the guidance must never
    make a worktree MORE likely to be swept. `force=True` is the only
    override.

    A worktree is removed only if ALL of these hold:
      (0) [T-1739] no live process is cwd'd into it (unless `force`);
      (0.5) [T-1934] its CURRENT branch carries no finished-but-unlanded
          ticket work (`kept:unlanded` -- unconditional, `force` does NOT
          override this one, unlike gate 0): a worktree whose agent
          committed cleanly and died before `frob ticket land` used to
          read identical to an abandoned one under the dirty-tree proxy
          alone, which inverted the incentive (the better an agent
          behaved, the more likely it was swept). Checked before (a) so a
          CLEAN unlanded worktree is caught too, not just a dirty one.
      (a) its working tree is clean (`_worktree_is_clean` is `True` --
          `None`/unresolvable counts as dirty, never as clean);
      (b) no LIVE (unexpired) lease (`is_lease_ttl_expired`) among
          `read_all_leases(root)` is pinned to it -- an EXPIRED lease is
          treated as not live, exactly like a dead agent's abandoned
          worktree, and does not block removal.

    `min_age_hours`, if given, adds a fourth gate: a worktree whose HEAD
    commit (`_worktree_head_age_seconds`) is newer than `min_age_hours`
    (or whose age is unresolvable) is kept regardless of (a)/(b).

    `dry_run=True` computes and returns the same verdicts but never calls
    `git worktree remove` -- used by `--dry-run` to preview a sweep.
    Removal NEVER deletes a branch (`git worktree remove` alone never
    does); the branch this worktree points to survives every removal
    this function performs.

    Reuses `scan_for_live_worktree_process`/`read_all_leases`/
    `is_lease_ttl_expired`/`lease_age_seconds` directly rather than
    re-deriving liveness -- this ticket's own incident was caused by a
    sweep whose keep-criteria had no liveness check at all, not by a bug
    within the liveness machinery itself.

    `Err(ListFailed)` if `_list_agent_worktrees` itself fails; never
    raises."""
    candidates = _list_agent_worktrees(root)
    if candidates.is_err:
        return Err(candidates.danger_err)
    leases = read_all_leases(root)
    verdicts = [
        _sweep_verdict_for_worktree(
            root, candidate, leases, min_age_hours, dry_run, now, force=force
        )
        for candidate in candidates.danger_ok
    ]
    return Ok(tuple(verdicts))


# frob:ticket T-1779
# frob:doc docs/modules/tickets-landing.md#root-checkout-write-guard-t-1779
# frob:tests \
# tests/test_ticket_leases.py::TestRemoveWorktree.test_removes_a_clean_unleased_worktree
# frob:tests \
# tests/test_ticket_leases.py::TestRemoveWorktree.test_keeps_a_live_process_worktree
# frob:tests tests/test_ticket_leases.py::TestRemoveWorktree.test_refuses_a_path_not_registered_as_a_worktree  # noqa: E501
# frob:waive AFFECT001 reason="T-2833 is a pure verbatim move out of _leases into \
# _worktree_sweep (file-level extraction, T-1103's own precedent) -- behavior, inputs, \
# outputs, and the documented contract in tickets-landing.md#root-checkout- \
# write-guard-t-1779 are all unchanged; the digest moved only because the function's \
# FILE PATH changed, the same T-1162-shape false positive"
def remove_worktree(
    root: Path,
    path: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    now: datetime | None = None,
) -> Result[_WorktreeVerdict, _WorktreeSweepError]:
    """`frob worktree remove PATH` (T-1779): the single-worktree twin of
    `sweep_worktrees`, for a coordinator who wants a SAFE alternative to
    raw `git worktree remove` for ONE specific worktree, not a bulk scan.

    T-1779's incident 4: `git worktree remove` deleted a LIVE agent's
    checkout outright -- there is no way to make the raw git command
    itself refuse (T-1739's liveness gate is this repo's own invention,
    not something `git worktree remove` knows about), so the fix is
    making the SAFE path (this function, and the `frob worktree remove`
    CLI verb it powers) easier to reach than the raw command, not
    guarding the raw command itself.

    Reuses `_sweep_verdict_for_worktree` (T-1739's per-candidate liveness/
    dirty/lease/age decision) directly rather than re-deriving any of its
    gates -- a single-worktree call is exactly `sweep_worktrees`'s own
    per-candidate loop body with one candidate instead of every
    `.claude/worktrees/` entry, so the same T-1739 liveness-first
    ordering, the same `force` escape hatch, and the same failure-closed
    posture on an unresolvable clean/lease/age check all apply unchanged.

    `Err(NotARegisteredWorktree)` if `path` (resolved) is not one of
    `root`'s own git-registered worktrees under the `.claude/worktrees/`
    dispatch convention (`_is_agent_worktree_path`) -- this function will
    never act on the repository's own primary checkout or a hand-made
    worktree living elsewhere on disk, the same restriction
    `_list_agent_worktrees` already enforces for the bulk sweep.
    `Err(ListFailed)` if `git worktree list --porcelain` itself fails."""
    resolved = path.resolve()
    if not _is_agent_worktree_path(resolved):
        return Err(_WorktreeSweepError.NotARegisteredWorktree)
    candidates = _list_agent_worktrees(root)
    if candidates.is_err:
        return Err(candidates.danger_err)
    if resolved not in candidates.danger_ok:
        return Err(_WorktreeSweepError.NotARegisteredWorktree)
    leases = read_all_leases(root)
    verdict = _sweep_verdict_for_worktree(
        root, resolved, leases, None, dry_run, now, force=force
    )
    return Ok(verdict)


# frob:ticket T-1739
def _kept_live_verdict_if_process_present(candidate: Path) -> "_WorktreeVerdict | None":
    """`_sweep_verdict_for_worktree`'s T-1739 liveness gate, split out to
    stay under ARCH001's per-function line budget: `kept:live` (naming the
    pid) if `scan_for_live_worktree_process` finds a live process cwd'd
    into `candidate`, else `None` (the caller falls through to the
    dirty/lease/age gates)."""
    found = scan_for_live_worktree_process(candidate)
    if found is None:
        return None
    pid, argv = found
    argv_str = " ".join(argv) if argv else "argv unknown"
    _log.warning(
        "tickets: worktree sweep: kept %s -- pid %s has it as its cwd (%s)",
        candidate,
        pid,
        argv_str,
    )
    return _WorktreeVerdict(
        path=str(candidate), verdict="kept:live", detail=f"pid {pid}"
    )


# frob:ticket T-1934
def _kept_unlanded_verdict_if_present(
    root: Path, candidate: Path, leases: tuple["_LeaseRecord", ...]
) -> "_WorktreeVerdict | None":
    """`_sweep_verdict_for_worktree`'s T-1934 gate: `kept:unlanded` (naming
    the ticket ids) if `candidate`'s CURRENT branch carries finished-but-
    unlanded ticket work (`frob.tickets._unlanded._unlanded_findings_for_
    branch`), else `None` (the caller falls through to the dirty/lease/age
    gates). This is the fix for T-1934's own inverted-heuristic finding: a
    worktree whose agent COMMITTED its finished work cleanly and died
    before `frob ticket land` reads identical to a genuinely abandoned one
    under the dirty-tree proxy alone -- unlanded work must outrank
    cleanliness, so this gate runs BEFORE `_worktree_is_clean` is ever
    consulted, exactly mirroring how T-1739's live-process gate already
    outranks it for a different reason. Never removes anything itself;
    `dry_run` and real sweeps both just KEEP a candidate this gate flags."""
    branch_result = gitio.current_branch(candidate)
    if branch_result.is_err:
        return None
    from frob.tickets._unlanded import _unlanded_findings_for_branch

    findings = _unlanded_findings_for_branch(root, branch_result.danger_ok, leases)
    if not findings:
        return None
    ids = ",".join(sorted({finding.ticket_id for finding in findings}))
    _log.warning(
        "tickets: worktree sweep: kept %s -- branch %s carries unlanded "
        "ticket work (%s), not terminal on main",
        candidate,
        branch_result.danger_ok,
        ids,
    )
    return _WorktreeVerdict(path=str(candidate), verdict="kept:unlanded", detail=ids)


# frob:ticket T-1739
def _kept_lease_or_age_verdict(
    candidate: Path,
    leases: tuple["_LeaseRecord", ...],
    min_age_hours: float | None,
    now: datetime | None,
) -> "_WorktreeVerdict | None":
    """`_sweep_verdict_for_worktree`'s lease/age gates, split out to stay
    under ARCH001's per-function line budget: `kept:lease` if a live lease
    (`_live_lease_for_worktree`) is pinned to `candidate`, `kept:age` if
    `min_age_hours` is set and `candidate`'s HEAD commit is too recent (or
    unresolvable) to judge, else `None` (the caller proceeds to remove).
    Any surprise while judging either gate fails CLOSED to `kept:age`, the
    same removal-safety posture `sweep_worktrees`'s own docstring
    documents (EXHAUST001/EXHAUST002, T-1371)."""
    try:
        live_lease = _live_lease_for_worktree(candidate, leases, now=now)
        if live_lease is not None:
            age = lease_age_seconds(live_lease, now=now)
            age_str = f"{int(age)}s" if age is not None else "unknown-age"
            return _WorktreeVerdict(
                path=str(candidate),
                verdict="kept:lease",
                detail=f"{live_lease.ticket_id} {age_str}",
            )
        if min_age_hours is not None:
            head_age = _worktree_head_age_seconds(candidate, now=now)
            if head_age is None or head_age < min_age_hours * 3600:
                return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    except (TypeError, ValueError):
        return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    except Exception:
        return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    return None


# frob:ticket T-1739
def _sweep_verdict_for_worktree(
    root: Path,
    candidate: Path,
    leases: tuple["_LeaseRecord", ...],
    min_age_hours: float | None,
    dry_run: bool,
    now: datetime | None,
    *,
    force: bool = False,
) -> "_WorktreeVerdict":
    """One candidate worktree's removal verdict: `sweep_worktrees`'s per-
    candidate half, split from its own candidate-listing loop.

    T-1739: the LIVENESS check (a live process cwd'd into `candidate`,
    `scan_for_live_worktree_process`) runs FIRST, before the dirty/lease/
    age gates below, and unconditionally overrides them -- this is the
    exact fix for the inverted-verdict incident this ticket documents: a
    worktree that is clean, holds no lease, and has a recent HEAD commit
    (today's "remove" shape) still gets `kept:live` if a process is
    actually sitting in it, because a well-behaved agent committing its
    own work-in-progress (this repo's own stall-insurance guidance) makes
    it look identical to an abandoned one under the dirty/lease/age
    proxies alone. `force=True` (the CLI's `--force`) is the only way
    past this gate, for a worktree confirmed genuinely wedged.

    See `sweep_worktrees`'s own docstring for the dirty/lease/age gates
    below this one, in the same order as before."""
    if not force:
        live = _kept_live_verdict_if_process_present(candidate)
        if live is not None:
            return live

    # frob:ticket T-1934
    # Unlanded work outranks cleanliness -- checked BEFORE the dirty gate,
    # unconditionally (not gated by `force`: `force` overrides only the
    # T-1739 live-process gate, never this data-loss guard).
    unlanded = _kept_unlanded_verdict_if_present(root, candidate, leases)
    if unlanded is not None:
        return unlanded

    clean = _worktree_is_clean(candidate)
    if clean is not True:
        return _WorktreeVerdict(path=str(candidate), verdict="kept:dirty")

    lease_or_age = _kept_lease_or_age_verdict(candidate, leases, min_age_hours, now)
    if lease_or_age is not None:
        return lease_or_age

    if dry_run:
        return _WorktreeVerdict(
            path=str(candidate), verdict="removed", detail="dry-run"
        )

    removed = gitio.run_argv(
        ("git", "-C", str(root), "worktree", "remove", str(candidate))
    )
    if removed.is_err or removed.danger_ok.returncode != 0:
        _log.warning(
            "tickets: worktree sweep: git worktree remove failed for %s", candidate
        )
        return _WorktreeVerdict(
            path=str(candidate), verdict="kept:dirty", detail="remove-failed"
        )
    _log.info("tickets: worktree sweep removed %s", candidate)
    return _WorktreeVerdict(path=str(candidate), verdict="removed")

"""`frob ticket land` -- one-command landing (docs/modules/tickets.md#frob-ticket-land).

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check (a stale worktree base can silently drop files main already has),
squash-apply onto main, a ledger splice on conflict, close (evidence +
Done-report validation), and a conventional commit. `land()` does the
whole chain atomically, with a `--dry-run` mode that runs every check and
every git operation the real run would, then unwinds it, so a dry run can
never green-light a landing that would actually fail (T-0176).

Every abort path logs the exact manual remedy alongside its `Err` -- the
`--dry-run` output IS the incident report a human would otherwise have to
reconstruct by hand.

T-1186 split this module's merge/splice machinery into
`frob.tickets._land_merge`, its post-merge claim reverification into
`frob.tickets._land_verify`, and its finalize/squash-apply/release stage
into `frob.tickets._land_finalize` (following the verbatim-move pattern
`_evidence.py`/`_reporting.py` set at T-1171) -- this module retains the
land lock/repair-marker machinery, the `land()`/`_land_locked`
orchestrator, and the pre-merge preflight validators, importing the
split-out families back in explicitly.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._journal import _clear_intent, _write_intent
from frob.tickets._land_finalize import _land_finalize_and_close, _land_squash_apply
from frob.tickets._land_merge import (
    _abort_merge,
    _merge_main_into_worktree,
    _porcelain_dirty,
    _restore_lock_version_only_drift,
    _rev_parse,
    _uncommitted_out_of_scope_waive_deletions,
    _unowned_deletions,
    _validate_closeable,
    _wip_commit,
)

# Re-exported for `frob.tickets.__init__`'s `from frob.tickets._land import
# land, splice_ledger` -- T-1186 moved the implementation to
# `frob.tickets._land_merge`; this module keeps the public import path
# stable.
from frob.tickets._land_merge import splice_ledger as splice_ledger  # noqa: E402
from frob.tickets._land_verify import (
    _reverify_done_report_claims_post_merge,
    _reverify_evidence_post_merge,
)
from frob.tickets._models import (
    LandError,
    LandReport,
    Ticket,
)

# T-0577: same posix-only degradation as `frob.tickets._store`'s
# `ledger_lock` -- `_land_lock` degrades to a documented no-op (see its
# docstring) on a platform without `fcntl`, rather than failing import.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

# T-0577: dedicated lock file for serializing `land()` calls against the
# SAME `root`, deliberately a DIFFERENT name from `_store._lock_path`'s
# `.frob/tickets.lock`. Reusing that exact path was tried first and broke:
# a worktree's own `.frob/tickets.lock` (created the moment ANY ticket
# operation runs in the worktree, then committed into the branch by
# `land`'s own `git add -A` wip-commit/finalize-commit steps) collides,
# by identical relative path, with the untracked lock file `root`'s own
# lock would have created -- git's squash-merge refuses outright ("would
# be overwritten by merge") rather than silently picking a side. A
# distinct filename `root` never shares with anything a worktree branch
# legitimately commits sidesteps that collision entirely.
_LAND_LOCK_REL = Path(".frob") / "land.lock"


def _land_lock_path(root: Path) -> Path:
    """The advisory lock file path `_land_lock` holds, serializing every
    `land()` call against `root` (T-0577)."""
    return root / _LAND_LOCK_REL


@contextmanager
def _land_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing every `land()`
    call against `root` (T-0577) -- see `land`'s docstring for why this
    closes the REL001 version-bump-collision incident class. Degrades to a
    documented no-op (logged at WARNING) on a platform without `fcntl`,
    matching `frob.tickets._store.ledger_lock`'s same documented
    degradation."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "land: _land_lock: fcntl unavailable on this platform, lock is "
            "a NO-OP -- concurrent `land()` calls against %s are NOT "
            "serialized here",
            root,
        )
        yield
        return
    path = _land_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    _log.debug("land: _land_lock acquired (%s)", path)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("land: _land_lock released (%s)", path)


# frob:ticket T-0907
# T-0907 incident: a killed `land()` (SIGTERM/SIGKILL mid-staging) used to
# unwind root's squash-staging via a BARE `git reset --hard` (target
# defaults to whatever `HEAD` resolves to AT THAT MOMENT) -- if root's
# `HEAD`/branch ref was itself corrupted mid-run by the kill (a torn
# ref-update from an interrupted git subprocess sharing the kill's process
# group), that bare reset silently CEMENTED the corruption onto main
# instead of restoring it, observed once as a ~60-commit regression only
# caught because a human happened to check the reflog before the next
# `land` committed anything new. `_verified_reset_root`/the land-repair
# marker below close this two ways: (1) every unwind site now resets to an
# EXPLICIT sha (`pre_land_tip`, captured via `git rev-parse HEAD` once at
# THIS run's start and threaded through as a plain local value -- never
# re-derived from a possibly-corrupted `HEAD` and never stored in shared
# `.frob` state), refusing loudly instead of resetting at all if root's
# current tip has already drifted from that recorded value by the time an
# unwind runs; (2) a marker file recorded under `root`'s `.frob/` BEFORE
# `_land_squash_apply` starts mutating root survives an uncatchable
# SIGKILL (a Python signal handler cannot trap that signal at all) and is
# reconciled by `_repair_stale_land_marker` at the START of the NEXT
# `land()` call against the same `root`/ticket -- the "leave an explicit
# marker the next invocation repairs" half of the T-0907 fix requirement.
_LAND_REPAIR_DIRNAME = "land-repair"


# frob:ticket T-0907
def _land_repair_dir(root: Path) -> Path:
    """`<root>/.frob/land-repair`, where a crashed `land()`'s pre-mutation
    root tip is recorded (T-0907) so a later invocation can reconcile it."""
    return root / ".frob" / _LAND_REPAIR_DIRNAME


# frob:ticket T-0907
def _land_repair_marker_path(root: Path, ticket_id: str) -> Path:
    """The per-ticket land-repair marker path under `root` (T-0907)."""
    return _land_repair_dir(root) / f"{ticket_id}.json"


# frob:ticket T-0907
def _write_land_repair_marker(root: Path, ticket_id: str, pre_land_tip: str) -> None:
    """Record `pre_land_tip` (this run's verified pre-mutation root tip)
    under `root`'s land-repair marker for `ticket_id` (T-0907), BEFORE
    `_land_squash_apply` starts mutating `root` -- so a crash between this
    write and `_clear_land_repair_marker` (including an uncatchable
    SIGKILL) leaves a durable record of what `root`'s tip legitimately was
    before this run touched anything, for `_repair_stale_land_marker` to
    reconcile on the next `land()` call. Best-effort, like the T-0456
    intent journal: a write failure is logged but does not itself fail the
    land, since the pre-existing (pre-T-0907) safety net -- root untouched
    until `_commit_squash_apply`'s final commit -- still holds even with no
    marker recorded; the marker is an ADDITIONAL recovery aid, not the sole
    line of defense."""
    path = _land_repair_marker_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"ticket_id": ticket_id, "pre_land_tip": pre_land_tip}) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.warning(
            "land: %s could not write land-repair marker (%s) -- proceeding "
            "without the T-0907 crash-repair aid for this run",
            ticket_id,
            exc,
        )


# frob:ticket T-0907
def _clear_land_repair_marker(root: Path, ticket_id: str) -> None:
    """Remove `ticket_id`'s land-repair marker under `root`, if any
    (T-0907) -- called when `_land_squash_apply` returns for ANY reason
    (success or a clean, handled `Err`), from a `finally` block, mirroring
    `_clear_intent`'s same unconditional-cleanup shape."""
    path = _land_repair_marker_path(root, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("land: %s could not clear land-repair marker: %s", ticket_id, exc)


# frob:ticket T-0907
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
def _repair_stale_land_marker(root: Path) -> Result[None, LandError]:
    """Reconcile every leftover T-0907 land-repair marker under `root`, if
    any exist -- called at the very start of `_land_locked`, under `root`'s
    `_land_lock`, before this run captures its OWN pre-land tip.

    Scans `root`'s ENTIRE land-repair directory rather than looking up one
    marker by THIS call's own `ticket_id`: a crash can happen AFTER
    `_land_finalize_and_close` has already renumbered a draft id to its
    real sequential id (`_write_land_repair_marker` records under the id
    `_land_locked` was CALLED with, which for a draft ticket is the
    pre-finalize draft id), so a human's natural retry -- exactly the
    T-0795 `TestLandRetryAfterFinalizeThenFail` shape this reuses -- passes
    the now-finalized id, which would never match a marker filename keyed
    to the draft id it replaced. `root`'s `_land_lock` guarantees at most
    one `land()` is ever in flight against `root` at a time, so ANY marker
    found here unambiguously belongs to a fully-finished-or-crashed PRIOR
    attempt, never this one -- reconciling all of them, regardless of the
    id in this call, is always correct.

    No marker at all is the overwhelmingly common case and is a silent
    no-op (`Ok(None)`) -- most `land()` calls never crash mid-staging.

    For each marker found: if `root`'s CURRENT tip still equals the
    marker's recorded `pre_land_tip`, the crash happened before any commit
    landed on `root` (the pre-T-0907 safety net -- root is never committed
    to until `_commit_squash_apply`'s final step -- held), so this resets
    `root` to that same tip (explicit, not bare) and cleans any leftover
    staged/conflicted squash state, then clears the marker and continues to
    the next one.

    When `root`'s current tip has DRIFTED from a marker's recorded value,
    this is the exact ambiguous condition the T-0907 incident's reset
    blindly cemented -- refuses loudly (`Err(GitFailed)`) instead of
    resetting anything, naming both shas and pointing at manual
    reflog/log inspection, and leaves that marker (and any not yet
    processed) in place so the next attempt sees the same refusal until a
    human resolves it."""
    marker_dir = _land_repair_dir(root)
    if not marker_dir.is_dir():
        return Ok(None)

    for marker_path in sorted(marker_dir.glob("*.json")):
        reconciled = _reconcile_one_land_repair_marker(root, marker_path)
        if reconciled.is_err:
            return reconciled
    return Ok(None)


# frob:ticket T-0976
def _reconcile_one_land_repair_marker(
    root: Path, marker_path: Path
) -> Result[None, LandError]:
    """One T-0907 land-repair marker's reconciliation:
    `_repair_stale_land_marker`'s per-marker half, split from its
    directory-scan loop. See that function's docstring for the reset-if-
    tip-matches / refuse-if-drifted contract this implements."""
    marker_ticket_id = marker_path.stem
    try:
        raw = json.loads(marker_path.read_text(encoding="utf-8"))
        recorded_tip = str(raw["pre_land_tip"])
    except (OSError, ValueError, KeyError) as exc:
        _log.error(
            "land: found an unreadable T-0907 land-repair marker at %s "
            "(%s) -- a prior `frob ticket land %s` crashed mid-staging "
            "but its recorded pre-land tip could not be read; inspect "
            "%s and `git -C %s reflog`/`git -C %s log --oneline -5` by "
            "hand, confirm %s's tip is sound, then remove %s and retry",
            marker_path,
            exc,
            marker_ticket_id,
            marker_path,
            root,
            root,
            root,
            marker_path,
        )
        return Err(LandError.GitFailed)

    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)

    if current.danger_ok != recorded_tip:
        _log.error(
            "land: refused -- a prior `frob ticket land %s` crashed "
            "mid-staging (T-0907) with a land-repair marker recording "
            "%s's pre-land tip as %s, but %s's CURRENT tip is %s -- "
            "these differ, so the exact damage cannot be safely "
            "auto-repaired; inspect `git -C %s reflog` and `git -C %s "
            "log --oneline -5` by hand, confirm %s's tip is sound "
            "(recover with `git -C %s reset --hard <known-good-sha>` "
            "if not), then remove %s and retry",
            marker_ticket_id,
            root,
            recorded_tip,
            root,
            current.danger_ok,
            root,
            root,
            root,
            root,
            marker_path,
        )
        return Err(LandError.GitFailed)

    _log.warning(
        "land: repairing a prior crashed `frob ticket land %s` -- %s's "
        "current tip (%s) matches the recorded pre-land tip, resetting "
        "any leftover staged/conflicted state from the crashed run "
        "(T-0907)",
        marker_ticket_id,
        root,
        recorded_tip,
    )
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", recorded_tip])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    marker_path.unlink(missing_ok=True)
    _log.info(
        "land: %s T-0907 land-repair marker cleared, %s cleaned to %s",
        marker_ticket_id,
        root,
        recorded_tip,
    )
    return Ok(None)


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
# `dry_run` runs every check and every git mutation the real run would
# (merge, splice, deletion-check) then unwinds it via
# `merge --abort`/`reset --hard`, so a clean dry run is a real guarantee,
# not a guess (T-0176).
def land(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool = False,
    collected: Callable[[], frozenset[str]] | None = None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None = None,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]]
    | None = None,
    rebuild_natives: Callable[[Path], bool] | None = None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
    skip_mutation_evidence: bool = False,
) -> Result[LandReport, LandError]:
    """T-1011: `sync_gate_rules(root, pre_land_tip)`, if supplied, runs
    right after `bump_version` (same staged-but-uncommitted point) and
    decides for itself -- by diffing `pre_land_tip`..`root`'s now-squashed
    tree -- whether the landing diff touched `_KNOWN_GATE_RULES`
    (`src/frob/gates/__init__.py`); if so it runs the equivalent of `frob
    registry audit --sync-gate-rules` and stages `check-coverage.yaml`'s
    new rows into the SAME land commit, ending the manual re-sync this
    repo's own history shows drifting twice in one drive
    (docs/audits/coordination-churn.md). Returns `Ok(None)` (no-op) when
    nothing needed syncing, `Ok(rule_ids)` after a real sync, or an `Err`
    that unwinds the staged squash exactly like a `bump_version` failure.
    Defaults to `None` (skip) for the same cycle-avoidance reason as
    `bump_version`/`rebuild_natives` (docs/rework.md) -- the `frob ticket
    land` CLI supplies it by default (see `ticket_runner.py`'s `_land`).

    T-0846: `check_gate_findings` (opt-in, alongside `check_gates`) lets
    a caller with a fresh per-finding (rule id, file) oracle supply it so
    the gate-state claim re-verification can compare identities scoped to
    the ticket's own declared scope instead of a raw scope-wide count --
    see `_reverify_done_report_claims_post_merge`'s own doc for the
    masking gap this closes. Defaults to `None` (skip, same posture as
    every other D-05/T-0754 capture callable) -- falls back to the
    existing count-only comparison unchanged.

    Land `ticket_id` from `worktree` onto `root`'s current branch:
    precheck, wip-commit + merge + deletion-check, finalize + close, then
    squash-apply onto main with a conventional-commit message.

    T-0755 reviewer round 2: `skip_mutation_evidence` (default `False`) is
    the documented escape hatch for the TEST016 mutation-evidence refusal
    (`_check_mutation_evidence`) -- `frob ticket land --skip-mutation-
    evidence` sets it. Every use is logged at WARNING with the ticket id
    naming the override, matching how other land bypasses (e.g. a manual
    `frob:waive`) leave a visible trail rather than a silent skip; this is
    a deliberate escape hatch for a genuinely false-positive finding, not
    a way to make a real confirmatory-evidence problem quietly disappear.

    T-0338: `bump_version` and `rebuild_natives` let a caller fold the two
    remaining coordinator-plumbing steps (REL001 version bump/stamp, and
    a native-extension rebuild trigger) into the same one-command land
    instead of leaving them as manual follow-ups. Both are invoked AFTER
    the squash-apply is staged onto `root` (so their writes land in the
    SAME commit) but BEFORE the T-0463 completeness assertion and the
    final commit -- a failure from either unwinds the squash exactly like
    any other land failure. `bump_version(root, ticket, final_id)`
    computes and applies whatever `frob.release` says the just-squashed
    public API demands (pyproject.toml + CHANGELOG.md + `.frob-release.
    json`, all staged), returning `Ok(new_version)` if a bump was applied,
    `Ok(None)` if none was needed. `rebuild_natives(root)` is invoked only
    when the landed changeset touches a native source tree (frob-core/,
    strata-core/) and returns whether the rebuild succeeded (best-effort:
    a `False` is logged but does not fail the land, matching the T-0248
    stale-native warning's existing non-blocking severity). Both default
    to `None` (skip), matching every caller before T-0338 -- computing
    either needs `frob.release`/`frob.graph`/subprocess access
    `frob.tickets` deliberately does not have (docs/rework.md cycle-
    avoidance); the `frob ticket land` CLI supplies both by default (see
    `ticket_runner.py`'s `_land`).

    D-05: `collected`/`passed`/`covers_scope` let a caller with a fresh
    test-collection/run/graph-binding oracle re-verify the ticket's
    evidence against the POST-MERGE worktree tree (after
    `_merge_main_into_worktree` has run -- NOT the pre-merge worktree
    report `_land_precheck` validated) before it is finalized and closed,
    instead of `land` trusting whatever the worktree's `Done report`
    claims. They are CALLABLES, not precomputed values, because the
    caller cannot know the post-merge tree state before `land` has
    actually performed the merge internally -- `land` invokes them at the
    right point instead: `collected()` (no args, run against `worktree`
    after the merge) re-checks every non-cmd evidence id still resolves;
    `passed(non_cmd_evidence_ids)` (given the reloaded post-merge ticket's
    ids) returns the subset actually observed passing; `covers_scope
    (ticket)` (given the reloaded post-merge ticket) answers the D-02
    scope-binding question the same way `transition`'s own `covers_scope`
    parameter does (`True`/`False`/`None`-skip). T-0774: `_land_precheck`
    ALSO invokes `covers_scope` once more, PRE-merge, against the
    worktree's still-unmerged ticket -- a preflight simulation of this
    same D-02 question that lets a landing refuse (with git log unchanged)
    before `_land_merge_stage` ever runs `git merge`, instead of only
    discovering an uncovered scope after a merge/finalize commit already
    exists; the post-merge invocation here remains the authoritative
    re-check against the tree that will actually land. All three default to
    `None` (skip, matching every caller before D-05) since computing them
    needs `frob.testing`/`frob.graph` access `frob.tickets` deliberately
    does not have (docs/rework.md cycle-avoidance) -- a caller that sits
    above both (today, `frob.gates` for `covers_scope`'s computation, and
    the `frob ticket land` CLI, which supplies all three by default --
    see `ticket_runner.py`'s `_land`) provides them. Passing nothing
    preserves the exact pre-D-05 behavior, which is why the library
    default stays permissive even though the CLI's default is strict.

    T-0754: `check_gates()` re-runs the SAME `frob check --ticket` capture
    `frob ticket done-report` made when the Done report was written,
    against the post-merge tree, and refuses the land (`ClaimDivergence`)
    if the recorded `gate_errors` count no longer matches (warnings/waived
    are recorded but never gate the land -- review round 2 fix #1, they
    legitimately drift on a busy shared branch). The test-count half of
    the SAME claim reuses `passed`'s own post-merge run (review round 2
    fix #3 -- no second collect+run), so it is checked whenever both
    `passed` and `check_gates` are supplied, with no separate parameter of
    its own. A ticket whose Done report carries no Captured claims section
    (predates T-0754, or was written without the capture callables) is
    unaffected. `check_gates` defaults to `None` (skip, same posture as
    `collected`/`passed`) -- the `frob ticket land` CLI supplies it by
    default (see `ticket_runner.py`'s `_land`).

    T-0832: `check_gates()` returns `None` (never a negative sentinel)
    when the fresh check it ran produced no parsable gate-summary; the
    gate-state half of the claim comparison is then skipped with an
    explicit logged notice rather than comparing an unmeasured value
    against anything, and the test-count half is still checked
    independently whenever `passed` was supplied and ran successfully.

    T-0577: the ENTIRE precheck-through-squash-commit body runs under
    `root`'s dedicated `_land_lock` (a cross-process `flock`, same
    primitive family as `frob.tickets._store.ledger_lock`'s T-0458
    single-writer lock but its OWN file -- see `_land_lock`'s doc for why
    it cannot reuse `ledger_lock`'s path) -- a second `land()` against the
    SAME `root` (a different agent/coordinator process landing a different
    ticket concurrently) blocks at the lock acquire instead of racing this
    one. This is what makes the REL001 version bump (`bump_version`,
    computed against `root`'s tree from INSIDE this critical section)
    collision-free: two lands can no longer both read the same
    pre-bump manifest version and each compute the same "next" version,
    the real incident (6 version-number collisions from parallel branches
    in one session) this closes. Manual, non-`land` coordinator surgery
    that mutates `root` while holding no lock is not protected by this --
    only concurrent `land()` calls are serialized against each other."""
    root, worktree = root.resolve(), worktree.resolve()

    # T-1003 (churn item 4): `root` defaults to the invoker's cwd
    # (`ticket_runner.py`'s `_land`) -- running `frob ticket land <id>
    # --worktree <path>` from a shell sitting INSIDE the worktree (rather
    # than cd-ing out to the shared root checkout first, the "chained cd"
    # ritual this ticket retires) makes `root` resolve to the identical
    # path as `worktree`, for free, no misconfigured `--worktree` involved.
    # Resolve the TRUE primary checkout from `worktree`'s own git common
    # dir and use it instead, transparently, whenever that resolves to
    # something OTHER than `worktree` itself -- a real linked worktree,
    # which is the common case this retires the ritual for. When the
    # common-dir resolution ALSO comes back equal to `worktree` (no linked
    # worktree exists at all -- `--worktree` was pointed at the primary
    # checkout itself, the genuinely wrong configuration T-0795 introduced
    # this refusal for), `root` is left as `worktree` unchanged and
    # `_refuse_if_root_is_worktree` still refuses exactly as before.
    if root == worktree:
        resolved_root = _resolve_primary_checkout(worktree)
        if resolved_root is not None and resolved_root != worktree:
            _log.info(
                "land: %s root defaulted to the cwd inside --worktree (%s) "
                "-- resolved the primary checkout %s from its git common "
                "dir instead (T-1003), no manual cd required",
                ticket_id,
                root,
                resolved_root,
            )
            root = resolved_root

    with _land_lock(root):
        return _land_locked(
            root,
            ticket_id,
            worktree,
            dry_run=dry_run,
            collected=collected,
            passed=passed,
            covers_scope=covers_scope,
            bump_version=bump_version,
            rebuild_natives=rebuild_natives,
            sync_gate_rules=sync_gate_rules,
            check_gates=check_gates,
            check_gate_findings=check_gate_findings,
            skip_mutation_evidence=skip_mutation_evidence,
        )


# frob:waive ARCH001 reason="already the decomposed orchestrator (T-0577): delegates to _land_precheck/_land_merge_stage/_reverify_evidence_post_merge/_land_finalize_and_close/_land_squash_apply; remaining length is the try/finally intent-marker sequencing plus the D-05/T-0456 ordering-rationale comments themselves, not undecomposed logic"  # noqa: E501
# frob:ticket T-0601
# frob:ticket T-0907
def _land_locked(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool,
    collected: Callable[[], frozenset[str]] | None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None,
    covers_scope: Callable[[Ticket], bool | None] | None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    rebuild_natives: Callable[[Path], bool] | None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
    skip_mutation_evidence: bool = False,
) -> Result[LandReport, LandError]:
    """`land`'s actual body (T-0577), run by the caller already holding
    `root`'s `ledger_lock` -- split out only so `land`'s docstring can state
    the locking contract once at the public entry point rather than
    interleaved with the implementation.

    T-0907: before anything else, reconciles a leftover land-repair marker
    for `ticket_id` (a prior `land()` against this same `root` that crashed
    mid-staging, see `_repair_stale_land_marker`'s own doc), then captures
    THIS run's own verified pre-mutation root tip (`root_pre_land_tip`) as
    a plain local value -- never re-derived from `root`'s possibly-stale
    `HEAD` later, and never stored in shared `.frob` state -- threaded
    through to `_land_squash_apply` (the only step that mutates `root`) so
    every unwind there resets to this exact sha instead of a bare `git
    reset --hard`."""
    repaired = _repair_stale_land_marker(root)
    if repaired.is_err:
        return Err(repaired.danger_err)

    root_pre_land_tip = _rev_parse(root, "HEAD")
    if root_pre_land_tip.is_err:
        return Err(root_pre_land_tip.danger_err)

    precheck = _land_precheck(
        root,
        worktree,
        ticket_id,
        covers_scope=covers_scope,
        skip_mutation_evidence=skip_mutation_evidence,
    )
    if precheck.is_err:
        return Err(precheck.danger_err)
    ticket, main_branch_name = precheck.danger_ok

    # T-0456: record that a multi-step land is starting BEFORE any of the
    # steps below mutate the worktree/root -- cleared in the `finally` below
    # on every exit (success or a clean, handled Err) so a marker that
    # OUTLIVES this process means it crashed mid-land, the condition `frob
    # ticket reconcile` surfaces as an anomaly instead of it going unnoticed.
    _write_intent(root, ticket_id, worktree)
    try:
        stage = _land_merge_stage(
            root, worktree, ticket, ticket_id, main_branch_name, dry_run
        )
        if stage.is_err:
            return Err(stage.danger_err)
        wip_committed, did_merge, dry_run_report = stage.danger_ok

        # T-0754 review round 2 fix #4: refresh the pre-work sweep BEFORE
        # any inner check runs `check_gates()` (a live `frob check
        # --ticket` spawn) -- landing can pull in unrelated main-side
        # commits that touch the ticket's scope globs, moving the sweep's
        # scope digest out from under it (see `_refresh_prework_sweep`'s
        # own doc, T-0236); done AFTER that check instead, `check_gates()`
        # would observe a stale-sweep PRE001 the Done report's captured
        # claim never carried, refusing the land on a false divergence.
        # Only for a REAL land (`dry_run_report is None` -- the exact same
        # condition the unconditional call below already required, since a
        # dry run always returns before reaching it): a dry run must still
        # leave the worktree exactly as found, and this call's write is
        # not itself unwound the way the merge commit is.
        if dry_run_report is None:
            _refresh_prework_sweep(worktree, ticket)

        # D-05: re-verify BEFORE the dry-run early return -- otherwise a
        # `--dry-run` would report clean without ever running the
        # post-merge check, defeating T-0176's "a clean dry run is a real
        # guarantee, not a guess" design intent.
        post_merge_check = _reverify_evidence_post_merge(
            worktree, ticket_id, collected, passed
        )
        if post_merge_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(post_merge_check.danger_err)
        passing_ids = post_merge_check.danger_ok

        # T-0754: re-verify captured Done-report claims (test count, gate
        # state) against the SAME post-merge tree `post_merge_check` just
        # re-verified evidence against -- same ordering rationale (before
        # the dry-run early return, so `--dry-run` stays a real guarantee).
        # T-0754 review round 2 fix #3: the test-count half is DERIVED from
        # `passing_ids` (the exact set D-05's own `passed()` run just
        # computed above), never a second collect+run -- halves the real
        # cost of a `run_tests`-supplying land.
        claims_check = _reverify_done_report_claims_post_merge(
            worktree, ticket_id, passing_ids, check_gates, check_gate_findings
        )
        if claims_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(claims_check.danger_err)

        if dry_run_report is not None:
            return Ok(dry_run_report)

        finalized = _land_finalize_and_close(
            root,
            worktree,
            ticket_id,
            did_merge,
            main_branch_name,
            covers_scope=covers_scope,
        )
        if finalized.is_err:
            return Err(finalized.danger_err)
        final_id = finalized.danger_ok

        # T-0907: the land-repair marker is written right before the ONLY
        # step that mutates `root` (`_land_squash_apply`) and cleared in
        # this inner `finally` on any exit -- an uncatchable SIGKILL
        # between these two points leaves the marker for
        # `_repair_stale_land_marker` to reconcile on the NEXT `land()`
        # call, closing the "leave an explicit marker the next invocation
        # repairs" half of the T-0907 fix requirement.
        _write_land_repair_marker(root, ticket_id, root_pre_land_tip.danger_ok)
        try:
            return _land_squash_apply(
                root,
                worktree,
                ticket,
                ticket_id,
                final_id,
                wip_committed,
                did_merge,
                main_branch_name,
                pre_land_tip=root_pre_land_tip.danger_ok,
                bump_version=bump_version,
                rebuild_natives=rebuild_natives,
                sync_gate_rules=sync_gate_rules,
            )
        finally:
            _clear_land_repair_marker(root, ticket_id)
    finally:
        _clear_intent(root, ticket_id)


def _refuse_if_main_dirty(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(DirtyMain)` if `root` has any uncommitted change.

    Tolerates one specific shape of "dirty" without refusing (T-0793):
    `uv.lock`'s frob-version line flapping on its own, with nothing else
    in the tree touched, from a prior `uv run`/`uv lock` invocation
    against a pyproject a sibling land already bumped. That case is
    auto-restored (`git checkout -- uv.lock`) before the dirty check is
    re-evaluated, rather than refusing the land -- any OTHER dirt (a real
    lock change, any other file) is left alone and still refuses exactly
    as before."""
    main_dirty = _porcelain_dirty(root)
    if main_dirty.is_err:
        return Err(main_dirty.danger_err)
    if main_dirty.danger_ok and _restore_lock_version_only_drift(root):
        _log.info(
            "land: %s auto-restored a uv.lock frob-version-only drift in "
            "%s before the DirtyMain check (T-0793)",
            ticket_id,
            root,
        )
        main_dirty = _porcelain_dirty(root)
        if main_dirty.is_err:
            return Err(main_dirty.danger_err)
    if main_dirty.danger_ok:
        _log.error(
            "land: %s refused -- %s has uncommitted changes; commit or stash "
            "them first (git -C %s status), then retry `frob ticket land %s "
            "--worktree %s`",
            ticket_id,
            root,
            root,
            ticket_id,
            worktree,
        )
        return Err(LandError.DirtyMain)
    return Ok(None)


# frob:ticket T-0795
# frob:ticket T-1003
# frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_a_real_linked_worktree_resolves_and_lands kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_the_primary_checkout_itself_still_refuses kind="integration"  # noqa: E501
def _resolve_primary_checkout(worktree: Path) -> Path | None:
    """The primary checkout for `worktree`'s clone -- the parent directory
    of `git -C worktree rev-parse --git-common-dir` -- or `None` if that
    git call fails (an unreadable/non-git path; the caller then leaves
    `root` unchanged and downstream checks handle it exactly as before
    this ticket).

    Every git worktree (linked or primary) shares ONE common `.git` dir,
    owned by the primary checkout; `--git-common-dir` is git's own,
    authoritative answer to "where is that," regardless of which worktree
    the command runs from or what the caller's cwd happens to be -- this
    is what lets `land` (T-1003, churn item 4) resolve the true root from
    `worktree` alone, without the caller needing to know or pass it. A
    PRIMARY checkout's own common dir is simply its own `.git`, so calling
    this on a primary checkout returns that same checkout back unchanged
    (the genuinely-no-worktree case `_refuse_if_root_is_worktree` still
    needs to catch)."""
    common_dir = run_argv(["git", "-C", str(worktree), "rev-parse", "--git-common-dir"])
    if common_dir.is_err or common_dir.danger_ok.returncode != 0:
        return None
    raw = common_dir.danger_ok.stdout.strip()
    if not raw:
        return None
    common_dir_path = Path(raw)
    resolved = (
        common_dir_path.resolve()
        if common_dir_path.is_absolute()
        else (worktree / common_dir_path).resolve()
    )
    return resolved.parent


# frob:waive DUP001 reason="T-1186 split-induced false positive: the DUP001 template \
# similarity heuristic matches this guard clause against frob.serve.__getattr__ and \
# frob.strata._threat._flow_completeness_gap purely on control-flow shape (an \
# early-return equality check) -- neither shares this function's domain (refusing a \
# land whose root/worktree paths chain to the same checkout); this function's file \
# location did not move in T-1186, but the split changed which OTHER symbols in this \
# module the DUP scan pairs it against, surfacing a pre-existing pairing freshly"
def _refuse_if_root_is_worktree(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(IncompleteLand)`, logged with the ACTUAL mistake named, if
    `root` and `worktree` (both already `.resolve()`d by `land`) are the
    identical path (T-0795).

    Before this check, that exact condition (root == worktree) fell
    through all the way to `_worktree_full_changeset`'s much later T-0640/
    T-0761 diagnosis ("`--worktree` almost certainly points at the SAME
    checkout/branch `root` has checked out ... create a real feature
    branch") -- correct for a worktree genuinely pointed at the wrong
    branch, but misleading for the far more common real cause: `root`
    defaults to `cfg.ticket_path or Path(".")` (the invoker's CWD), so
    running `frob ticket land <id> --worktree <path>` from A SHELL SITTING
    INSIDE THE WORKTREE (rather than the shared root checkout) makes
    `root` resolve to `worktree` for free, no misconfigured `--worktree`
    involved. Refusing here, before `_land_merge_stage` runs any git
    mutation, names the actual mistake immediately instead of sending an
    agent chasing the T-0640 "create a real feature branch" remedy for a
    worktree that was never the problem. Reuses `LandError.IncompleteLand`
    (no new enum variant -- both are "this land cannot proceed as
    configured, nothing was committed" outcomes; the log message, not the
    enum tag, carries the corrected diagnosis) rather than the true-
    same-branch check (`_worktree_full_changeset`'s merge-base-equals-HEAD
    test), which still fires unchanged for a distinct-but-branchless
    worktree path further down the pipeline."""
    if root != worktree:
        return Ok(None)
    _log.error(
        "land: %s refused -- root (%s) and --worktree (%s) resolve to the "
        "IDENTICAL path. This is almost always caused by running `frob "
        "ticket land` from a shell whose cwd is INSIDE the worktree "
        "(`root` defaults to cwd) rather than a --worktree pointed at the "
        "wrong branch. Run `frob ticket land %s --worktree %s` from the "
        "ROOT checkout instead -- cd out of %s first, then retry",
        ticket_id,
        root,
        worktree,
        ticket_id,
        worktree,
        worktree,
    )
    return Err(LandError.IncompleteLand)


# frob:ticket T-1323
def _check_uncommitted_waive_deletions(
    worktree: Path, ticket: Ticket, ticket_id: str
) -> Result[None, LandError]:
    """`Err(OutOfScopeWaiveDeletion)` if `worktree`'s UNCOMMITTED changes
    (against `HEAD`, before `_wip_commit` ever runs) delete a `frob:waive`
    directive whose file is neither in `ticket.scope` nor named/declared in
    `ticket.body`'s Done report -- the 2026-07-29 incident's own
    laundering path: a wip-snapshot commit folds unattributed uncommitted
    edits into the merge, and nothing before this check ever inspected
    what a wip-commit was ABOUT to capture. Runs at `_land_precheck` time,
    strictly before any git mutation (`_wip_commit`/`_merge_main_into_
    worktree`), so the refusal fires with the worktree still dirty and
    untouched -- nothing to unwind, unlike `_check_unowned_deletions`
    (which necessarily runs post-merge and aborts a staged merge on
    refusal)."""
    found = _uncommitted_out_of_scope_waive_deletions(worktree, ticket)
    if found.is_err:
        return Err(found.danger_err)
    if found.danger_ok:
        _log.error(
            "land: %s refused -- worktree has uncommitted frob:waive "
            "deletion(s) outside scope %s and undeclared by the Done "
            "report: %s. If intentional, add the file to the ticket's "
            "scope or name it/the rule in the Done report; if accidental, "
            "restore it: cd %s && git checkout -- <file> ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            [f"{file}:{rule}" for file, rule in found.danger_ok],
            worktree,
            ticket_id,
            worktree,
        )
        return Err(LandError.OutOfScopeWaiveDeletion)
    return Ok(None)


def _validate_scope_covered_preflight(
    ticket: Ticket, covers_scope: Callable[[Ticket], bool | None] | None
) -> Result[None, LandError]:
    """`Err(NotCloseable)` if `covers_scope(ticket)` answers `False` against
    the PRE-merge worktree ticket (T-0774): D-05's `covers_scope` callable
    was previously only ever invoked POST-merge (`_land_finalize_and_close`,
    against the graph rebuilt from the just-merged tree, after `git commit`
    had already made a merge commit) -- correct for the graph itself
    (`frob.gates` needs the post-merge tree to know what actually landed),
    but it left a residual fail-after-merge class T-0763's acceptance/
    evidence preflight did not close: a ticket whose evidence is bound but
    does not cover its own scope still merged+committed before failing.

    Invoking the SAME callable again here, before `_land_merge_stage` ever
    runs `git merge`, is a PREFLIGHT SIMULATION against the pre-merge
    worktree tree, not a replacement for the post-merge re-check
    `_land_finalize_and_close` still performs unconditionally afterward --
    for the common case (the ticket's scope files are untouched by any
    concurrent main-side change), the pre-merge tree already answers the
    same D-02 scope-binding question, so a landing whose evidence does not
    cover its scope now refuses here, with git log unchanged on both sides,
    instead of only after a merge/finalize commit already exists. A
    concurrent main-side edit to a scope file between this preflight and
    the real merge can still only be caught by the existing post-merge
    check, which is untouched by this addition. `covers_scope=None` (skip,
    matching every caller before D-02) or a `True`/`None` answer leaves this
    preflight silent, exactly like the post-merge check's own tri-state
    contract (`_done_transition_guard`)."""
    if covers_scope is None:
        return Ok(None)
    if covers_scope(ticket) is False:
        _log.error(
            "land: %s cannot land -- no evidence id covers a touched/scope "
            "symbol (scope=%s); bind evidence to the uncovered scope "
            "(`frob ticket evidence %s <node-id>...`) and retry "
            "`frob ticket land %s`",
            ticket.id,
            list(ticket.scope),
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


def _check_mutation_evidence(
    worktree: Path,
    ticket: Ticket,
    base_ref: str,
    *,
    skip: bool = False,
) -> Result[None, LandError]:
    """T-0755: run the diff-scoped adversarial evidence obligation
    (`frob.gates.mutation_evidence_violations`) against `ticket`'s current
    worktree tree.

    A `security`/`bug`-kind ticket whose bound evidence killed zero
    mutants (TEST016 at ERROR severity, see `frob.gates._mutation_evidence`'s
    module docstring for why that severity split, not the ratchet-pool
    mechanism, is the right tool here) REFUSES the land -- the same
    "knowable before any git mutation" posture `_validate_closeable` and
    `_validate_scope_covered_preflight` already hold. Every other kind's
    TEST016 finding (WARN) is logged and does NOT block: the obligation
    text calls WARN "a TEST-family warning," not a hard gate, for those
    kinds. `Err(MutationEvidenceError.ExecDisabled)` (surfaced as an empty
    violation tuple by `mutation_evidence_violations`, T-0803's honest-
    empty-is-not-a-pass posture) and any other check failure are logged
    and treated as non-blocking -- this obligation augments the existing
    evidence gates, it does not replace their own hard-fail paths if the
    mutation subsystem itself cannot run.

    `skip=True` (T-0755 reviewer round 2, `frob ticket land
    --skip-mutation-evidence`) is the documented escape hatch: the check
    still RUNS (so its findings are still logged and visible) but never
    refuses the land. Every use is logged at WARNING naming the ticket, so
    a bypass always leaves a trail -- this is for a genuinely false-
    positive finding (e.g. a mutation-testing gap the reviewer has not yet
    closed), never a silent way to wave through real confirmatory
    evidence."""
    from frob.gates import mutation_evidence_violations

    violations = mutation_evidence_violations(worktree, ticket, base_ref)
    if not violations:
        return Ok(None)
    errors = [v for v in violations if v.severity == "error"]
    for v in violations:
        _log.warning("land: %s TEST016 %s", ticket.id, v.message)
    if errors and skip:
        _log.warning(
            "land: %s --skip-mutation-evidence set -- %d ERROR-severity "
            "TEST016 finding(s) logged above are NOT blocking this land "
            "(justification required: this bypass is for a genuinely "
            "false-positive finding, never a way to wave through real "
            "confirmatory evidence)",
            ticket.id,
            len(errors),
        )
        return Ok(None)
    if errors:
        _log.error(
            "land: %s cannot land -- %d confirmatory-only evidence finding(s) "
            "at ERROR severity (kind=%s); remedies: (1) strengthen the "
            "named evidence tests so at least one fails on a mutant of the "
            "changed lines (see the TEST016 lines above for exact "
            "file:line + mutation), then retry `frob ticket land %s`; or "
            "(2) if this is a genuine false positive, retry with `frob "
            "ticket land %s --skip-mutation-evidence` (logs a loud, "
            "justification-required override, does not suppress the "
            "finding)",
            ticket.id,
            len(errors),
            ticket.kind,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.EvidenceConfirmatoryOnly)
    return Ok(None)


def _check_live_tracker_citations(
    worktree: Path, ticket: Ticket, base_ref: str
) -> Result[None, LandError]:
    """T-0854: refuse to land while a registry `deferred:`/`tracked_by:`
    disposition or a waiver `ticket=` attribute in `worktree`'s tree still
    cites `ticket.id` as its live tracker, AND that exact citation already
    existed unchanged at `base_ref` (`frob.tickets._live_tracker.
    live_tracker_citations`'s diff-aware grep-shaped scan, T-0854 rework)
    -- the T-0605-orphaned-41-rows incident class, caught BEFORE the merge
    that makes those citations stale, not one `frob check` later. A
    citation this same diff freshly introduces (never present at
    `base_ref`) is not reported -- see the T-0854 rework note in
    `frob.tickets._live_tracker`'s module docstring for why a scope-based
    exemption was rejected as gameable in favor of this diff-aware one."""
    from frob.tickets._live_tracker import live_tracker_citations

    citations = live_tracker_citations(worktree, ticket.id, base_ref=base_ref)
    if not citations:
        return Ok(None)
    _log.error(
        "land: %s cannot land -- %d site(s) still cite it as their live "
        "tracker (registry deferred:/tracked_by: disposition or a waiver "
        "ticket= attribute): %s -- file a successor ticket and re-point "
        "these rows, or re-point them in this same change, then retry "
        "`frob ticket land %s`",
        ticket.id,
        len(citations),
        list(citations),
        ticket.id,
    )
    return Err(LandError.LiveTrackerCited)


def _land_precheck(
    root: Path,
    worktree: Path,
    ticket_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
    skip_mutation_evidence: bool = False,
) -> Result[tuple[Ticket, str], LandError]:
    """Refuse on root/worktree being the same path (T-0795) or a dirty
    main, load+validate the worktree's ticket is closeable (including,
    T-0774, a `covers_scope` preflight simulation, T-0755's diff-scoped
    mutation-evidence obligation, bypassable via `skip_mutation_evidence`,
    and T-0854's live-tracker-citation preflight), and resolve main's
    current branch name -- everything `land` must check BEFORE any git
    mutation."""
    from frob.tickets import _load_one

    same_path_check = _refuse_if_root_is_worktree(root, worktree, ticket_id)
    if same_path_check.is_err:
        return Err(same_path_check.danger_err)

    dirty_check = _refuse_if_main_dirty(root, worktree, ticket_id)
    if dirty_check.is_err:
        return Err(dirty_check.danger_err)

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error("land: %s not found in worktree store at %s", ticket_id, worktree)
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok

    validated = _validate_closeable(ticket)
    if validated.is_err:
        return Err(validated.danger_err)

    waive_deletion_check = _check_uncommitted_waive_deletions(
        worktree, ticket, ticket_id
    )
    if waive_deletion_check.is_err:
        return Err(waive_deletion_check.danger_err)

    scope_preflight = _validate_scope_covered_preflight(ticket, covers_scope)
    if scope_preflight.is_err:
        return Err(scope_preflight.danger_err)

    main_branch = current_branch(root)
    if main_branch.is_err:
        return Err(LandError.GitFailed)

    live_tracker_check = _check_live_tracker_citations(
        worktree, ticket, main_branch.danger_ok
    )
    if live_tracker_check.is_err:
        return Err(live_tracker_check.danger_err)

    mutation_check = _check_mutation_evidence(
        worktree,
        ticket,
        main_branch.danger_ok,
        skip=skip_mutation_evidence,
    )
    if mutation_check.is_err:
        return Err(mutation_check.danger_err)

    return Ok((ticket, main_branch.danger_ok))


def _land_merge_stage(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    dry_run: bool,
) -> Result[tuple[bool, bool, LandReport | None], LandError]:
    """wip-commit, merge main into the worktree, and check for unowned
    deletions; returns `(wip_committed, did_merge, dry_run_report)` where
    `dry_run_report` is the early-return report for a clean dry run, else
    `None`."""
    wip = _wip_commit(worktree, ticket_id, dry_run=dry_run)
    if wip.is_err:
        return Err(wip.danger_err)
    wip_committed = wip.danger_ok

    merged = _merge_main_into_worktree(root, worktree, ticket, main_branch_name)
    if merged.is_err:
        return Err(merged.danger_err)
    did_merge = merged.danger_ok

    unowned_check = _check_unowned_deletions(
        root, worktree, ticket, ticket_id, main_branch_name, did_merge
    )
    if unowned_check.is_err:
        return Err(unowned_check.danger_err)

    if not dry_run:
        return Ok((wip_committed, did_merge, None))

    report = _dry_run_report(
        worktree, ticket_id, main_branch_name, wip_committed, did_merge
    )
    return Ok((wip_committed, did_merge, report))


# frob:ticket T-0236
def _refresh_prework_sweep(worktree: Path, ticket: Ticket) -> None:
    """Re-record `ticket`'s pre-work sweep against the just-merged worktree
    state, post-merge and pre-close.

    Landing can pull in unrelated main commits that touch the ticket's scope
    globs, moving the recorded sweep's scope digest out from under it -- if
    `land` then fails before reaching close (evidence or Done-report issue),
    the ticket is left in-progress carrying a sweep that `frob check`'s
    PRE001 will flag as stale on the very next check, even though nothing
    about THIS ticket's own work was actually un-swept (T-0236). Refreshing
    here, unconditionally, before the close attempt below means a retried
    land (or a reviewer's `frob check --ticket` in the interim) sees a sweep
    that matches the current tree, not a stale one caused by drift outside
    this ticket's control.

    Best-effort: a refresh failure is logged and does not block landing --
    the close step's own evidence/Done-report gates are what actually gate
    `land`, not this sweep's freshness.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(worktree, ticket)
    if swept.is_err:
        _log.warning(
            "land: %s post-merge pre-work sweep refresh failed (%s) -- "
            "PRE001 may report staleness until `frob ticket sweep %s` "
            "is run manually",
            ticket.id,
            swept.danger_err,
            ticket.id,
        )


def _dry_run_report(
    worktree: Path,
    ticket_id: str,
    main_branch_name: str,
    wip_committed: bool,
    did_merge: bool,
) -> LandReport:
    """Abort any staged merge and build the early-return `LandReport` for a
    clean dry run."""
    if did_merge:
        _abort_merge(worktree)
    _log.info(
        "land: %s dry-run clean -- would merge=%s, would close, would "
        "squash-apply onto %s",
        ticket_id,
        did_merge,
        main_branch_name,
    )
    return LandReport(
        ticket_id=ticket_id,
        final_id=ticket_id,
        dry_run=True,
        wip_committed=wip_committed,
        merged_main_into_worktree=did_merge,
        ledger_spliced=did_merge,
        unowned_deletions=(),
    )


def _check_unowned_deletions(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    did_merge: bool,
) -> Result[None, LandError]:
    """`Err(UnownedDeletions)` (aborting the merge first) if the worktree
    deletes any file outside `ticket.scope`."""
    unowned = _unowned_deletions(root, worktree, ticket.scope, main_branch_name)
    if unowned.is_err:
        if did_merge:
            _abort_merge(worktree)
        return Err(unowned.danger_err)
    if unowned.danger_ok:
        if did_merge:
            _abort_merge(worktree)
        _log.error(
            "land: %s refused -- worktree deletes file(s) outside its scope "
            "%s: %s. If intentional, add the path(s) to the ticket's scope; "
            "if accidental (a stale worktree base), restore them: "
            "cd %s && git checkout %s -- %s ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            list(unowned.danger_ok),
            worktree,
            main_branch_name,
            " ".join(unowned.danger_ok),
            ticket_id,
            worktree,
        )
        return Err(LandError.UnownedDeletions)
    return Ok(None)

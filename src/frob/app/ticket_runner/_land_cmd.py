"""frob.app.ticket_runner._land_cmd -- the `land`/`merge-driver` command
family (T-1090/T-1078's atomic id-allocation and REL bump paths carried).

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok

from frob.app.config import AppConfig
from frob.gitio import run_argv, working_diff
from frob.logging import get_logger
from frob.process._guard import ProcessGuardError
from frob.tickets._land_git_ops import _describe_git_failure, _land_internal_git_env
from frob.tickets._leases import refuse_if_worktree_in_use

from ._verify import (
    _check_gate_findings_fn,
    _check_gates_summary_fn,
    _parse_error_findings_from_stdout,
    _python_for_tree,
    _shared_check_spawn_fn,
)

_log = get_logger("frob.app.ticket_runner")


# frob:ticket T-1437
# frob:tests tests/test_ticket_merge_driver.py::TestMergeDriverViaRealGit.test_merge_driver_reads_archived_ids_from_merge_head_not_stale_disk  # noqa: E501
# frob:tests tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver.test_not_mid_merge_falls_back_to_disk_based_archived_ids  # noqa: E501
def _archived_ids_for_merge_driver(root: Path) -> frozenset[str]:
    """T-1437 fix: `frob ticket merge-driver`'s archive-resurrection guard
    used to call `frob.tickets._land_git_ops._archived_ids(root)`, a plain
    disk read of `root`'s CURRENT `tickets-archive.md` -- but during a
    LIVE git merge (this function's only real caller: git invokes the
    merge driver as a subprocess mid-merge, one call per conflicting
    path), git does not write any path's resolved merge content back to
    the actual working-tree file until the entire merge machinery
    finishes; it only ever hands a driver invocation three TEMP files
    (`%O`/`%A`/`%B`) for the ONE path it is resolving. So a disk read of
    `tickets-archive.md` from inside a `tickets.md` merge-driver
    invocation always sees the PRE-merge archive, even if a sibling
    invocation is concurrently resolving `tickets-archive.md` itself (both
    paths are registered to `merge=frob-ledger` in `.gitattributes`) --
    the exact T-1437 incident: `frob ticket archive` ran on `main` after a
    worktree branched, and every subsequent `git merge main` inside that
    worktree resurrected the just-archived id into `tickets.md`, because
    `_archived_ids(root)` could not see main's new archive content yet.

    This resolves archived ids from GIT OBJECTS instead of the working
    tree: `HEAD` (`ours`) and `MERGE_HEAD` (`theirs`, the commit-ish git
    sets for the in-progress merge this driver is running inside of) each
    have a real, committed `tickets-archive.md` blob regardless of what
    the working tree currently shows -- `git show <ref>:tickets-archive.md`
    reads it directly from the object store, sidestepping the working-tree
    staleness entirely. The union of ids parsed from BOTH refs is
    returned, so a ticket archived on EITHER side is treated as archived.
    Degrades to the old disk-based `_archived_ids(root)` (still correct
    for `frob ticket land`'s own non-live-merge internal splice calls,
    section 9 of this repo's `docs/guides/agent-playbook.md`) whenever
    `MERGE_HEAD` cannot be resolved (not currently inside a git merge --
    the ordinary case for every OTHER caller of this helper's underlying
    machinery) or either ref's archive content fails to parse."""
    from frob.tickets._land_git_ops import _archived_ids
    from frob.tickets._land_git_ops import _read_text_at_ref as _show_at_ref
    from frob.tickets._store import _parse_ledger

    merge_head = run_argv(["git", "-C", str(root), "rev-parse", "MERGE_HEAD"])
    if merge_head.is_err or merge_head.danger_ok.returncode != 0:
        return _archived_ids(root)
    theirs_ref = merge_head.danger_ok.stdout.strip()
    if not theirs_ref:
        return _archived_ids(root)

    ours_text = _show_at_ref(root, "HEAD", "tickets-archive.md")
    theirs_text = _show_at_ref(root, theirs_ref, "tickets-archive.md")

    ids: set[str] = set()
    for text in (ours_text, theirs_text):
        if text is None:
            continue
        parsed = _parse_ledger(text)
        if parsed.is_ok:
            ids.update(parsed.danger_ok)
    if not ids:
        # Neither ref's archive parsed/existed -- degrade to the disk
        # read rather than claim "nothing is archived" on a parse failure
        # this helper cannot itself distinguish from "genuinely empty".
        return _archived_ids(root)
    return frozenset(ids)


# frob:ticket T-1404
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_out_of_scope_file_with_noncanonical_directive_is_left_untouched  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_in_scope_file_with_noncanonical_directive_is_still_fixed  # noqa: E501
def _land_touched_paths(worktree: Path, ticket_id: str) -> frozenset[str] | None:
    """The landing ticket's touched-file set, root-relative -- `working_
    diff(worktree, "main")`'s own hunk files, the same diff-scoped
    touched-set source FMT001's own gate (`_fmt001_touched_lines`,
    `frob.gates._todo_fmt`) already uses to decide which lines are "this
    ticket's own", rather than the ticket's declared `scope` globs
    resolved to real paths (a real diff is exact; a glob resolution can
    both over- and under-match against what actually changed). `None`
    when the diff cannot be computed (no merge-base, detached HEAD, a
    `git` spawn failure) -- the caller degrades to the pre-T-1404 whole-
    tree behaviour rather than guess at a touched set it cannot verify."""
    diff_result = working_diff(worktree, "main")
    if diff_result.is_err:
        _log.warning(
            "ticket land: %s could not compute touched-file set for the "
            "pre-land FMT001 fix (%s) -- falling back to a whole-tree pass",
            ticket_id,
            diff_result.danger_err,
        )
        return None
    return frozenset(hunk.file for hunk in diff_result.danger_ok.hunks)


# frob:ticket T-1175
# frob:ticket T-1404
# frob:ticket T-1903
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_fmt_half_canonicalizes_a_non_canonical_directive  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_out_of_scope_file_with_noncanonical_directive_is_left_untouched  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes.test_in_scope_file_with_noncanonical_directive_is_still_fixed  # noqa: E501
def _absorb_pre_land_fixes(worktree: Path, ticket_id: str) -> None:
    """`frob ticket land`'s T-1175 absorption step: run `frob fmt`
    (directive canonicalization) and the T-1138 Tier-A deterministic
    auto-fix handlers against `worktree`, BEFORE `land()`'s own merge/
    wip-commit runs. Any file either of these two rewrites becomes an
    ordinary uncommitted change in `worktree`, picked up by `land()`'s
    existing `_do_wip_commit` step exactly like a change the agent typed
    by hand -- no new commit path, no new subsystem, per the T-1175
    absorb-not-add directive. Every step here is IN-PROCESS (no `frob
    fmt` subprocess spawn) -- `format_paths`/`apply_tier_a_fixes` are the
    exact functions those CLI commands themselves call, reused directly.
    Best-effort: either step's own failure (an unloadable queue) is
    logged and skipped rather than refusing the land -- these are
    auto-fix conveniences, not a land precondition.

    T-1870: this used to also run `frob sys sync-interface` (interface=
    drift auto-write) as a third absorbed step -- deleted along with the
    rest of that machinery, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface. What replaces
    it is NOT an auto-fix: `_assert_design_loads_pre_land`, called
    separately below (not part of this best-effort trio -- it can refuse
    the land outright), keeps the ONE property from the old step that
    protects OTHER agents rather than just this change (T-1686's
    damages-others rule for what stays synchronous): that `design/
    frob.strata` still PARSES before this land can commit on top of it.

    T-1903: `_assert_design_loads_pre_land` is called TWICE -- once here,
    before `_tier_a_pre_land_step`, and once again immediately after it.
    The first call only proves the design root was already healthy going
    in (useful for a clearer error message pointing at pre-existing
    breakage); it CANNOT catch corruption `_tier_a_pre_land_step` itself
    introduces, because it runs before that rewrite exists. The T-1900
    incident is exactly this: a Tier-A handler (SYS-IFACE-ORDER)
    re-rendered `design/frob.strata` into an unparseable block, the
    before-call had already passed, and nothing after the rewrite ever
    re-checked -- the land printed 'strata parse failed' to stderr and
    STILL reported `LAND-PROOF verified=True`. The second call below is
    the load-bearing one: it is what makes a corrupting Tier-A handler
    structurally unable to publish, not just the one handler T-1900
    happened to fix."""
    touched_paths = _land_touched_paths(worktree, ticket_id)
    _fmt_pre_land_step(worktree, ticket_id, touched_paths)
    _assert_design_loads_pre_land(worktree, ticket_id, stage="pre-tier-a")
    _tier_a_pre_land_step(worktree, ticket_id, touched_paths)
    _assert_design_loads_pre_land(worktree, ticket_id, stage="post-tier-a")


# frob:ticket T-1404
def _fmt_pre_land_step(
    worktree: Path, ticket_id: str, touched_paths: frozenset[str] | None
) -> None:
    """The fmt half of `_absorb_pre_land_fixes`. T-1404: scoped to this
    ticket's own touched-file set when it can be computed -- the pre-T-1404
    whole-tree `format_paths(worktree, ...)` call rewrote ANY non-canonical
    `frob:` directive anywhere in the tree, including files entirely
    outside the landing ticket's own diff (the land-scope-discipline
    collision T-1391 diagnosed but did not wire a fix for). Falls back to
    the old whole-tree call when the touched set could not be computed
    (`touched_paths is None`) -- degrading to the pre-T-1404 behaviour,
    never silently skipping the fix outright."""
    from frob.gates._fmt_directives import format_paths, read_line_length

    limit = read_line_length(worktree)
    if touched_paths is None:
        fmt_report = format_paths(worktree, check_only=False, limit=limit)
        fmt_changed = len(fmt_report.changes)
    else:
        fmt_changed = 0
        for rel in sorted(touched_paths):
            path = worktree / rel
            if not path.is_file():
                continue
            scoped_report = format_paths(path, check_only=False, limit=limit)
            fmt_changed += len(scoped_report.changes)
    if fmt_changed:
        _log.info(
            "ticket land: %s pre-land frob fmt canonicalized %d file(s)",
            ticket_id,
            fmt_changed,
        )


# frob:ticket T-1175
# frob:ticket T-1796
# frob:ticket T-1870
# frob:ticket T-1903
def _assert_design_loads_pre_land(
    worktree: Path, ticket_id: str, *, stage: str = "pre-tier-a"
) -> None:
    """Refuse the land (`sys.exit(1)`) if `worktree`'s design root exists
    but fails to PARSE/ELABORATE. Writes nothing, ever -- this is a
    read-only guard, not an auto-fix.

    T-1903: called TWICE by `_absorb_pre_land_fixes` -- `stage` names
    which call this is (`"pre-tier-a"` or `"post-tier-a"`), purely for the
    error message, so a refusal names WHICH side of the Tier-A rewrite
    produced the unparseable file rather than leaving that ambiguous. A
    `"pre-tier-a"` failure means the design root was ALREADY broken before
    this land touched it (pre-existing corruption); a `"post-tier-a"`
    failure means `_tier_a_pre_land_step`'s own rewrite is what broke it
    -- the failure mode T-1900 slipped through undetected because no
    post-rewrite check existed at all.

    T-1870: this used to be bundled into a step (formerly named
    `_sync_interface_pre_land_step`) that ALSO auto-wrote `interface=`
    drift into `design/frob.strata` on every land. That write half is
    deleted per an explicit owner directive that no code path may
    auto-update declared public-symbol surface -- but this load-
    validation half is kept, deliberately, extracted rather than deleted
    as collateral damage of removing the unrelated write path, because it
    answers a DIFFERENT question with a DIFFERENT reason to stay
    synchronous.

    WHY THIS STAYS ON THE LAND CRITICAL PATH (T-1686's rule: a check
    must be synchronous if and only if its failure damages someone OTHER
    than the change's own author -- the same rule that keeps ledger
    integrity and LAND-PROOF verification synchronous in every profile,
    forever, while coverage floors and doc drift may defer). A `design/
    frob.strata` that does not parse breaks `strata` -- and therefore
    every gate built on it -- repo-wide, for every OTHER agent, not just
    this land's own author. `frob ticket land` is the one process that
    mutates `design/**` on nearly every run, so it is the one place a
    parse failure can be caught before it ever reaches another agent's
    checkout. T-1796's own incident is the proof this matters: a dropped
    quote in `design/frob.strata` broke strata parsing repo-wide and
    SURVIVED THREE SEPARATE LANDS undetected, because SYS004 (the gate
    that would have caught it) only fires on an explicit `frob check
    --only sys`, and nothing else in the land path forced that
    invocation. "SYS004 catches it on the next `frob check`" is exactly
    the reasoning that let it through three times -- a guard that only
    fires when someone remembers to ask is not a guard. DO NOT delete
    this function as leftover plumbing from the removed `sync-interface`
    feature; it protects a different, still-live incident class."""
    from frob.strata._design_load import load_design_ids

    if not (worktree / "design").is_dir():
        return
    ids = load_design_ids(worktree, "design")
    if ids.errors:
        first = ids.errors[0]
        if stage == "post-tier-a":
            _log.error(
                "ticket land: %s refused -- design/** failed to load AFTER "
                "the pre-land Tier-A auto-fix rewrite (%s: %s); the "
                "Tier-A pass itself just corrupted design/frob.strata -- "
                "a handler in _tier_a_pre_land_step's batch is producing "
                "unparseable output for this diff (see `frob check --only "
                "sys` for the exact parse error, and re-run with Tier-A "
                "handlers bisected/excluded to name which one) before "
                "retrying `frob ticket land %s`",
                ticket_id,
                first.path,
                first.error,
                ticket_id,
            )
        else:
            _log.error(
                "ticket land: %s refused -- design/** failed to load (%s: "
                "%s); a pre-existing corrupt .strata file cannot be "
                "tolerated by the process that mutates it on every land -- "
                "fix the design file (see `frob check --only sys` for the "
                "exact parse error) before retrying `frob ticket land %s`",
                ticket_id,
                first.path,
                first.error,
                ticket_id,
            )
        sys.exit(1)


# frob:ticket T-1578
def _worktree_natives_verifiably_healthy(worktree: Path) -> bool:
    """T-1578: attempt the SAME auto-rebuild `run_gates` itself would
    (`frob.gates._maybe_autorebuild_natives`), then check that every
    declared `[[native]]` is both IMPORTABLE (`frob.strata.
    unimportable_natives`) and content-FRESH (`frob.strata.
    stale_natives`) -- mirrors exactly what a WAIVE004 self-manufactured
    `run_gates()` call inside `fix_waive004_stale_waiver` would itself
    observe, cheaply, WITHOUT paying for a full gates suite run when the
    answer is already 'no, this run's WAIVE004 verdict cannot be
    trusted'. `False` means the caller should exclude `WAIVE004` from
    this land's Tier-A batch rather than let `run_gates()` burn a full
    pass whose verdict `fix_waive004_stale_waiver`'s own `_degraded_
    verification_reason`/mass-invalidation guards would refuse to act on
    anyway."""
    from frob.gates import _maybe_autorebuild_natives
    from frob.strata import stale_natives, unimportable_natives

    _maybe_autorebuild_natives(worktree)
    return not stale_natives(worktree) and not unimportable_natives(worktree)


# frob:ticket T-1323
# frob:ticket T-1404
def _tier_a_pre_land_step(
    worktree: Path, ticket_id: str, touched_paths: frozenset[str] | None
) -> None:
    """The Tier-A deterministic auto-fix half of `_absorb_pre_land_fixes`,
    logging and skipping when the graph or queue cannot load (a land
    convenience, not a precondition)."""
    from frob.gates._fix_engine import apply_tier_a_fixes
    from frob.graph import build_graph
    from frob.tickets import load_active

    snapshot_result = build_graph(worktree, worktree / ".frob" / "cache.db")
    queue_result = load_active(worktree)
    if snapshot_result.is_err or queue_result.is_err:
        _log.warning(
            "ticket land: %s pre-land Tier-A fixes skipped (graph or "
            "queue load failed)",
            ticket_id,
        )
        return
    # frob:ticket T-1323
    # WAIVE004 ran unexcluded here until the 2026-07-29 incident: its
    # staleness self-check trusts a fresh gates run, but in a natives-stale
    # worktree that run silently under-reported (PERF/REF reach analysis
    # found nothing), so every live waiver read as dead and got
    # mass-deleted -- the land that stripped 50 PERF waivers onto main.
    # `fix_waive004_stale_waiver` itself now refuses to delete anything
    # when its self-manufactured verification run looks degraded (stale/
    # missing natives, a skipped gate stage) or shows a mass-invalidation
    # shape (one rule's waivers all going stale together in one run --
    # `_degraded_verification_reason`/`_mass_invalidation_rule`,
    # `src/frob/gates/_fix_engine.py`), so WAIVE004 runs here again
    # unexcluded -- prove-fresh-or-do-nothing at the handler itself,
    # rather than a blanket exclude at this call site. `exclude=` itself
    # stays available (regression-tested, `tests/test_gates.py`) for a
    # future caller that needs it again.
    #
    # T-1404: FMT001 is excluded from this generic batch when the scoped
    # fmt pass above already ran (`touched_paths is not None`) -- Tier-A's
    # own FMT001 handler (`fix_fmt001_directive_wrap`, T-1391) has no
    # scoping context here and would otherwise redundantly re-walk the
    # WHOLE tree right after the scoped pass, reintroducing the exact
    # out-of-scope rewrite this ticket closes. When the touched set could
    # not be computed, FMT001 stays in the batch (unscoped, matching the
    # pre-T-1404 fallback the scoped fmt pass above also took).
    # T-1581: COV002's insertion handler writes a Python-style
    # `# frob:ticket <id>` comment whatever the target file's language is.
    # It has already corrupted design/frob.strata (comment leader `//`)
    # during two separate lands, each time breaking `frob sys
    # sync-interface` on main until hand-repaired. Excluded from the
    # pre-land batch until that handler resolves the leader per language
    # (T-1581 fixes this in `_insert_ticket_directive_above`, but stays
    # excluded HERE until that ticket's own land actually reverts this
    # workaround -- reverting it preemptively from an unrelated ticket
    # would race whichever lands second); COV002 still REPORTS normally,
    # it just cannot auto-edit here.
    #
    # T-1578: preflight worktree natives BEFORE paying for the WAIVE004
    # self-run at all -- `fix_waive004_stale_waiver`'s own guards
    # (`_degraded_verification_reason`/`_mass_invalidation_rules`) would
    # refuse to act on a natives-degraded run anyway, but only AFTER a
    # full `run_gates()` pass and a loud ERROR log; excluding WAIVE004
    # here when `_worktree_natives_verifiably_healthy` says no gets the
    # identical outcome (nothing deleted) for a fraction of the cost, at
    # INFO level instead of a scary ERROR every land.
    # T-1592: WAIVE004 is excluded from the land path UNCONDITIONALLY.
    # Deleting a waiver is cleanup, never a landing requirement, but doing
    # it here has now caused three separate incidents (2026-07-29's 50
    # PERF waivers; 2026-08-05's 55 across arch/strata/perf/graph/vet via
    # the T-1579 escape; then 4 more DEPR005/DEAD001 that slipped UNDER
    # the mass-invalidation threshold, which cannot see a rule holding
    # fewer than `_WAIVE004_MASS_INVALIDATION_THRESHOLD` waivers at all).
    # Every one traces to the same root: a worktree gates run whose
    # analysis layer silently under-reports, which `_worktree_natives_
    # verifiably_healthy` below does NOT reliably detect -- it answered
    # "healthy" for the run that deleted those 4 while the perf gate was
    # reporting zero PERF004 findings repo-wide.
    #
    # The blanket exclude goes away when a degraded-run signal actually
    # fires for a silently under-reporting perf/reach substrate (T-1578
    # covers stale/unimportable natives, not the zero-findings case).
    # WAIVE004 still REPORTS on every `frob check`; only the land's
    # unattended auto-delete is off.
    exclude: tuple[str, ...] = ("COV002", "WAIVE004") + (
        ("FMT001",) if touched_paths is not None else ()
    )
    if not _worktree_natives_verifiably_healthy(worktree):
        _log.info(
            "ticket land: %s worktree natives stale/unimportable after "
            "auto-rebuild attempt (T-1578)",
            ticket_id,
        )
    applied = apply_tier_a_fixes(
        worktree,
        snapshot_result.danger_ok,
        queue_result.danger_ok,
        exclude=exclude,
        ticket_id=ticket_id,
    )
    if applied:
        _log.info(
            "ticket land: %s pre-land Tier-A fixes applied %d fix(es)",
            ticket_id,
            len(applied),
        )


# frob:ticket T-1456
# frob:ticket T-1463
# 90s was far under a real unscoped check (~3.5 min on this repo); every
# land's sweep spawn then died on TimeoutExpired, which also ESCAPED as an
# unhandled crash instead of the documented None/skip path (fixed below).
_POST_LAND_SWEEP_BUDGET_S = 300

#: T-1804: PRE001/SCOPE001, in their OWN "no active ticket derivable" mode
#: (`frob.gates._no_active_ticket_violation`, B9) -- the loud, by-design
#: error a diff touching non-ledger source with no `--ticket`/`T-####-`
#: branch always trips. `_unscoped_error_findings`'s whole callers
#: (the deferred post-land sweep, `--land-parity`) run UNSCOPED with NO
#: `--ticket` by deliberate design (catching residue outside any one
#: ticket's own scope is the whole point), against the SHARED root
#: checkout, on a detached timer -- so a concurrent land's transient dirt
#: (an untracked ticket directory, a staged-but-uncommitted file) reads
#: as a non-empty diff to B9 at the exact moment this spawn's child reads
#: it, and B9 fires exactly as designed for that case. This is a hygiene
#: signal about root's git state at the instant of measurement, never a
#: code regression the sweep exists to catch -- measured 2026-08-07: five
#: sweep-filed regression tickets in one hour whose only findings were
#: these two. Reused as the exclusion set both this function's callers
#: share, so it cannot drift independently between them.
_UNSCOPED_NO_TICKET_STRUCTURAL_NOISE_RULE_IDS = frozenset({"PRE001", "SCOPE001"})


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1456
# frob:ticket T-1535
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to \
# guarded_subprocess_run/_parse_error_findings_from_stdout, cross-module calls the \
# resolver cannot see through; the one real raise path (subprocess.TimeoutExpired) is \
# caught below"
# frob:waive EXHAUST002 reason="T-1636: leaked KeyError traces to the resolver's \
# unconditional _SUBSCRIPT_RAISE default for spawn_kwargs['env'] = env, a dict WRITE \
# (never raises KeyError) that the resolver's syntactic bracket scan cannot \
# distinguish from a read"
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456/T-1535) is a deliberate architecture doc walking through this \
# exact private spawn-and-parse helper's own contract, same T-0524/T-0529 per-function \
# architecture-doc precedent every other COV007 waiver in this repo already carries -- \
# not accidental drift onto a private helper"
def _unscoped_error_findings(
    root: Path,
    ticket_id: str,
    *,
    budget: int = _POST_LAND_SWEEP_BUDGET_S,
    env: dict[str, str] | None = None,
) -> frozenset[tuple[str, str]] | None:
    """Spawn an UNSCOPED, `--budget`-bounded `frob check --json` in `root`
    and parse the `(rule_id, file)` error-identity set from it, reusing
    `_parse_error_findings_from_stdout` (T-0846's shared parser -- no
    second hand-typed copy of the `## Errors` section format). Unlike
    `_check_gate_findings_fn`, this deliberately passes NO `--ticket`: the
    whole point of T-1456's post-land sweep is catching residue OUTSIDE
    any one ticket's own scope (a relocated waiver, drifted format, a
    stale registry denominator) that a `--ticket`-scoped re-verification
    structurally cannot see (playbook section 6c).

    T-1804: the returned set always excludes
    `_UNSCOPED_NO_TICKET_STRUCTURAL_NOISE_RULE_IDS` (PRE001/SCOPE001) --
    both fire unconditionally whenever this deliberately-no-`--ticket`
    spawn catches root's diff genuinely non-empty (including transient
    dirt from a concurrent land elsewhere on the shared checkout), which
    is a hygiene signal about root's state at the instant of measurement,
    never a code regression either caller of this function exists to
    catch. `None` means
    unmeasurable (refused spawn, timeout, unparsable output, OR -- T-1703
    -- a `--budget` run that deferred any stage group) -- the caller
    treats that as "skip the sweep, do not compare a real set against a
    guess," matching every other T-0846/T-0850 unmeasured-is-not-zero
    convention in this module.

    T-1703: the live incident this closed -- a deferred rapid-profile
    sweep logged `CLEAN, 0 errors` at a commit a plain unscoped `frob
    check` found 5 real errors in (2 of them TICK006 regressions the same
    land had just introduced). `--budget` runs whichever stage groups fit
    the time budget and DEFERS the rest; a gate that never ran emits no
    diagnostic lines, so a partial run's error set used to be
    indistinguishable from a genuinely clean full run. `--json` (this
    call) plus `_parse_error_findings_from_json`'s `_budget_deferred_
    stage_groups` check (via `_parse_error_findings_from_stdout`'s
    JSON-first dispatch) close this: any deferred stage group makes the
    whole result `None`, never a partial set. Confirmed independently
    time-dependent before the fix: two `--budget 300` runs on the
    IDENTICAL tree minutes apart selected different stage groups, so the
    old parsed "error identity set" was not even a function of tree state.

    `env` (T-1535, `--land-parity`'s own cache-bypassed evaluation): when
    given, passed straight through to `guarded_subprocess_run`'s own
    `env=` kwarg instead of the default parent-environment inheritance --
    `land_parity_findings` uses this to force `FROB_NO_GATE_CACHE=1` onto
    the spawned check without mutating THIS process's own environment.
    `None` (every pre-existing caller) preserves the exact prior
    behavior: no `env=` kwarg at all, `subprocess.run`'s own default
    (inherit the parent's environment unchanged)."""
    import subprocess

    from frob.app import ticket_runner as _ticket_runner

    spawn_kwargs: dict[str, object] = {
        "cwd": root,
        "capture_output": True,
        "text": True,
        "timeout": budget + 60,
        "check": False,
    }
    if env is not None:
        spawn_kwargs["env"] = env
    try:
        guarded = _ticket_runner.guarded_subprocess_run(
            [
                _python_for_tree(root),
                "-m",
                "frob",
                "check",
                "--budget",
                str(budget),
                "--json",
            ],
            **spawn_kwargs,
        )
    except subprocess.TimeoutExpired:
        # T-1463: the docstring's "None means unmeasurable (... timeout ...)"
        # contract was never actually implemented -- TimeoutExpired escaped
        # to main()'s top-level handler and crashed the whole land.
        _log.warning(
            "ticket land: %s unscoped post-land sweep timed out after %ds -- "
            "skipping the sweep (unmeasured, not zero); run `frob check` by "
            "hand to verify main's error floor",
            ticket_id,
            budget + 60,
        )
        return None
    if guarded.is_err:
        _log.warning(
            "ticket land: %s unscoped post-land sweep spawn refused (%s)",
            ticket_id,
            ProcessGuardError.ExecDisabled,
        )
        return None
    result = guarded.danger_ok
    findings = _parse_error_findings_from_stdout(
        ticket_id, result.stdout, result.returncode
    )
    if findings is None:
        return None
    return frozenset(
        (rule, file)
        for rule, file in findings
        if rule not in _UNSCOPED_NO_TICKET_STRUCTURAL_NOISE_RULE_IDS
    )


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1456
# frob:ticket T-1513
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456/T-1513) is a deliberate architecture doc walking through this \
# exact private Tier-A auto-fix step, same T-0524/T-0529 per-function architecture-doc \
# precedent every other COV007 waiver in this repo already carries -- not accidental \
# drift onto a private helper"
def _apply_root_tier_a_fixes(root: Path, ticket_id: str) -> list[str]:
    """Run the T-1138 Tier-A deterministic auto-fix handlers against
    `root`'s WHOLE tree (unscoped -- no `touched_paths`, mirroring
    `_tier_a_pre_land_step`'s own body but without the FMT001-exclusion
    logic that step's touched-set scoping needs) and return the sorted,
    de-duplicated list of repo-relative file paths the handlers actually
    rewrote (T-1513: was a bare count -- `_sweep_apply_tier_a_and_commit`
    needs the exact path set to stage narrowly, never `git add -A`, so
    land-owned files like `uv.lock` can never be swept in by accident).
    Best-effort: a graph/queue load failure is logged and treated as no
    fixes applied, never raised -- the caller's refusal path already
    covers "nothing fixed the residue."""
    from frob.gates._fix_engine import apply_tier_a_fixes
    from frob.graph import build_graph
    from frob.tickets import load_active

    snapshot_result = build_graph(root, root / ".frob" / "cache.db")
    queue_result = load_active(root)
    if snapshot_result.is_err or queue_result.is_err:
        _log.warning(
            "ticket land: %s post-land Tier-A auto-fix skipped (graph or "
            "queue load failed)",
            ticket_id,
        )
        return []
    applied = apply_tier_a_fixes(
        root, snapshot_result.danger_ok, queue_result.danger_ok, ticket_id=ticket_id
    )
    # frob:ticket T-1775
    # An auto-fix must never undo the change being landed. These handlers
    # run in ROOT against ROOT's INSTALLED frob, which is still the
    # PRE-land build -- so a ticket that deletes a gate rule lands a
    # registry with that rule's row removed, and `fix_reg010_registry_sync`
    # (reading the old `known_gate_rule_ids()`) immediately files it back.
    # T-1763 hit exactly that on every one of ~4 land attempts and reached
    # main REG002-red. Any file the landing changeset itself modified is
    # the ticket's deliberate intent, so drop it from the fix set rather
    # than letting a stale-code repair overwrite it.
    landed = _worktree_touched_paths(root)
    return sorted({entry.file for entry in applied} - landed)


# frob:ticket T-1775
def _worktree_touched_paths(root: Path) -> set[str]:
    """Repo-relative paths the in-flight land has already staged in
    `root`'s index.

    Empty set on any git failure -- "cannot tell what the land touched"
    must never silently widen what an auto-fix may overwrite, but it also
    must not block the land, so the fixes simply proceed unfiltered as
    they did before."""
    staged = run_argv(["git", "-C", str(root), "diff", "--cached", "--name-only"])
    if staged.is_err or staged.danger_ok.returncode != 0:
        return set()
    return {
        line.strip() for line in staged.danger_ok.stdout.splitlines() if line.strip()
    }


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1456
# frob:ticket T-1513
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_error_fixed_by_tier_a_lands_with_a_followup_commit  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_fix_commit_stages_only_touched_paths_not_git_add_dash_a  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456/T-1513) is a deliberate architecture doc walking through this \
# exact private commit-and-fix step, same T-0524/T-0529 per-function architecture-doc \
# precedent every other COV007 waiver in this repo already carries -- not accidental \
# drift onto a private helper"
def _sweep_apply_tier_a_and_commit(
    root: Path, ticket_id: str, final_id: str, new_findings: frozenset[tuple[str, str]]
) -> int:
    """T-1456 autofix-retry phase of `_post_land_unscoped_error_sweep`: run
    the unscoped Tier-A auto-fix handlers against `root` and, if any fix
    applied, stage ONLY the exact paths Tier-A touched (T-1513: never
    `git add -A` -- that used to also stage the perpetually-dirty
    land-owned `uv.lock`, which the T-0731 pre-commit hook then refused,
    leaving the fix uncommitted and the land reverting) and commit the
    result as a follow-up cleanup commit under `FROB_LAND_INTERNAL=1`
    (T-0828's escape hatch -- this commit is land's own internal
    machinery, same disposition as land's other internal commits, and
    without it a Tier-A fix that happens to touch a land-owned file would
    still be refused). Logs `git`'s stderr on any add/commit failure
    (T-1513: previously silent) rather than raising -- the caller re-scans
    regardless of whether this commit succeeded. Returns the number of
    fixes Tier-A applied, independent of whether the commit itself
    succeeded."""
    _log.warning(
        "ticket land: %s post-land unscoped sweep found %d new error(s) "
        "absent before this land: %s -- attempting Tier-A auto-fix",
        final_id,
        len(new_findings),
        sorted(new_findings),
    )
    touched_paths = _apply_root_tier_a_fixes(root, ticket_id)
    fixed_count = len(touched_paths)
    if touched_paths:
        add_argv = ["git", "-C", str(root), "add", "--", *touched_paths]
        added = run_argv(add_argv)
        if added.is_err or added.danger_ok.returncode != 0:
            _log.error(
                "ticket land: %s post-land Tier-A fix `git add` failed for "
                "%s -- %s left uncommitted in %s: %s",
                final_id,
                touched_paths,
                fixed_count,
                root,
                _describe_git_failure(add_argv, added),
            )
            return fixed_count
        commit_argv = [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            f"fix(land): {final_id} post-land Tier-A cleanup ({fixed_count} fix(es))",
        ]
        with _land_internal_git_env():
            committed = run_argv(commit_argv)
        if committed.is_err or committed.danger_ok.returncode != 0:
            _log.error(
                "ticket land: %s post-land Tier-A fix commit failed -- %s "
                "left uncommitted in %s: %s",
                final_id,
                fixed_count,
                root,
                _describe_git_failure(commit_argv, committed),
            )
    return fixed_count


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1456
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_error_absent_before_land_refuses_and_reverts  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456) is a deliberate architecture doc walking through this exact \
# private revert step, same T-0524/T-0529 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries -- not accidental drift onto \
# a private helper"
def _sweep_revert_land(
    root: Path,
    final_id: str,
    pre_land_sha: str,
    still_new: frozenset[tuple[str, str]],
) -> None:
    """T-1456 refuse-revert phase of `_post_land_unscoped_error_sweep`:
    hard-reset `root` back to `pre_land_sha` after Tier-A auto-fix failed
    to resolve every new finding, logging the finding list either way and
    escalating to an error log (never raising) if the reset itself also
    fails, since that leaves `root` landed with unresolved residue."""
    _log.error(
        "ticket land: %s post-land unscoped sweep still shows %d new "
        "error(s) after Tier-A auto-fix: %s -- reverting %s to its "
        "pre-land state %s",
        final_id,
        len(still_new),
        sorted(still_new),
        root,
        pre_land_sha,
    )
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", pre_land_sha])
    if reset.is_err or reset.danger_ok.returncode != 0:
        _log.error(
            "ticket land: %s post-land revert to %s FAILED in %s -- %s is "
            "left landed with %d unresolved new error(s); manual repair "
            "required: %s",
            final_id,
            pre_land_sha,
            root,
            root,
            len(still_new),
            sorted(still_new),
        )


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1456
# frob:ticket T-1463
# frob:waive AFFECT001 reason="T-1463 only skips a guaranteed-redundant second scan \
# when Tier-A applied 0 fixes (root's tree is provably unchanged since fresh was \
# captured); the documented step 4/5 contract in docs/modules/tickets.md's Post-land \
# unscoped error sweep section is unchanged -- same inputs, same outputs, fewer \
# duplicate frob check spawns. Out of this ticket's declared scope (src/frob/app/ \
# ticket_runner/_land_cmd.py, src/frob/tickets/_land_finalize.py) to also touch \
# docs/modules/tickets.md here."
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_error_absent_before_land_refuses_and_reverts  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_new_error_fixed_by_tier_a_lands_with_a_followup_commit  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_no_new_error_is_a_silent_no_op  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep.test_unmeasurable_baseline_or_fresh_skips_the_sweep  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456) is a deliberate architecture doc walking through this exact \
# private orchestration entry point, same T-0524/T-0529 per-function architecture-doc \
# precedent every other COV007 waiver in this repo already carries -- not accidental \
# drift onto a private helper"
def _post_land_unscoped_error_sweep(
    root: Path,
    ticket_id: str,
    final_id: str,
    pre_land_sha: str,
    baseline_findings: frozenset[tuple[str, str]] | None,
) -> bool:
    """T-1456: after `land()`'s squash-apply commit has already landed on
    `root`, compare a fresh UNSCOPED error-finding identity set against
    `baseline_findings` (the same identity set captured against `root`
    BEFORE `land()` ran, at `pre_land_sha`). Every wave of this drive left
    small unscoped residue on main a `--ticket`-scoped land verification
    could not see -- waivers that did not travel with relocated prose,
    format drift, a stale registry denominator, SELFAUDIT interface attrs
    -- each only surfaced in the coordinator's NEXT full `frob check`. This
    closes that gap mechanically: a NEW error (absent from the baseline)
    is Tier-A-auto-fixed and committed as a follow-up if that resolves it,
    or the land is UNDONE (`root` hard-reset back to `pre_land_sha`) and
    refused with the exact finding list if it does not -- main's error
    floor can no longer regress silently at land time.

    Returns `True` if `root` is left in a landed state (clean, or fixed-
    and-committed), `False` if the land was reverted and the caller must
    refuse. Either `baseline_findings is None` (unmeasurable pre-land) or
    an unmeasurable fresh scan is treated as "skip the sweep, do not
    refuse a land over a comparison neither side could actually make" --
    same unmeasured-is-not-zero posture `_check_gates_summary_fn`/
    `_check_gate_findings_fn` already use.

    T-1463: when the Tier-A auto-fix retry applies 0 fixes, `root`'s tree
    is provably unchanged since `fresh` was captured a few lines above --
    a second full unscoped scan can only reproduce the identical result,
    so it is skipped and `fresh` is reused directly as `reverify` instead
    of paying for a guaranteed-redundant budget-bounded `frob check`
    spawn (this was, along with the pre-land baseline capture now running
    concurrently with `land()` in `_land`, one of the two near-full check
    invocations pushing a land past the playbook's foreground budget)."""
    if baseline_findings is None:
        _log.warning(
            "ticket land: %s post-land unscoped sweep skipped -- pre-land "
            "baseline was unmeasurable",
            final_id,
        )
        return True

    fresh = _unscoped_error_findings(root, ticket_id)
    if fresh is None:
        _log.warning(
            "ticket land: %s post-land unscoped sweep skipped -- fresh "
            "post-land scan was unmeasurable",
            final_id,
        )
        return True

    new_findings = fresh - baseline_findings
    if not new_findings:
        _log.info(
            "ticket land: %s post-land unscoped sweep clean (0 new error(s) "
            "vs the pre-land baseline of %d)",
            final_id,
            len(baseline_findings),
        )
        return True

    fixed_count = _sweep_apply_tier_a_and_commit(
        root, ticket_id, final_id, new_findings
    )

    # T-1463: Tier-A applying 0 fixes means `root`'s tree is UNCHANGED since
    # `fresh` was captured above -- a second full unscoped scan can only
    # reproduce the exact same result, so skip it and reuse `fresh`
    # directly instead of paying for a guaranteed-redundant budget-bounded
    # `frob check` spawn.
    if fixed_count == 0:
        reverify: frozenset[tuple[str, str]] | None = fresh
    else:
        reverify = _unscoped_error_findings(root, ticket_id)
    still_new = (reverify - baseline_findings) if reverify is not None else new_findings
    if not still_new:
        _log.info(
            "ticket land: %s post-land Tier-A auto-fix resolved every new "
            "error finding",
            final_id,
        )
        return True

    _sweep_revert_land(root, final_id, pre_land_sha, still_new)
    return False


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1514
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456/T-1514) is a deliberate architecture doc walking through this \
# exact private pre-commit Tier-A step, same T-0524/T-0529 per-function \
# architecture-doc precedent every other COV007 waiver in this repo already carries -- \
# not accidental drift onto a private helper"
def _sweep_apply_tier_a_pre_commit(root: Path, ticket_id: str) -> frozenset[str]:
    """T-1514's pre-commit twin of `_sweep_apply_tier_a_and_commit`: run the
    unscoped Tier-A auto-fix handlers against `root` and, for every path
    touched, `git add --` it into the index -- but never commit, since at
    this checkpoint `root`'s working tree IS the still-uncommitted, staged
    squash-apply changeset (`_land_squash_apply_finish` calls this right
    before `_commit_squash_apply`) and the fix belongs in that SAME final
    commit, not a separate follow-up one. Returns the set of paths staged
    this way (empty if Tier-A applied nothing or the add itself failed --
    logged, never raised)."""
    touched_paths = _apply_root_tier_a_fixes(root, ticket_id)
    if not touched_paths:
        return frozenset()
    add_argv = ["git", "-C", str(root), "add", "--", *touched_paths]
    added = run_argv(add_argv)
    if added.is_err or added.danger_ok.returncode != 0:
        _log.error(
            "ticket land: %s pre-commit Tier-A fix `git add` failed for "
            "%s -- fix(es) left unstaged in %s: %s",
            ticket_id,
            touched_paths,
            root,
            _describe_git_failure(add_argv, added),
        )
        return frozenset()
    return frozenset(touched_paths)


# frob:ticket T-1524
#: Land-owned artifacts the land machinery itself rewrites in the staged
#: squash (REL001 bump trio + uv resync). Findings against these at the
#: pre-commit checkpoint are land-machinery artifacts, not the ticket's --
#: only `frob ticket land` ever writes them (T-0731), and land's own
#: REL001/ledger finalization governs their hygiene after the commit.
_LAND_OWNED_SWEEP_EXEMPT = frozenset(
    {".frob-release.json", "CHANGELOG.md", "pyproject.toml", "uv.lock"}
)

# frob:ticket T-1524
#: Ticket-hygiene rules that structurally false-positive at the T-1514
#: staged-uncommitted checkpoint: the landing ticket is already
#: finalized done in the staged ledger, so SCOPE001/PRE001 see its own
#: staged diff as unlicensed-by-any-open-ticket. Both obligations were
#: already enforced against the REAL open ticket by land's pre-merge
#: covers_scope/prework verification; re-evaluating them against the
#: staged tree can only produce artifacts of the checkpoint itself.
_PRE_COMMIT_SWEEP_EXEMPT_RULES = frozenset({"PRE001", "SCOPE001"})


# frob:ticket T-1524
def _is_land_owned_finding(root: Path, file_field: str) -> bool:
    """True when a sweep finding's file field names a repo-ROOT land-owned
    artifact (`_LAND_OWNED_SWEEP_EXEMPT`), whether reported repo-relative
    (`.frob-release.json`) or absolute (`<root>/pyproject.toml`).
    Deliberately matches only root-level paths -- a nested
    `pyproject.toml` inside a fixture tree is a real finding, not
    land's."""
    normalized = file_field.replace("\\", "/").rstrip("/")
    if normalized in _LAND_OWNED_SWEEP_EXEMPT:
        return True
    root_prefix = str(root).replace("\\", "/").rstrip("/") + "/"
    return (
        normalized.startswith(root_prefix)
        and normalized[len(root_prefix) :] in _LAND_OWNED_SWEEP_EXEMPT
    )


# frob:ticket T-1524
def _drop_checkpoint_exempt_findings(
    root: Path,
    final_id: str,
    findings: frozenset[tuple[str, str]],
    *,
    log_exclusions: bool,
) -> frozenset[tuple[str, str]]:
    """Remove findings that are artifacts of the T-1514 staged-uncommitted
    checkpoint itself: rules in `_PRE_COMMIT_SWEEP_EXEMPT_RULES` (the
    landing ticket is already finalized done, so its own staged diff
    reads as unlicensed) and any finding on a root-level land-owned file
    (`_is_land_owned_finding` -- the land's own staged REL001 bump / uv
    resync). Exclusions are logged loudly (never silently dropped)."""
    exempt = frozenset(
        f
        for f in findings
        if _is_land_owned_finding(root, f[1]) or f[0] in _PRE_COMMIT_SWEEP_EXEMPT_RULES
    )
    if exempt and log_exclusions:
        _log.warning(
            "ticket land: %s pre-commit unscoped sweep excluding %d "
            "checkpoint-artifact finding(s) (T-1524): %s",
            final_id,
            len(exempt),
            sorted(exempt),
        )
    return findings - exempt


#: `land_parity_findings`'s own budget default (T-1535) -- deliberately
#: the SAME `_POST_LAND_SWEEP_BUDGET_S` the post-land/pre-commit sweeps
#: already use, so a worktree-mode `--land-parity` run and the real land
#: sweep it exists to preview measure against an identical time budget,
#: never a narrower one that could hide a stage the real sweep would see.
# frob:ticket T-1535
_LAND_PARITY_BUDGET_S = _POST_LAND_SWEEP_BUDGET_S


# frob:doc docs/modules/tickets.md#frob-check---land-parity-t-1535
# frob:ticket T-1535
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_none_when_unmeasurable kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_forces_no_gate_cache_env_on_the_spawn kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_parity_with_the_land_sweeps_own_exemption_function kind="unit"  # noqa: E501
def land_parity_findings(
    root: Path, *, budget: int = _LAND_PARITY_BUDGET_S
) -> frozenset[tuple[str, str]] | None:
    """`frob check --land-parity`'s own evaluation (T-1535): the EXACT
    same `(rule, file)` unscoped-error identity-set computation the
    pre-commit/post-land land sweeps run (`_unscoped_error_findings` +
    `_drop_checkpoint_exempt_findings`, both reused verbatim, no second
    copy of either), against `root`'s CURRENT tree state -- so a worktree
    agent can converge on a clean land BEFORE the coordinator ever lands,
    instead of discovering the divergence only after a real land sweep
    refuses.

    Two things this adds beyond a bare call to those two functions:
    cache-bypassed (`FROB_NO_GATE_CACHE=1` injected into the spawned
    check's OWN environment via `_unscoped_error_findings`'s `env=`
    param, never this process's own `os.environ` -- T-1346's gate-result
    cache is exactly the kind of staleness this ticket's own body names
    as a repeated blind-repair cause), and the T-1524 checkpoint
    exemptions applied unconditionally (there is no real pre-land-vs-
    post-land baseline to diff against here, only "what would the sweep
    see" -- so every checkpoint-artifact exclusion the real sweep would
    also drop is dropped here too, by the SAME function).

    `None` (unmeasurable: refused spawn, timeout, unparsable output)
    propagates unchanged from `_unscoped_error_findings` -- the CLI
    caller (`check_runner.py::_run_land_parity`) treats that as "could
    not evaluate," never a false-clean zero."""
    import os

    env = dict(os.environ)
    env["FROB_NO_GATE_CACHE"] = "1"
    findings = _unscoped_error_findings(root, "land-parity", budget=budget, env=env)
    if findings is None:
        return None
    return _drop_checkpoint_exempt_findings(
        root, "land-parity", findings, log_exclusions=True
    )


# frob:doc docs/modules/tickets.md#post-land-unscoped-error-sweep-t-1456
# frob:ticket T-1514
# frob:ticket T-1524
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's Post-land unscoped error \
# sweep section (T-1456/T-1514/T-1524) is a deliberate architecture doc walking \
# through this exact private pre-commit sweep entry point, same T-0524/T-0529 \
# per-function architecture-doc precedent every other COV007 waiver in this repo \
# already carries -- not accidental drift onto a private helper"
def _pre_commit_unscoped_error_sweep(
    root: Path,
    ticket_id: str,
    final_id: str,
    baseline_findings: frozenset[tuple[str, str]] | None,
) -> bool | None:
    """T-1514: the pre-commit twin of `_post_land_unscoped_error_sweep` --
    same identity-set comparison and Tier-A-auto-fix-then-refuse logic,
    but run at `_land_squash_apply_finish`'s LAST checkpoint before the
    final commit, while `root`'s working tree still holds only the staged,
    uncommitted squash-apply changeset. A refusal here (`False`) is
    unwound by `_land_squash_apply_finish` via `_verified_reset_root` --
    cheap, and touches no foreign commit, unlike the T-1456 post-land
    sweep's `git reset --hard` of an already-real commit that may have
    foreign work stacked on top of it by the time a refusal is detected.
    The post-land sweep (T-1456) stays wired in as-is, unchanged, as a
    cheap final assertion for whatever this pre-commit pass could not
    catch (e.g. a `_post_land_unscoped_error_sweep`-only-observable ledger
    splice artifact).

    Returns `None` (skip -- unmeasurable, never treated as "clean") when
    `baseline_findings` or the fresh scan could not be captured, `True`
    when clean or Tier-A auto-fix resolved every new finding (fix(es)
    already staged, ready for the same commit), `False` when a real new
    finding survives Tier-A and the caller must refuse+unwind."""
    if baseline_findings is None:
        _log.warning(
            "ticket land: %s pre-commit unscoped sweep skipped -- pre-land "
            "baseline was unmeasurable",
            final_id,
        )
        return None

    fresh = _unscoped_error_findings(root, ticket_id)
    if fresh is None:
        _log.warning(
            "ticket land: %s pre-commit unscoped sweep skipped -- staged "
            "pre-commit scan was unmeasurable",
            final_id,
        )
        return None

    new_findings = _drop_checkpoint_exempt_findings(
        root, final_id, fresh - baseline_findings, log_exclusions=True
    )
    if not new_findings:
        _log.info(
            "ticket land: %s pre-commit unscoped sweep clean (0 new "
            "error(s) vs the pre-land baseline of %d)",
            final_id,
            len(baseline_findings),
        )
        return True

    _log.warning(
        "ticket land: %s pre-commit unscoped sweep found %d new error(s) "
        "absent before this land: %s -- attempting Tier-A auto-fix",
        final_id,
        len(new_findings),
        sorted(new_findings),
    )
    fixed_paths = _sweep_apply_tier_a_pre_commit(root, ticket_id)
    reverify = _unscoped_error_findings(root, ticket_id) if fixed_paths else fresh
    still_new = (reverify - baseline_findings) if reverify is not None else new_findings
    still_new = _drop_checkpoint_exempt_findings(
        root, final_id, still_new, log_exclusions=False
    )
    if not still_new:
        _log.info(
            "ticket land: %s pre-commit Tier-A auto-fix resolved every new "
            "error finding (staged: %s)",
            final_id,
            sorted(fixed_paths),
        )
        return True

    _log.error(
        "ticket land: %s pre-commit unscoped sweep still shows %d new "
        "error(s) after Tier-A auto-fix: %s -- refusing before any commit "
        "lands on %s",
        final_id,
        len(still_new),
        sorted(still_new),
        root,
    )
    return False


#: T-1913: retry count/backoff (seconds, cumulative across attempts) for
#: `_is_ancestor_with_retry`'s `git merge-base --is-ancestor` re-check. Kept
#: small and bounded -- this is a self-heal for a suspected commit/ref
#: VISIBILITY race (T-1913's own ticket body, direction (c)), not a
#: general-purpose git retry policy; a genuinely non-ancestor commit costs
#: this same ~0.7s on every land, which is why the count stays low rather
#: than growing to chase an unconfirmed race indefinitely.
_LAND_PROOF_ANCESTOR_RETRY_DELAYS: tuple[float, ...] = (0.1, 0.2, 0.4)


# frob:ticket T-1913
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry.test_retries_until_ancestor_check_settles_true  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry.test_gives_up_after_exhausting_retries_on_a_genuine_non_ancestor  # noqa: E501
def _is_ancestor_with_retry(
    root: Path, commit_sha: str, *, sleep: Callable[[float], None] = time.sleep
) -> bool:
    """`git -C root merge-base --is-ancestor commit_sha main`, retried up
    to `len(_LAND_PROOF_ANCESTOR_RETRY_DELAYS)` extra times with a short
    backoff between attempts before giving up and returning False (T-1913).

    T-1913 investigated a real, unreproduced incident (T-1895, `frob
    ticket land` printed `is_ancestor_of_main=False` for a commit that
    HAD in fact fully landed) and could not pin the mechanism down in a
    synchronous test fixture -- the "wrong checkout" theory was ruled out
    directly. One of the ticket's own named follow-up directions is
    exactly this: treat a `False` result as possibly a transient commit/
    ref VISIBILITY race in the real dispatch environment (a network
    filesystem, a bind mount, or some other non-synchronous git backend
    this repo's own test fixtures never exercise) rather than trusting
    the first read unconditionally, and retry briefly before concluding
    the commit really is not on `main`. A genuinely non-ancestor commit
    still costs the full retry budget (`sum(_LAND_PROOF_ANCESTOR_RETRY_
    DELAYS)`, ~0.7s) on every land -- accepted deliberately: this is a
    self-heal for a suspected race, not a proof the race exists, and a
    False that never resolves to True is exactly what the caller should
    report as unverified regardless of how many times it was asked.
    `sleep` is injectable so a test can drive this without actually
    waiting."""
    is_ancestor = run_argv(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", commit_sha, "main"]
    )
    if is_ancestor.is_ok and is_ancestor.danger_ok.returncode == 0:
        return True
    for delay in _LAND_PROOF_ANCESTOR_RETRY_DELAYS:
        sleep(delay)
        retried = run_argv(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", commit_sha, "main"]
        )
        if retried.is_ok and retried.danger_ok.returncode == 0:
            _log.info(
                "land: is_ancestor_of_main re-check for %s settled True on "
                "retry (T-1913: suspected commit/ref visibility race, not "
                "a genuine non-ancestor)",
                commit_sha,
            )
            return True
    return False


# frob:ticket T-1175
# frob:ticket T-1523
# frob:ticket T-1884
# frob:ticket T-1913
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_verifies_an_anchor_ticket_left_queued_on_main  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_proof_still_refuses_a_non_anchor_ticket_left_queued  # noqa: E501
def _land_proof_checks(
    root: Path, final_id: str, commit_sha: str
) -> tuple[bool, str, bool]:
    """The two checks `_print_land_proof`'s `LAND-PROOF:` line reports
    (T-1175), split out (T-1523) so `_report_stale_post_land_verify_
    markers` can run the IDENTICAL check against a RECOVERED marker's
    `(ticket_id, commit_sha)` pair without duplicating the git/ledger
    logic: `commit_sha` is an ancestor of `root`'s `main` (T-1913: retried
    briefly via `_is_ancestor_with_retry` before concluding False), AND
    `final_id`'s state on `main` is a terminal state (done/dropped) -- OR
    (T-1884) `final_id` is an `anchor=True` ticket sitting in `queued`/
    `blocked`, the legitimate non-terminal-forever shape `_skip_close_for_
    anchor_no_close_requested` (T-1874) publishes as-is rather than
    forcing through a DONE transition. Returns `(ancestor_ok, state_desc,
    is_anchor)` -- the caller derives `verified` and any logging itself."""
    from frob.tickets import load_all

    ancestor_ok = _is_ancestor_with_retry(root, commit_sha)

    state_desc = "unknown"
    is_anchor = False
    loaded = load_all(root)
    if loaded.is_ok:
        ticket = loaded.danger_ok.get(final_id)
        if ticket is not None:
            state_desc = ticket.state.value
            is_anchor = ticket.anchor
    return ancestor_ok, state_desc, is_anchor


def _print_land_proof(root: Path, report) -> bool:  # noqa: ANN001
    """T-1175's machine-checkable on-main proof line: after a real
    (non-dry-run, `Ok`) land, verify and print `commit_sha` is an ancestor
    of `root`'s `main` AND the ticket's state on `main` is a terminal
    state (done/dropped) -- the exact two checks playbook section 0 step 9
    already asks every agent to run by hand
    (`git merge-base --is-ancestor <hash> main`, then re-`show` the ticket).
    Printed as one grep-able `LAND-PROOF:` line, and the combined
    `verified` bool is also RETURNED so `--finish` can gate worktree
    removal on it without re-deriving either check itself.

    T-1884: `state_ok` ALSO accepts `queued`/`blocked` when the ticket is
    `anchor=True` -- mirroring `_skip_close_for_anchor_no_close_
    requested`'s (T-1874) own condition for when landing a non-terminal
    ticket record as-is is correct, not a workaround. Before this, a
    legitimately anchored, requeued ticket (state stays `queued`/
    `blocked` on `main` BY DESIGN) always printed `verified=False` on a
    completely correct land, because this check predates T-1856's anchor
    marker and T-1874's land-time skip-close path -- observed landing
    T-1820 (2026-08-08): `is_ancestor_of_main=True state_on_main=queued
    verified=False`."""
    from frob.tickets import TicketState

    ancestor_ok, state_desc, is_anchor = _land_proof_checks(
        root, report.final_id, report.commit_sha
    )
    state_ok = state_desc in (TicketState.DONE.value, TicketState.DROPPED.value) or (
        is_anchor
        and state_desc in (TicketState.QUEUED.value, TicketState.BLOCKED.value)
    )
    verified = ancestor_ok and state_ok

    _log.info(
        "LAND-PROOF: ticket=%s commit=%s is_ancestor_of_main=%s "
        "state_on_main=%s verified=%s",
        report.final_id,
        report.commit_sha,
        ancestor_ok,
        state_desc,
        verified,
    )
    return verified


# frob:ticket T-1523
# frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared  # noqa: E501
def _report_stale_post_land_verify_markers(root: Path) -> None:
    """Reconcile every leftover T-1523 post-land-verify-pending marker
    under `root` -- called at the very START of `_land_core`, before this
    invocation does any work of its own: a prior `frob ticket land`
    SIGTERM-killed between its own commit landing and its post-land
    verification tail finishing (the 2026-08-04 T-1464 incident's own
    trigger) leaves one of these markers behind. This is READ-ONLY --
    unlike T-0907's own `_repair_stale_land_marker`, it never resets or
    mutates `root`; the commit the marker names is already durably on
    `root` either way (the marker is written AFTER the commit exists), so
    there is nothing to roll back. It simply re-runs the same two
    `LAND-PROOF` checks (`_land_proof_checks`) that a normal, uninterrupted
    land would have run, logs a `LAND-PROOF-RECOVERED:` line naming the
    result, and clears the marker -- surfacing exactly what a >540s kill
    left ambiguous instead of leaving it silently unverified forever. A
    `verified=False` result is a loud signal for a human to inspect
    `root`'s ledger/git-log by hand; this function itself never refuses or
    exits, since the NEW ticket this invocation is actually landing must
    not be blocked by a PRIOR, unrelated ticket's leftover marker."""
    from frob.tickets import TicketState
    from frob.tickets._land import _clear_post_land_verify_marker
    from frob.tickets._land import _stale_post_land_verify_markers as _stale_markers

    for ticket_id, commit_sha in _stale_markers(root):
        ancestor_ok, state_desc, is_anchor = _land_proof_checks(
            root, ticket_id, commit_sha
        )
        # frob:ticket T-1884
        state_ok = state_desc in (
            TicketState.DONE.value,
            TicketState.DROPPED.value,
        ) or (
            is_anchor
            and state_desc in (TicketState.QUEUED.value, TicketState.BLOCKED.value)
        )
        verified = ancestor_ok and state_ok
        _log.warning(
            "LAND-PROOF-RECOVERED: a prior `frob ticket land %s` was "
            "interrupted after its commit (%s) landed but before "
            "post-land verification finished (T-1523) -- re-checked now: "
            "is_ancestor_of_main=%s state_on_main=%s verified=%s",
            ticket_id,
            commit_sha,
            ancestor_ok,
            state_desc,
            verified,
        )
        _clear_post_land_verify_marker(root, ticket_id)


#: T-1845 (T-1554 design doc follow-up): the one remaining unmarked
#: `--finish`/`--retire-on-proof` sub-step per that doc's audit -- the two
#: git mutations (`_finish_worktree`'s `git worktree remove`, and
#: `--retire-on-proof`'s additional `_delete_worktree_branch`'s `git
#: branch -D`) run AFTER the land's own commit is already durable and
#: AFTER T-1523's own post-land-verify-pending marker has already been
#: cleared (`_finish_land_after_success` only reaches this point once
#: `_print_land_proof` returned `verified=True`) -- so a SIGTERM in this
#: specific window leaves nothing durable recording that finish/retire
#: was still in flight. Mirrors `_land_verify_pending_marker_path`'s own
#: shape (`frob.tickets._land`, T-1523) one-for-one: a small per-ticket
#: JSON file under `.frob/`, written right before the first mutation,
#: cleared once every mutation this invocation actually attempted has
#: completed (successfully or not -- a `_finish_worktree`/`_delete_
#: worktree_branch` failure already logs its own ERROR and is not this
#: marker's job to re-report), reconciled read-only at the top of the
#: NEXT `frob ticket land` invocation the same way `_report_stale_post_
#: land_verify_markers` reconciles T-1523's marker.
# frob:ticket T-1845
_LAND_FINISH_PENDING_DIRNAME = "land-finish-pending"


# frob:ticket T-1845
def _land_finish_pending_dir(root: Path) -> Path:
    """`<root>/.frob/land-finish-pending`, where a `--finish`/`--retire-
    on-proof` invocation still mid-flight records its per-ticket marker
    (T-1845)."""
    return root / ".frob" / _LAND_FINISH_PENDING_DIRNAME


# frob:ticket T-1845
def _land_finish_pending_marker_path(root: Path, ticket_id: str) -> Path:
    """The per-ticket land-finish-pending marker path under `root`
    (T-1845)."""
    return _land_finish_pending_dir(root) / f"{ticket_id}.json"


# frob:ticket T-1845
# frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_write_then_clear_round_trips  # noqa: E501
def _write_land_finish_pending_marker(
    root: Path, ticket_id: str, commit_sha: str, *, retire_on_proof: bool
) -> None:
    """Record that `ticket_id`'s `--finish`/`--retire-on-proof` mutations
    (worktree removal, and branch deletion when `retire_on_proof`) are
    about to start (T-1845) -- called by `_finish_land_after_success`
    immediately BEFORE `_finish_worktree` runs, mirroring `_write_post_
    land_verify_marker`'s own "write before the risky window, clear after
    it" shape. `commit_sha` is the already-landed, already-verified
    commit this finish is cleaning up after -- purely informational for
    whoever reads a leftover marker, never re-verified by the writer.
    Best-effort like its T-1523 sibling: a write failure is logged but
    never blocks `--finish` itself, since this marker is a recovery AID
    over an already-successful land, not a mutation gate."""
    path = _land_finish_pending_marker_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "commit_sha": commit_sha,
                    "retire_on_proof": retire_on_proof,
                }
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.warning(
            "land: %s could not write land-finish-pending marker (%s) -- "
            "proceeding without the T-1845 crash-recovery aid for this "
            "--finish/--retire-on-proof run",
            ticket_id,
            exc,
        )


# frob:ticket T-1845
# frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_write_then_clear_round_trips  # noqa: E501
def _clear_land_finish_pending_marker(root: Path, ticket_id: str) -> None:
    """Remove `ticket_id`'s land-finish-pending marker, if any (T-1845) --
    called once `_finish_land_after_success` has run every mutation this
    invocation attempted (`_finish_worktree`, and `_delete_worktree_branch`
    when `--retire-on-proof`), mirroring `_clear_post_land_verify_marker`'s
    unconditional-cleanup shape: cleared regardless of whether the
    mutation(s) themselves succeeded, since a mutation failure already logs
    its own ERROR with its own recovery instructions -- this marker's only
    job is telling a SIGTERM-killed run apart from a normally-completed
    one, not re-reporting a mutation outcome the caller already reported."""
    path = _land_finish_pending_marker_path(root, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning(
            "land: %s could not clear land-finish-pending marker: %s",
            ticket_id,
            exc,
        )


# frob:ticket T-1845
# frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_no_marker_is_a_silent_empty_result  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_stale_marker_is_reported  # noqa: E501
def _stale_land_finish_pending_markers(root: Path) -> tuple[tuple[str, str, bool], ...]:
    """`(ticket_id, commit_sha, retire_on_proof)` for every leftover T-1845
    land-finish-pending marker under `root`, read-only (never mutates
    `root` or the marker files -- reconciling/clearing is the caller's own
    job, mirroring `_stale_post_land_verify_markers`'s own contract
    exactly). Called at the very start of `_land_core`, alongside its
    T-1523 sibling, so a prior run's SIGTERM-interrupted finish/retire is
    surfaced before this invocation does any work of its own. A marker
    whose JSON fails to parse is skipped with a WARNING (never raises) --
    a corrupt marker must not block every future land against `root`.
    No markers at all -- the overwhelmingly common case -- returns an
    empty tuple."""
    marker_dir = _land_finish_pending_dir(root)
    if not marker_dir.is_dir():
        return ()
    found: list[tuple[str, str, bool]] = []
    for entry in sorted(marker_dir.glob("*.json")):
        try:
            payload = json.loads(entry.read_text(encoding="utf-8"))
            found.append(
                (
                    payload["ticket_id"],
                    payload["commit_sha"],
                    bool(payload.get("retire_on_proof", False)),
                )
            )
        except (OSError, ValueError, KeyError) as exc:
            _log.warning(
                "land: could not parse land-finish-pending marker %s (%s) "
                "-- skipping, left in place for manual inspection",
                entry,
                exc,
            )
    return tuple(found)


# frob:ticket T-1845
# frob:tests tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker.test_reconcile_reports_and_clears_a_stale_marker  # noqa: E501
def _report_stale_land_finish_pending_markers(root: Path) -> None:
    """Reconcile every leftover T-1845 land-finish-pending marker under
    `root` -- called at the very START of `_land_core`, right alongside
    `_report_stale_post_land_verify_markers` (T-1523): a prior `frob
    ticket land --finish`/`--retire-on-proof` SIGTERM-killed between the
    marker write and the mutation(s) completing leaves one of these
    behind. READ-ONLY over `root`'s git state -- the worktree/branch this
    marker names may or may not have actually been removed before the
    kill; this function does not attempt to determine which (git itself
    is idempotent for both `worktree remove` on an already-gone path and
    `branch -D` on an already-gone branch, so a human/the next `--finish`
    retry naturally converges either way). It logs a
    `LAND-FINISH-RECOVERED:` line naming what was pending, then clears the
    marker -- surfacing exactly what an interrupted run left ambiguous,
    never blocking the NEW ticket this invocation is actually landing."""
    for ticket_id, commit_sha, retire_on_proof in _stale_land_finish_pending_markers(
        root
    ):
        _log.warning(
            "LAND-FINISH-RECOVERED: a prior `frob ticket land %s "
            "--finish%s` was interrupted after its commit (%s) landed and "
            "verified but before the finish/retire mutation(s) completed "
            "(T-1845) -- worktree removal (and branch deletion, if "
            "retire-on-proof) may or may not have completed; both git "
            "operations are safe to retry/no-op either way",
            ticket_id,
            "/--retire-on-proof" if retire_on_proof else "",
            commit_sha,
        )
        _clear_land_finish_pending_marker(root, ticket_id)


# frob:ticket T-1715
def _refuse_finish_if_worktree_in_use(
    root: Path, worktree: Path, ticket_id: str
) -> None:
    """`_finish_worktree`'s liveness guard, split out to stay under
    ARCH103's per-body complexity budget: `sys.exit(1)`s (worktree left in
    place) if `refuse_if_worktree_in_use` finds either a live process
    cwd'd into `worktree` or an active cross-worktree lease still pinned
    to it -- the land itself already succeeded by this point, so this
    only ever refuses the CLEANUP step, never unwinds anything."""
    guard = refuse_if_worktree_in_use(root, worktree)
    if guard.is_err:
        _log.error(
            "ticket land --finish: %s refusing to remove worktree %s "
            "(%s) -- the land itself already succeeded and is not "
            "affected; land already happened, only cleanup did not -- "
            "retry --finish once the worktree is free, or rerun with "
            "--force if you have independently confirmed it is stale",
            ticket_id,
            worktree,
            guard.danger_err.value,
        )
        sys.exit(1)


# frob:ticket T-1762
def _force_finish_requires_reason(
    root: Path,
    worktree: Path,
    ticket_id: str,
    force_reason: str | None,
    force_reason_file: Path | None,
) -> None:
    """`_finish_worktree`'s T-1762 reason gate, split out to stay under
    ARCH103's per-body complexity budget: resolves `--reason`/
    `--reason-file` (`_archive._resolve_force_reason`'s same shape),
    `sys.exit(1)`s if neither is given, else records the override via
    `record_force_override` (`sys.exit(1)` on a record failure too --
    an unrecorded forced removal is not an acceptable outcome)."""
    from frob.app.ticket_runner._archive import _resolve_force_reason
    from frob.tickets._force_override import record_force_override

    reason = _resolve_force_reason(
        force_reason, force_reason_file, cli_label="ticket land --finish"
    )
    if not reason:
        _log.error(
            "ticket land --finish --force requires --reason TEXT or "
            "--reason-file PATH (T-1762): %s's worktree %s is genuinely "
            "in use and the liveness guard would otherwise refuse",
            ticket_id,
            worktree,
        )
        sys.exit(1)
    recorded = record_force_override(
        root,
        command="ticket land --finish",
        guard="T-1715 worktree-in-use refusal",
        target=f"{ticket_id}:{worktree}",
        reason=reason,
    )
    if recorded.is_err:
        _log.error("ticket land --finish --force: %s", recorded.danger_err)
        sys.exit(1)


# frob:ticket T-1175
# frob:ticket T-1715
# frob:ticket T-1762
# frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_removes_a_worktree_with_no_live_process  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_force_removes_despite_a_live_process  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_finish_worktree_force_requires_reason_when_guard_would_fire  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestFinishWorktree.test_finish_worktree_force_is_a_no_op_reason_wise_when_worktree_is_free  # noqa: E501
def _finish_worktree(
    root: Path,
    worktree: Path,
    ticket_id: str,
    *,
    force: bool = False,
    force_reason: str | None = None,
    force_reason_file: Path | None = None,
) -> None:
    """`frob ticket land --finish`'s worktree-removal half: `git -C root
    worktree remove <worktree>`, called ONLY after `_print_land_proof` has
    already verified the land -- this function itself does no re-
    verification of the LAND-PROOF, it trusts its caller (`_land`) to have
    gated on `ancestor_ok and state_ok` first.

    T-1715: before removing anything, refuses (exits 1, worktree left in
    place) if `refuse_if_worktree_in_use` finds either a live process
    cwd'd into `worktree` or an active cross-worktree lease still pinned
    to it -- this is the fix for the incident where `--finish` deleted
    the calling agent's own worktree out from under it: dispatch briefs
    tell an agent to run `frob ticket land --worktree <their own>` from
    the root checkout, so the natural, documented invocation is the one
    that used to strand the caller. `force=True` (`--force`) skips this
    check entirely, for a worktree independently confirmed genuinely
    wedged -- the process scan cannot always prove a pid is dead.

    T-1762: when the guard would ACTUALLY have refused (the worktree is
    genuinely in use) and `force=True` skips it, a reason is now REQUIRED
    -- exits 1, worktree left in place, if neither `force_reason` nor
    `force_reason_file` is given -- and the override is recorded via
    `frob.tickets._force_override.record_force_override` (WARNING log +
    an append-only `force-overrides.jsonl` line) before the worktree is
    touched. `--force` when the worktree is already free is a no-op
    guard-wise, so no reason is demanded for it.

    Run from `root` (the primary checkout `worktree` belongs to), not
    from an arbitrary cwd -- `git worktree remove` resolves its target
    against the repo the invoking working copy belongs to, so an
    unrelated cwd can spuriously report "not a working tree" even for a
    real, live worktree path. A failed removal (uncommitted stray files,
    a stale lock) is logged at ERROR but does not raise -- the land
    itself already fully succeeded by this point, so a cleanup failure is
    reported separately rather than unwinding anything (playbook section
    12b: never force-remove a worktree the mechanical way, surface it
    instead)."""
    if not force:
        _refuse_finish_if_worktree_in_use(root, worktree, ticket_id)
    elif refuse_if_worktree_in_use(root, worktree).is_err:
        _force_finish_requires_reason(
            root, worktree, ticket_id, force_reason, force_reason_file
        )
    removed = run_argv(["git", "-C", str(root), "worktree", "remove", str(worktree)])
    if removed.is_err or removed.danger_ok.returncode != 0:
        detail = removed.danger_err if removed.is_err else removed.danger_ok.stderr
        _log.error(
            "ticket land --finish: %s could not remove worktree %s: %s -- "
            "remove it by hand once any stray files are resolved",
            ticket_id,
            worktree,
            detail,
        )
        return
    _log.info("ticket land --finish: %s removed worktree %s", ticket_id, worktree)


# frob:ticket T-1003
def _resolve_land_root(root: Path, worktree: Path, ticket_id: str) -> Path:
    """T-1003 (churn item 4): `root` is `(cfg.ticket_path or Path(".")).
    resolve()` -- the invoker's cwd. `land()` itself now resolves the SAME
    "root defaulted to inside --worktree" shape internally, but this CLI
    wrapper's own `root` local is used AGAIN after `land()` returns, for
    `_report_land_result`/`_push_after_land`/`_print_land_proof`/`_finish_
    worktree` -- resolving it here too (same shared helper, not a re-
    implementation) keeps those post-land steps pointed at the real
    primary checkout instead of silently reporting against/pushing
    from/removing the worktree path that was never actually landed onto."""
    from frob.tickets._land import _resolve_primary_checkout

    if root.resolve() != worktree.resolve():
        return root
    resolved_root = _resolve_primary_checkout(worktree)
    if resolved_root is None or resolved_root == worktree.resolve():
        return root
    _log.info(
        "ticket land: %s root defaulted to the cwd inside --worktree (%s) "
        "-- resolved the primary checkout %s from its git common dir "
        "instead (T-1003), no manual cd required",
        ticket_id,
        root,
        resolved_root,
    )
    return resolved_root


# frob:ticket T-1175
# frob:ticket T-1715
# frob:ticket T-1845
# frob:ticket T-1910
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_unverified_land_exits_nonzero_even_without_finish  # noqa: E501
def _finish_land_after_success(
    root: Path, worktree: Path, report, cfg: AppConfig
) -> None:  # noqa: ANN001
    """`_land`'s post-success tail (T-1175, split out of `_land` itself to
    stay under ARCH001's line budget): print the `LAND-PROOF:` line for a
    real (non-dry-run) land, then, if `--finish`/`--retire-on-proof` was
    passed, remove `worktree` -- but ONLY when the proof actually verified.
    A dry run prints nothing here (there is nothing durable yet to prove or
    finish).

    T-1619: `--retire-on-proof` is `--finish` PLUS branch deletion -- the
    one-command "verify then destroy" that makes chaining `frob ticket
    land && git worktree remove` (the unsafe two-step sequence: the
    removal runs unconditionally, even after a failed land, since `&&`
    only guards on `land`'s own exit code and a caller can still chain a
    bare `;` or run the two as separate commands) structurally
    unavailable. The branch name is captured BEFORE `_finish_worktree`
    removes the worktree checkout, and deletion only ever runs after the
    SAME `verified` gate `--finish` already uses -- there is no path from
    an unverified/failed land to either the worktree or its branch being
    touched.

    T-1715: `_finish_worktree` itself also refuses (independent of the
    `verified` gate above) if `worktree` is still provably in use --
    `cfg.ticket_force` (`--force`) is threaded through to override that
    refusal for a worktree confirmed genuinely wedged.

    T-1910: `verified=False` now exits non-zero HERE, unconditionally --
    not only when `--finish`/`--retire-on-proof` was passed. Before this
    fix, a land whose commit never actually became an ancestor of `main`
    (the T-1895 incident: `frob ticket land` printed "landed as <sha>"
    plus a REL001 bump, then `LAND-PROOF: ... verified=False`, and still
    exited 0) reported success to its caller by exit code even though the
    `LAND-PROOF:` line right below it said the opposite -- a script or
    coordinator loop that only checks the exit code, not greps the log
    for `verified=`, sees a clean success and moves on while the real
    code change stays lost. The two lines must never disagree about
    whether the caller should treat this as done."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    if report.dry_run:
        return
    verified = _print_land_proof(root, report)
    if not verified:
        _log.error(
            "ticket land: %s LAND-PROOF did not verify -- the commit "
            "(%s) exists but did NOT reach `main` (or the ticket's "
            "on-main state is not terminal); treat this land as FAILED "
            "despite the 'landed as' line above, investigate with `git "
            "merge-base --is-ancestor %s main` and `git branch --contains "
            "%s`, and recover the commit (e.g. cherry-pick it onto main) "
            "before assuming the work is safe (T-1910)",
            cfg.ticket_id,
            report.commit_sha,
            report.commit_sha,
            report.commit_sha,
        )
        sys.exit(1)
    wants_finish = cfg.ticket_land_finish or cfg.ticket_land_retire_on_proof
    if not wants_finish:
        # T-1720: auto-rebase the worktree's own branch onto the main tip
        # this land just produced -- skipped when `wants_finish` is set,
        # since `_finish_worktree` below is about to remove the checkout
        # entirely and rebasing a worktree seconds before deleting it is
        # pure wasted git work with the same (small) conflict-abort risk
        # for no benefit. The common series-worktree case (no `--finish`,
        # more tickets to land in the same worktree next) is exactly the
        # case this closes.
        _auto_rebase_worktree_onto_main(root, worktree, cfg.ticket_id)
        return
    # T-1910: `verified` is always True by this point -- the unconditional
    # `sys.exit(1)` above already handled the False case for every caller,
    # not just `--finish`/`--retire-on-proof`. Nothing left to gate here.
    branch = (
        _worktree_branch_name(root, worktree)
        if cfg.ticket_land_retire_on_proof
        else None
    )
    # T-1845: write the land-finish-pending marker BEFORE either git
    # mutation below runs -- both are already gated on `verified=True`
    # above, so a SIGTERM anywhere from here through the end of this
    # function is exactly the unmarked window T-1554's design doc audit
    # named. Cleared unconditionally once every mutation this invocation
    # attempted has returned, regardless of their own individual outcome
    # (a mutation failure already logs its own ERROR separately).
    _write_land_finish_pending_marker(
        root,
        cfg.ticket_id,
        report.commit_sha,
        retire_on_proof=cfg.ticket_land_retire_on_proof,
    )
    try:
        _finish_worktree(
            root,
            worktree,
            cfg.ticket_id,
            force=cfg.ticket_force,
            force_reason=cfg.ticket_force_reason,
            force_reason_file=cfg.ticket_force_reason_file,
        )
        if cfg.ticket_land_retire_on_proof:
            _delete_worktree_branch(root, branch, cfg.ticket_id)
    finally:
        _clear_land_finish_pending_marker(root, cfg.ticket_id)


# frob:ticket T-1720
# frob:doc docs/modules/tickets.md#auto-rebase-after-a-successful-land-t-1720
# frob:tests tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain.test_rebases_the_worktree_onto_the_new_main_tip  # noqa: E501
# frob:tests tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain.test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land  # noqa: E501
def _auto_rebase_worktree_onto_main(root: Path, worktree: Path, ticket_id: str) -> None:
    """T-1720: `git rebase <main>` `worktree`'s own branch onto the main
    tip THIS land just produced, best-effort -- closes the repeated,
    by-hand `git rebase main` every multi-ticket series worktree agent
    performed after each successful land in this session (T-1720's own
    evidence: six for six lands, same manual recipe every time), before
    starting the next ticket in the same worktree.

    ORDERING (T-1932's own finding, applied here): this MUST run only
    AFTER `_finish_land_after_success` has already confirmed `verified=
    True` from `_print_land_proof` -- never before. `_print_land_proof`'s
    ancestry/state check reads `root`'s own `main` ref and the just-
    landed commit; this rebase only rewrites `worktree`'s OWN branch
    history and never touches `root` at all, so it cannot retroactively
    invalidate that already-run guard's verdict. Nothing inside THIS same
    `frob ticket land` invocation re-reads the worktree's rewritten
    history afterward, so the rebase introduces no NEW guard for a LATER
    mutation in this call to defeat either -- it is the last thing this
    function does. A future caller that adds a check AFTER this point
    that re-reads `worktree`'s branch state must reason about this
    mutation the same way T-1932 asks every land-path guard to.

    Best-effort, never fails the overall `frob ticket land` invocation
    (the land itself already succeeded and is durable on `main` by the
    time this runs) -- a real conflict aborts the rebase immediately
    (`git rebase --abort`), restoring `worktree` to its exact pre-rebase
    state, and logs a WARNING naming the ticket and worktree for manual
    resolution, rather than leaving the branch mid-rebase (a half-
    mutated worktree is exactly the kind of state a LATER guard -- e.g.
    the next ticket's own T-1922 committed-waive-deletion scan, or its
    pre-work sweep -- could misread). A worktree not on a real branch
    (detached HEAD) or with no resolvable `main` branch name is skipped
    silently -- neither is this function's problem to fix."""
    branch = _worktree_branch_name(root, worktree)
    if branch is None:
        _log.debug(
            "ticket land: %s auto-rebase skipped -- %s is not on a "
            "named branch (detached HEAD)",
            ticket_id,
            worktree,
        )
        return
    main_ref = run_argv(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"])
    if main_ref.is_err or main_ref.danger_ok.returncode != 0:
        _log.warning(
            "ticket land: %s auto-rebase skipped -- could not resolve "
            "%s's current branch name",
            ticket_id,
            root,
        )
        return
    main_branch = main_ref.danger_ok.stdout.strip()
    rebased = run_argv(["git", "-C", str(worktree), "rebase", main_branch])
    if rebased.is_ok and rebased.danger_ok.returncode == 0:
        _log.info(
            "ticket land: %s auto-rebased %s (branch %s) onto %s (T-1720)",
            ticket_id,
            worktree,
            branch,
            main_branch,
        )
        return
    _log.warning(
        "ticket land: %s auto-rebase onto %s failed or conflicted in %s -- "
        "aborting the rebase (T-1720 is best-effort, never fails an "
        "already-successful land) and leaving the worktree exactly as it "
        "was before this attempt; resolve with a manual `git rebase %s` "
        "in %s before starting the next ticket there",
        ticket_id,
        main_branch,
        worktree,
        main_branch,
        worktree,
    )
    run_argv(["git", "-C", str(worktree), "rebase", "--abort"])


# frob:ticket T-1619
def _worktree_branch_name(root: Path, worktree: Path) -> str | None:
    """The short branch name checked out in `worktree` (T-1619), parsed
    from `git -C root worktree list --porcelain`'s stable machine-readable
    format -- `None` if `worktree` is not a registered worktree of `root`,
    is detached (no `branch` line in its record), or the `git` call itself
    fails. Read BEFORE `_finish_worktree` removes the worktree checkout
    (`--retire-on-proof`'s caller) so branch deletion always has a name to
    act on even though `git branch -D` itself does not require the
    worktree to still exist."""
    resolved = worktree.resolve()
    spawned = run_argv(["git", "-C", str(root), "worktree", "list", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    for block in spawned.danger_ok.stdout.split("\n\n"):
        lines = block.splitlines()
        if not lines or not lines[0].startswith("worktree "):
            continue
        if Path(lines[0][len("worktree ") :]).resolve() != resolved:
            continue
        for line in lines[1:]:
            if line.startswith("branch "):
                ref = line[len("branch ") :]
                return ref.removeprefix("refs/heads/")
        return None
    return None


# frob:ticket T-1619
def _delete_worktree_branch(root: Path, branch: str | None, ticket_id: str) -> None:
    """`git -C root branch -D <branch>` (T-1619, `--retire-on-proof`'s
    second half) -- called ONLY after `_finish_worktree` has already
    removed the worktree checkout, and ONLY when the caller's own LAND-
    PROOF gate (`_finish_land_after_success`) has already verified. A
    missing/detached branch name (`branch is None`) is a no-op, logged at
    WARNING rather than treated as a failure -- the worktree removal above
    already succeeded and is the durable half of this operation; a branch
    this repo could not identify is surfaced, not silently swallowed, but
    never turned into a hard failure of an otherwise-successful retire.
    A failed `git branch -D` (e.g. the branch has commits not reachable
    from anything, which `-D` overrides anyway, or a lock contention) is
    logged at ERROR with the exact manual recovery command -- the branch
    is always the recovery path (playbook section 12b) until this step
    itself succeeds, so a failure here must never look silent."""
    if branch is None:
        _log.warning(
            "ticket land --retire-on-proof: %s could not determine the "
            "worktree's branch name -- worktree removed, branch left in "
            "place (nothing to delete blindly)",
            ticket_id,
        )
        return
    deleted = run_argv(["git", "-C", str(root), "branch", "-D", branch])
    if deleted.is_err or deleted.danger_ok.returncode != 0:
        detail = deleted.danger_err if deleted.is_err else deleted.danger_ok.stderr
        _log.error(
            "ticket land --retire-on-proof: %s could not delete branch %s: "
            "%s -- run `git -C %s branch -D %s` by hand once resolved",
            ticket_id,
            branch,
            detail,
            root,
            branch,
        )
        return
    _log.info("ticket land --retire-on-proof: %s deleted branch %s", ticket_id, branch)


def _require_land_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket land`'s required
    `<id>`/`--worktree <path>` args are both present."""
    if cfg.ticket_id is None:
        _log.error("frob ticket land requires <id>")
        sys.exit(1)
    if cfg.ticket_worktree is None:
        _log.error("frob ticket land requires --worktree <path>")
        sys.exit(1)


def _report_land_result(root: Path, report) -> None:  # noqa: ANN001
    """Log every field of a `LandReport`: the dry-run summary line, or the
    landed commit plus each changed file."""
    if report.dry_run:
        _log.info(
            "land %s: DRY RUN clean -- merged=%s wip_committed=%s "
            "(would finalize/close/squash-apply/commit onto %s)",
            report.ticket_id,
            report.merged_main_into_worktree,
            report.wip_committed,
            root,
        )
        return
    _log.info(
        "land %s: landed as %s at %s (%d file(s) changed)",
        report.ticket_id,
        report.final_id,
        report.commit_sha,
        len(report.files_changed),
    )
    for f in report.files_changed:
        _log.info("  %s", f)
    if report.release_bumped_to is not None:
        _log.info(
            "land %s: REL001 bumped to %s",
            report.ticket_id,
            report.release_bumped_to,
        )
    if report.natives_rebuilt:
        _log.info("land %s: native extension(s) rebuilt", report.ticket_id)


# frob:ticket T-0398
def _land_collected_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with no args, AFTER its
    internal merge, to get the post-merge worktree's collected node ids.
    Best-effort -- a collection failure logs and returns an empty set
    (fail-closed: `land`'s post-merge check then treats every non-cmd
    evidence id as unresolved, refusing the landing, rather than silently
    skipping the check)."""

    def fn() -> frozenset[str]:
        from frob.app import ticket_runner as _ticket_runner

        collected = _ticket_runner._collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as unresolved",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, _runners = collected.danger_ok
        return python_ids | rust_ids

    return fn


# frob:ticket T-0398
def _land_passed_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with the post-merge ticket's
    non-cmd evidence ids, AFTER its internal merge, and expects back the
    subset actually observed passing -- reuses `_verify_ids_passing`
    (D-01's same real-run verification) against the worktree."""

    def fn(node_ids) -> frozenset[str]:  # noqa: ANN001
        from frob.app import ticket_runner as _ticket_runner

        collected = _ticket_runner._collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as NOT passing",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, runners = collected.danger_ok
        from frob.app import ticket_runner as _ticket_runner

        return _ticket_runner._verify_ids_passing(
            worktree, node_ids, python_ids, rust_ids, runners
        )

    return fn


# frob:ticket T-0398
# frob:ticket T-0774
def _land_covers_scope_fn(worktree: Path):  # noqa: ANN201
    """D-05/D-02 CLI closure: `land()` calls this TWICE -- once (T-0774) as
    a PRE-merge preflight simulation with the worktree's still-unmerged
    `Ticket` (via `_land_precheck`), and once, as before, with the post-
    merge/post-finalize `Ticket` (via `_land_finalize_and_close`) -- and
    expects back the D-02 scope-binding answer computed against the
    WORKTREE's graph (not root's) either way. `worktree` itself does not
    change between the two calls (it is this same closure's captured
    argument); only the ticket state on disk under it does, since `land`'s
    internal merge mutates the worktree tree in between. The post-merge
    call remains authoritative -- the merged, about-to-be-squashed tree is
    the one whose scope/evidence actually matter -- the pre-merge call is
    only an early, best-effort refusal for the common case where the
    ticket's scope files are untouched by any concurrent main-side change."""

    def fn(ticket):  # noqa: ANN001, ANN202
        from frob.app import ticket_runner as _ticket_runner

        return _ticket_runner._covers_scope_for_ticket(worktree, ticket)

    return fn


# frob:ticket T-1410
def _land_gate_claims_fn(worktree: Path):  # noqa: ANN201
    """T-1410 CLI closure: `land()` calls this ONCE, POST-merge, with the
    reloaded post-merge `Ticket` (mirroring `_land_covers_scope_fn`'s own
    calling convention), and expects back whether every acceptance
    criterion shaped as a package-wide gate-outcome claim ("0 <RULE>
    findings under <glob>") holds against a live `frob check --only gates`
    run in `worktree` -- reuses `_close_gate_claims_for_ticket`'s exact
    computation (T-1410, `frob.app.ticket_runner._close_cmd`), just against
    `worktree` instead of the direct-close path's `root`, so the two
    callers (`frob ticket close`/`reverify` and `frob ticket land`) can
    never drift into two independently hand-typed copies of the same
    check."""

    def fn(ticket):  # noqa: ANN001, ANN202
        from frob.app import ticket_runner as _ticket_runner

        return _ticket_runner._close_gate_claims_for_ticket(worktree, ticket)

    return fn


# frob:ticket T-0338
def _land_bump_version_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this AFTER the squash-apply is staged
    onto `root`, computing whatever `frob.release` says the just-squashed
    public API demands and applying it -- the REL001 half of T-0338's
    coordinator-plumbing consolidation. `frob.release`/`frob.graph` access
    lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_covers_scope_fn`)."""

    def fn(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
        return _apply_release_bump_for_land(root, ticket, final_id)

    return fn


# frob:ticket T-1011
def _land_sync_gate_rules_fn():  # noqa: ANN201
    """CLI closure (T-1011): `land()` calls this AFTER the REL001 bump is
    staged onto `root`, letting a landing that changes `_KNOWN_GATE_RULES`
    (`src/frob/gates/_waive.py`, since T-1072) auto-file the matching `check-coverage.
    yaml` rows in the SAME commit -- ending the manual `frob registry audit
    --sync-gate-rules` re-sync docs/audits/coordination-churn.md's item 6
    disclosed drifting twice in one drive. `frob.gates`/`frob.registry`
    access lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_bump_version_fn`)."""

    def fn(root: Path, pre_land_tip: str):  # noqa: ANN202
        return _sync_gate_rules_for_land(root, pre_land_tip)

    return fn


# frob:ticket T-1011
# frob:ticket T-1805
def _sync_gate_rules_for_land(root: Path, pre_land_tip: str):  # noqa: ANN201
    """The body of `_land_sync_gate_rules_fn`'s callback (T-1011, fixed by
    T-1805): diffs `root`'s just-squashed working tree against
    `pre_land_tip` for `src/frob/gates/_waive.py` -- the file that has
    actually held the `_KNOWN_GATE_RULES` frozenset literal since T-1072
    moved it out of `src/frob/gates/__init__.py` (which now only imports
    and consumes the name, never edits it when a rule id is appended); if
    `_KNOWN_GATE_RULES` does not appear in that diff, nothing needs syncing
    (`Ok(None)`, the common case). If it does, scans `root`'s ON-DISK tree
    (`generated_gate_rule_ids`, the T-0964 scanner -- never a live
    `frob.gates` import, which would read THIS process's own
    already-imported module, not root's freshly-squashed source) for the
    live rule-id set and appends any `check-coverage.yaml` row still
    missing one (`sync_gate_rule_entries`), staging the result. A
    registry-level failure (missing/malformed `check-coverage.yaml`) is
    logged and treated as `Ok(None)` -- best-effort, not a landing-critical
    guarantee the way a REL001 version bump is; only a git staging failure
    (a genuinely broken working tree) escalates to `Err(GitFailed)`, which
    `land()` unwinds exactly like a `bump_version` failure."""
    from frob.gates._rule_id_scan import generated_gate_rule_ids
    from frob.gitio import run_argv
    from frob.registry._staleness import sync_gate_rule_entries
    from frob.tickets._land import LandError

    diffed = run_argv(
        [
            "git",
            "-C",
            str(root),
            "diff",
            pre_land_tip,
            "--",
            "src/frob/gates/_waive.py",
        ]
    )
    if diffed.is_err:
        return Err(LandError.GitFailed)
    if "_KNOWN_GATE_RULES" not in diffed.danger_ok.stdout:
        return Ok(None)

    known = generated_gate_rule_ids(root)
    target = root / "docs" / "design" / "registry" / "check-coverage.yaml"
    synced = sync_gate_rule_entries(target, known)
    if synced.is_err:
        _log.warning(
            "land: gate-rule registry auto-sync skipped (%s at %s) -- run "
            "`frob registry audit --sync-gate-rules` by hand if needed",
            synced.danger_err,
            target,
        )
        return Ok(None)
    added = synced.danger_ok
    if not added:
        return Ok(None)
    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "--",
            "docs/design/registry/check-coverage.yaml",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(added)


# frob:ticket T-0338
# frob:ticket T-1007
def _required_release_bump(root: Path, final_id: str):  # noqa: ANN201
    """The REL001-required version string for `root`'s current public API
    against its tracked release manifest AS RECORDED AT ROOT'S OWN GIT HEAD
    (T-1007 -- never the worktree-carried on-disk copy), or `Ok(None)` if
    no bump is needed (no manifest yet, or `BumpClass.NONE`) -- split out of
    `_apply_release_bump_for_land` to keep each half under the ARCH001
    line-count threshold (T-0338)."""
    from frob.app import ticket_runner as _ticket_runner
    from frob.release import BumpClass, diff_class, required_version
    from frob.tickets._land import LandError

    manifest = _ticket_runner._root_release_manifest(root)
    if manifest is None:
        _log.debug("land: no release manifest at %s HEAD, skipping REL001 bump", root)
        return Ok(None)

    from frob.app import ticket_runner as _ticket_runner

    snapshot = _ticket_runner._graph_snapshot(root)
    if snapshot.is_err:
        _log.error(
            "land: %s graph unavailable (%s), cannot compute REL001 bump",
            final_id,
            snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    bump = diff_class(manifest, snapshot.danger_ok)
    if bump == BumpClass.NONE:
        return Ok(None)

    needed = required_version(manifest.version, bump)
    if needed.is_err:
        _log.error(
            "land: %s manifest version %r is not parseable, cannot compute REL001 bump",
            final_id,
            manifest.version,
        )
        return Err(LandError.ReleaseBumpFailed)
    return Ok(needed.danger_ok)


# frob:ticket T-0338
# frob:ticket T-1007
# frob:ticket T-1368
def _apply_release_bump_for_land(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN201
    """Compute the REL001 bump class for `root`'s just-squashed public API
    against its release manifest -- read from ROOT's OWN git HEAD via
    `_root_release_manifest` (T-1007: never the worktree-carried on-disk
    copy that rides the squash-apply, the root cause of the repeat
    monotonicity-guard refusals T-0992 could only catch, not prevent) --
    and, if the declared version does not already cover it, bump
    `pyproject.toml`'s `version`, append a minimal CHANGELOG.md entry
    (satisfies `_changelog_mentions`'s "the version string appears
    somewhere" contract), and `frob release stamp` the new manifest --
    staging all three files in `root`'s index so they land in the same
    commit as the squash-apply (T-0338).

    Returns `Ok(None)` (no write at all) when no manifest exists yet (the
    repo has never opted into `frob release stamp`) or when the diff class
    is `BumpClass.NONE`; `Ok(new_version)` after a successful bump+stamp;
    `Err(LandError.ReleaseBumpFailed)` on any failure along the way (an
    unreadable manifest, an unparsable `pyproject.toml` version, a graph
    build failure, or -- T-1368 -- `stamp`'s own write failing, e.g. its
    `enforce_worktree_lease` refusal) -- fail-closed, since a silently-
    skipped bump would let a landed API change slip past REL001
    undetected."""
    from frob.gitio import run_argv
    from frob.release import stamp
    from frob.tickets._land import LandError

    needed = _required_release_bump(root, final_id)
    if needed.is_err:
        return Err(needed.danger_err)
    if needed.danger_ok is None:
        return Ok(None)
    new_version = needed.danger_ok

    written = _write_release_bump(root, ticket, final_id, new_version)
    if written.is_err:
        return Err(written.danger_err)

    from frob.app import ticket_runner as _ticket_runner

    fresh_snapshot = _ticket_runner._graph_snapshot(root)
    if fresh_snapshot.is_err:
        _log.error(
            "land: %s graph unavailable post-bump (%s), cannot stamp release manifest",
            final_id,
            fresh_snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    stamped = stamp(root, fresh_snapshot.danger_ok, new_version)
    if stamped.is_err:
        # T-1368: `stamp`'s Result used to be discarded here -- a write
        # failure (its own `enforce_worktree_lease` refusal, or any future
        # failure mode `stamp` grows) silently fell through to `git add
        # .frob-release.json` below, staging whatever (possibly stale)
        # content already happened to be on disk instead of the fresh
        # bump. Propagate it the same fail-closed way every other error
        # path in this function already does.
        _log.error(
            "land: %s failed to stamp release manifest at %s (%s)",
            final_id,
            new_version,
            stamped.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "pyproject.toml",
            "CHANGELOG.md",
            ".frob-release.json",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage the REL001 bump files", final_id)
        return Err(LandError.ReleaseBumpFailed)
    return Ok(new_version)


# frob:ticket T-0338
# frob:ticket T-1009
def _write_release_bump(root: Path, ticket, final_id: str, new_version: str):  # noqa: ANN001, ANN201
    """Rewrite `root/pyproject.toml`'s `version = "..."` line to
    `new_version` and add a `## [new_version] - unreleased` CHANGELOG.md
    entry naming `final_id`/`ticket.title` (T-0338), via the shared
    `frob.release` helpers (T-1009 -- the same regex/insertion logic
    `frob release sync` uses, kept in one home rather than duplicated
    here)."""
    from frob.release import changelog_skeleton_entry, rewrite_pyproject_version
    from frob.tickets._land import LandError

    pyproject_path = root / "pyproject.toml"
    rewritten = rewrite_pyproject_version(root, new_version)
    if rewritten.is_err:
        _log.error(
            'land: %s could not find a `version = "..."` line in %s (%s)',
            final_id,
            pyproject_path,
            rewritten.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    changelog_skeleton_entry(root, new_version, note=f"{final_id}: {ticket.title}")
    _log.info(
        "land: %s wrote REL001 bump -> %s in %s and CHANGELOG.md",
        final_id,
        new_version,
        pyproject_path,
    )
    return Ok(None)


# frob:ticket T-0338
def _land_rebuild_natives_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this with `root` only when the landed
    changeset touches a native source tree (frob-core/, strata-core/) --
    runs `make core` in `root` and returns whether it exited 0 (T-0338).
    Best-effort: `land` treats a `False` as a logged warning, never a hard
    failure (a native rebuild is cheap to re-run by hand, and a `make
    core` failure in a from-scratch clone is not necessarily this land's
    fault)."""

    def fn(root: Path) -> bool:
        # T-0803: routed through `guarded_subprocess_run` (T-0778's guard)
        # so `FROB_DISABLE_EXEC=1` refuses this `make core` spawn too;
        # treated as a failed rebuild (`False`, logged) rather than a hard
        # error, matching this function's existing best-effort contract.
        from frob.app import ticket_runner as _ticket_runner

        guarded = _ticket_runner.guarded_subprocess_run(
            ["make", "core"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "land: `make core` in %s refused to spawn (%s)",
                root,
                ProcessGuardError.ExecDisabled,
            )
            return False
        result = guarded.danger_ok
        if result.returncode != 0:
            _log.warning(
                "land: `make core` in %s exited %d -- stdout=%r stderr=%r",
                root,
                result.returncode,
                result.stdout[-2000:],
                result.stderr[-2000:],
            )
        return result.returncode == 0

    return fn


# frob:ticket T-1369
def _warn_land_override_flags(cfg: AppConfig) -> None:
    """`_land`'s flag-warning phase: log a WARNING for each land-time
    refusal override (`--skip-mutation-evidence`, `--allow-cross-ticket`)
    that is set, so an override that lets a real finding through is at
    least visible in the log, even though it does not stop this land."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller
    if cfg.ticket_skip_mutation_evidence:
        _log.warning(
            "ticket land: %s --skip-mutation-evidence set -- a TEST016 "
            "confirmatory-only-evidence finding will be logged but will NOT "
            "refuse this land (justification required: use only for a "
            "genuine false positive)",
            cfg.ticket_id,
        )
    if cfg.ticket_allow_cross_ticket:
        _log.warning(
            "ticket land: %s --allow-cross-ticket set -- a CrossTicketLeakage "
            "finding will be logged but will NOT refuse this land "
            "(justification required: use only when the joint landing is "
            "genuinely intentional, e.g. a series worktree or an open epic's "
            "umbrella scope over its own leaf)",
            cfg.ticket_id,
        )


# frob:ticket T-1456
# frob:ticket T-1463
def _spawn_baseline_snapshot_worktree(root: Path, sha: str) -> Path | None:
    """T-1463: create a detached, throwaway `git worktree` checkout of
    `root` at `sha` so the pre-land baseline scan (`_unscoped_error_
    findings`) can run against an IMMUTABLE snapshot instead of `root`'s
    live working tree. This is what makes running the baseline scan
    CONCURRENTLY with `land()`'s own merge into `root` safe: without a
    snapshot, a background scan reading `root` directly would race
    `land()`'s merge writing to those same files mid-scan, producing a
    baseline that is neither the true pre-land state nor the post-merge
    one. Returns `None` (never raises) on any git failure -- the caller
    falls back to the pre-T-1463 sequential, direct-on-`root` scan, same
    as if this function did not exist."""
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="frob-land-baseline-"))
    added = run_argv(
        ["git", "-C", str(root), "worktree", "add", "--detach", str(tmp_dir), sha]
    )
    if added.is_err or added.danger_ok.returncode != 0:
        _log.warning(
            "ticket land: baseline snapshot worktree creation failed at %s -- "
            "baseline capture will run sequentially against root instead",
            sha,
        )
        return None
    return tmp_dir


# frob:ticket T-1463
def _remove_baseline_snapshot_worktree(root: Path, tmp_dir: Path) -> None:
    """Best-effort cleanup of `_spawn_baseline_snapshot_worktree`'s temp
    checkout (T-1463): logged, never raised, on failure -- a leaked
    worktree registration is a cheap, later-swept nuisance (`frob worktree
    sweep`, playbook section 12b), not a land-blocking error."""
    removed = run_argv(
        ["git", "-C", str(root), "worktree", "remove", "--force", str(tmp_dir)]
    )
    if removed.is_err or removed.danger_ok.returncode != 0:
        _log.warning(
            "ticket land: failed to remove baseline snapshot worktree %s -- "
            "run `frob worktree sweep` later to clean it up",
            tmp_dir,
        )


# frob:ticket T-1456
# frob:ticket T-1463
def _capture_pre_land_baseline(
    root: Path, cfg: AppConfig
) -> tuple[str | None, frozenset[tuple[str, str]] | None]:
    """`_land`'s baseline-capture phase (T-1456): before `land()` runs,
    record `root`'s current HEAD sha and its unscoped error-finding
    identity set -- the exact pair `_post_land_unscoped_error_sweep`
    compares a post-land scan against. Skipped outright (returns
    `(None, None)`) for a `--dry-run`, since nothing will actually land on
    `root` to compare a post-land state against.

    T-1463: scans a detached snapshot worktree at the captured HEAD sha
    (`_spawn_baseline_snapshot_worktree`) instead of `root` directly, when
    that snapshot can be created -- this is what lets `_land` run this
    whole function in a background thread WHILE `land()`'s own merge
    proceeds on `root`, instead of paying for the two sequentially (this
    scan's ~budget-bounded wall time was previously pure dead time added
    on top of `land()`'s own worktree-scoped checks, and was the single
    biggest reason a land could exceed the playbook's foreground budget).
    Falls back to scanning `root` directly (the pre-T-1463 behavior) if
    the snapshot worktree cannot be created for any reason."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller
    if cfg.ticket_dry_run:
        return None, None
    pre_land_sha: str | None = None
    rev = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    if rev.is_ok and rev.danger_ok.returncode == 0:
        pre_land_sha = rev.danger_ok.stdout.strip()
    if pre_land_sha is None:
        pre_land_findings = _unscoped_error_findings(root, cfg.ticket_id)
        return pre_land_sha, pre_land_findings
    snapshot = _spawn_baseline_snapshot_worktree(root, pre_land_sha)
    if snapshot is None:
        pre_land_findings = _unscoped_error_findings(root, cfg.ticket_id)
        return pre_land_sha, pre_land_findings
    try:
        pre_land_findings = _unscoped_error_findings(snapshot, cfg.ticket_id)
    finally:
        _remove_baseline_snapshot_worktree(root, snapshot)
    return pre_land_sha, pre_land_findings


# frob:ticket T-1514
def _land_pre_commit_sweep_fn(
    baseline_thread,  # noqa: ANN001
    baseline_holder: list[tuple[str | None, frozenset[tuple[str, str]] | None]],
    cfg: AppConfig,
):  # noqa: ANN201
    """CLI closure: `land()` calls this (via `pre_commit_sweep`) at the last
    checkpoint before its final commit. Joins the T-1463 background
    baseline-capture thread first (a no-op if it already finished, which
    it almost always has by this point in `land()`'s own sequential work)
    so this reuses the SAME pre-land finding set the post-land sweep
    (the inline marker-write/sweep/marker-clear sequence in the land CLI
    entrypoint, T-1523) also consumes -- no second baseline
    scan. `None` (skip) if the baseline thread produced nothing (e.g. a
    dry run, where `_capture_pre_land_baseline` returns `(None, None)`)."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller
    ticket_id: str = cfg.ticket_id  # closure-stable narrowed binding

    def sweep(root: Path, final_id: str) -> bool | None:
        baseline_thread.join()
        _pre_land_sha, pre_land_findings = (
            baseline_holder[0] if baseline_holder else (None, None)
        )
        return _pre_commit_unscoped_error_sweep(
            root, ticket_id, final_id, pre_land_findings
        )

    return sweep


# frob:ticket T-1269
def _land_plan_check_ticks_fn(root: Path):  # noqa: ANN201
    """Build a zero-arg `check_ticks` closure for `land_plan` (T-1269):
    spawns `frob check --only tickets` in `root` (post-merge) and returns
    whether `gate:TICK`'s own line reports 0 errors -- `None` (unmeasurable,
    `land_plan` treats this as "skip", never as "dirty") if the spawn is
    refused/fails or the line cannot be found, matching the same
    unmeasured-is-not-a-value posture `_check_gates_summary_fn` already
    uses for the identical failure mode."""
    tick_line_re = re.compile(r"gate:TICK\s+(\d+)\s+errors?")

    def check_ticks() -> bool | None:
        from frob.app import ticket_runner as _ticket_runner

        guarded = _ticket_runner.guarded_subprocess_run(
            [_python_for_tree(root), "-m", "frob", "check", "--only", "tickets"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "ticket land --plan: `frob check --only tickets` refused to "
                "spawn (%s) -- TICK-gate re-check skipped",
                ProcessGuardError.ExecDisabled,
            )
            return None
        match = tick_line_re.search(guarded.danger_ok.stdout)
        if match is None:
            _log.warning(
                "ticket land --plan: could not parse a gate:TICK line from "
                "`frob check --only tickets` output -- TICK-gate re-check "
                "skipped"
            )
            return None
        return int(match.group(1)) == 0

    return check_ticks


# frob:ticket T-1269
def _land_plan_cmd(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land --plan --worktree PATH [--dry-run]` (T-1269): land
    a design-phase worktree via `frob.tickets.land_plan` -- merge, finalize
    every incoming draft id, TICK-gate re-check, atomic commit -- reporting
    every field of the resulting `LandPlanReport` (or the `Err` + remedy
    already logged by `land_plan` itself) before exiting non-zero on
    failure."""
    from frob.tickets._land import land_plan

    if cfg.ticket_worktree is None:
        _log.error("frob ticket land --plan requires --worktree <path>")
        sys.exit(1)
    worktree = cfg.ticket_worktree

    result = land_plan(
        root,
        worktree,
        dry_run=cfg.ticket_dry_run,
        check_ticks=_land_plan_check_ticks_fn(root),
    )
    if result.is_err:
        _log.error("ticket land --plan failed: %s", result.danger_err)
        sys.exit(1)

    report = result.danger_ok
    if report.dry_run:
        _log.info(
            "land --plan: DRY RUN clean -- merge_commit=%s finalized=%s "
            "(would commit onto %s)",
            report.merge_commit,
            list(report.finalized),
            root,
        )
        return
    _log.info(
        "land --plan: landed onto %s -- merge_commit=%s finalized=%s commit=%s",
        root,
        report.merge_commit,
        list(report.finalized),
        report.commit_sha,
    )


# frob:ticket T-1463
# frob:ticket T-1495
# frob:ticket T-1444
# frob:ticket T-1518
# frob:ticket T-1884
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.test_cli_land_invoked_with_root_equal_to_worktree_still_verifies  # noqa: E501
def _land(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> [--dry-run]`: run the whole
    merge-check-splice-close-commit chain via `frob.tickets.land`, reporting
    every field of the resulting `LandReport` (or the exact `Err` + remedy
    already logged by `land` itself) before exiting non-zero on failure.

    T-0398: this is the CLI's STRICT default -- `collected`/`passed`/
    `covers_scope` are ALWAYS supplied (as closures over the worktree,
    since `land`'s internal merge determines the post-merge state they
    must be computed against, see `land`'s own docstring), so a stale/
    red/unrelated evidence id can never silently land onto main through
    the real `frob ticket land` command, even though the library function
    itself still defaults to permissive (`None`) for other callers/tests.

    T-0338: `bump_version`/`rebuild_natives` are ALSO always supplied here
    (`_land_bump_version_fn`/`_land_rebuild_natives_fn`), folding the
    REL001 version-bump/stamp and native-rebuild-trigger coordinator steps
    into this same one command.

    T-0754: `check_gates` (`_check_gates_summary_fn`, the SAME closure
    `_done_report` captures with) is ALSO always supplied here, so a
    ticket carrying a `### Captured claims` section is re-verified against
    the post-merge tree before `frob ticket land` ever finalizes/closes/
    squash-applies it. The claim's test-count half reuses `passed` above
    -- no separate `run_tests` parameter at the land layer (review round 2
    fix #3: derive from D-05's own real run instead of a duplicate one).

    T-1410: `check_gate_claims` (`_land_gate_claims_fn`) is ALSO always
    supplied here, so a ticket carrying a "0 <RULE> findings under <glob>"
    acceptance criterion refuses to land while the post-merge tree still
    reports live findings for that rule under that glob -- the T-1276
    defect (closed done and landed against 116 live TEST005 findings under
    its own criterion's glob) is now refused at the real land path.

    T-1463: the pre-land baseline capture (`_capture_pre_land_baseline`) is
    started in a background thread BEFORE `land()` is called, and joined
    only once its result is actually needed (the post-land sweep sequence
    below, after `land()` returns) -- it scans an isolated snapshot worktree, not
    `root` itself (see `_capture_pre_land_baseline`'s docstring), so it is
    safe to run while `land()` merges into `root` at the same time. This
    overlaps the baseline scan's own budget-bounded wall time with
    whatever `land()` spends on its own worktree-scoped checks instead of
    paying for both sequentially, which was the single largest reason a
    land exceeded the playbook's foreground budget.

    T-1514: `pre_commit_sweep` (`_land_pre_commit_sweep_fn`) reuses that
    SAME baseline thread/result to run the unscoped error sweep AGAIN,
    inside `land()`, at the last checkpoint before its final commit --
    while `root`'s working tree still holds only the staged, uncommitted
    squash-apply changeset. A refusal there costs nothing and reverts no
    real commit (`_verified_reset_root` on a staged-but-uncommitted tree),
    unlike the post-land sweep's own post-commit `git reset --hard`
    below, which stays wired in unchanged as a cheap final assertion."""
    if cfg.ticket_land_plan:
        _land_plan_cmd(root, cfg)
        return

    if cfg.ticket_land_queue:
        _land_enqueue(root, cfg)
        return

    if cfg.ticket_land_drain:
        _land_drain(root, cfg)
        return

    if cfg.ticket_land_run_mutation_sweep:
        _run_batch_mutation_sweep(root)
        return

    _require_land_args(cfg)
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    # frob:ticket T-1884
    # T-1884: resolve `root` HERE, once, before `_land_core` runs -- NOT
    # after. `_resolve_land_root`'s own docstring already documented the
    # intent ("this CLI wrapper's own `root` local is used AGAIN after
    # `land()` returns ... resolving it here too keeps those post-land
    # steps pointed at the real primary checkout"), but no call site at
    # this level ever actually existed: `_land_core_prepare` resolves its
    # OWN internal `root` local for the merge/commit itself, and that
    # resolved value was never threaded back out to this function. When
    # `root` starts out equal to `worktree` (a `frob ticket land`
    # invoked with cwd inside the worktree, or `--worktree` doubling as
    # the effective root), this function's `root` stayed pointed at the
    # worktree for every step below -- `_report_land_result`, an
    # optional `_push_after_land`, and (T-1884's own measured incident,
    # T-1895) `_finish_land_after_success`'s `_print_land_proof` call,
    # which computes `is_ancestor_of_main` via `git -C root merge-base
    # --is-ancestor <sha> main` against the WRONG checkout -- the
    # worktree branch the commit was merged FROM, not the primary
    # checkout it was merged ONTO. That checkout never receives the
    # commit under its own `main` ref, so the ancestry check reads
    # `False` even though the land fully succeeded -- not a ref-update
    # visibility race, a query against the wrong directory entirely.
    # Resolving once, up front, and reusing the SAME value for
    # `_land_core` and every post-land step below closes this: there is
    # only one `root` for the whole call, and it is always the real
    # primary checkout.
    root = _resolve_land_root(root, worktree, cfg.ticket_id)

    result = _land_core(root, cfg)
    if result.is_err:
        _log.error("ticket land failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    _report_land_result(root, report)

    if cfg.ticket_land_push:
        _push_after_land(root, report)

    _finish_land_after_success(root, worktree, report, cfg)


# frob:ticket T-1444
def _land_core(root: Path, cfg: AppConfig):  # noqa: ANN201
    """The whole merge-check-splice-close-commit-sweep chain
    (`frob.tickets.land` plus T-1456's post-land unscoped-error sweep),
    WITHOUT any of `_land`'s CLI-only tail (report/push/finish) -- the
    reusable core both the single-ticket `frob ticket land <id>` path and
    T-1444's `_land_drain` loop call, parametrized entirely by `cfg`
    (`cfg.ticket_id`/`cfg.ticket_worktree`/`cfg.ticket_dry_run`, etc.)
    rather than a specific ticket baked in at the call site. Returns
    `Result[LandReport, LandError]` -- unlike `_land`'s old inline body,
    this NEVER calls `sys.exit`: a post-land sweep revert reports
    `LandError.PostLandUnscopedSweepFailed` instead of killing the
    process, so a caller looping over several tickets (`_land_drain`) can
    attribute the failure to the one ticket that caused it and continue
    with the rest, matching this ticket's own acceptance criterion
    ("a failing ticket is named and dequeued alone").

    T-1593: split along T-1518's stage seams into `_land_core_prepare`
    (pre-merge setup), `_land_core_start_baseline` (T-1463 background
    baseline capture), `_land_core_invoke` (the actual `land()` call), and
    `_land_core_finish_post_land` (T-1523 post-land verification) -- this
    function is now just the glue between those stages, same call order
    and short-circuit/error semantics as before the split."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    root, rapid_land = _land_core_prepare(root, cfg, worktree)

    baseline_thread, baseline_holder = _land_core_start_baseline(
        root, cfg, rapid_land=rapid_land
    )

    result = _land_core_invoke(
        root, cfg, worktree, rapid_land, baseline_thread, baseline_holder
    )
    if result.is_err:
        baseline_thread.join()
        return result

    report = result.danger_ok

    # T-1463: join only now -- the background baseline scan has had this
    # whole land() call's wall time to finish concurrently; a slow scan
    # just blocks here a little longer, it never blocked land() itself.
    baseline_thread.join()
    pre_land_sha, pre_land_findings = (
        baseline_holder[0] if baseline_holder else (None, None)
    )

    return _land_core_finish_post_land(
        root, cfg, report, pre_land_sha, pre_land_findings, rapid_land=rapid_land
    )


# frob:ticket T-1982
def _ty_configured_excludes(worktree: Path) -> tuple[str, ...]:
    """`pyproject.toml`'s `[tool.ty.src] exclude = [...]`, the SAME globs
    a bare `ty check <root>` (no explicit paths) already honors natively
    -- read here because `_ty_check_files` passes EXPLICIT paths instead
    (T-1907's own touched-set scoping), and an explicit path silently
    overrides a config exclude for `ty` (confirmed: `tests/fixtures/**`
    is excluded here yet a fixture named on the command line still gets
    checked). Absent/unparsable `pyproject.toml`, or a malformed/missing
    `[tool.ty.src].exclude`, both degrade to `()` -- no excludes, i.e.
    the pre-T-1982 behavior (over-checking, never under-checking) --
    matching `frob.excludes.load_exclude_globs`'s own fail-open posture
    for the analogous `frob.toml [graph] exclude` read."""
    import tomllib

    toml_path = worktree / "pyproject.toml"
    if not toml_path.exists():
        return ()
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return ()
    globs = doc.get("tool", {}).get("ty", {}).get("src", {}).get("exclude", [])
    if not isinstance(globs, list) or not all(isinstance(g, str) for g in globs):
        return ()
    return tuple(globs)


# frob:ticket T-1907
# frob:ticket T-1982
def _touched_py_files(
    worktree: Path, touched_paths: frozenset[str] | None
) -> list[str]:
    """The `.py` subset of `touched_paths` that still exists in `worktree`
    AND is not covered by `pyproject.toml`'s own `[tool.ty.src].exclude`
    (T-1982: `_ty_check_files` passes these as EXPLICIT paths, which
    bypasses that exclude entirely if this function does not filter it
    itself first) -- sorted for a deterministic `ty` invocation. The pure
    filtering half of `_assert_touched_files_type_check_pre_land`, split
    out so that function's own body stays a flat sequence with no nested
    filtering logic."""
    if not touched_paths:
        return []
    from frob.excludes import is_excluded

    ty_excludes = _ty_configured_excludes(worktree)
    return sorted(
        rel
        for rel in touched_paths
        if rel.endswith(".py")
        and (worktree / rel).is_file()
        and not is_excluded(rel, ty_excludes)
    )


# frob:ticket T-1907
# frob:waive ARCH103 reason="build-the-command-then-run-it IS this function's one job \
# -- the two decision points (src/.venv presence) are command-construction branches, \
# not independent sub-concerns, and splitting the subprocess spawn away from the \
# command that feeds it would add indirection with no cohesion gain; mirrors \
# frob.check._python._run_ty's own identical shape, already precedented in this \
# codebase"
def _ty_check_files(worktree: Path, py_files: list[str]):  # noqa: ANN201
    """Spawn `ty check <py_files>` scoped to `worktree` and return its
    parsed `ToolResult`, or `None` if the spawn itself could not run (no
    `ty` binary, or it hung past the timeout) -- the pure subprocess-and-
    parse half of `_assert_touched_files_type_check_pre_land`, split out
    so that function's own body carries no I/O beyond calling this once.
    Mirrors `frob.check._python._run_ty`'s own `--extra-search-path`/
    `--python` resolution (T-0996) but scoped to explicit files rather
    than a whole root, since this is a touched-set check, not a full-tree
    one."""
    import subprocess

    from frob.process.parsers import parse_ty

    cmd = ["ty", "check", *py_files]
    src_dir = worktree / "src"
    if src_dir.is_dir():
        cmd += ["--extra-search-path", str(src_dir.resolve())]
    venv_dir = worktree / ".venv"
    if venv_dir.is_dir():
        cmd += ["--python", str(venv_dir.resolve())]
    try:
        proc = subprocess.run(
            cmd, cwd=worktree, capture_output=True, text=True, timeout=120, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return parse_ty(proc.stdout + proc.stderr, exit_code=proc.returncode)


# frob:ticket T-1907
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_type_error_in_a_touched_file_refuses_the_land  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_a_clean_touched_file_does_not_refuse  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_empty_touched_set_is_a_no_op  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand.test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error  # noqa: E501
# frob:waive ARCH103 reason="this IS _assert_design_loads_pre_land's own established \
# guard shape one function up in this same module (filter/spawn/decide-refuse-or-not, \
# three short-circuit returns): the decision points are early-outs for 'nothing to \
# check' and 'could not measure', not independent sub-concerns to split out, and the \
# filtering/spawning halves are already extracted into \
# _touched_py_files/_ty_check_files above"
def _assert_touched_files_type_check_pre_land(
    worktree: Path, ticket_id: str, touched_paths: frozenset[str] | None
) -> None:
    """T-1907: refuse the land (`sys.exit(1)`) when `ty check` finds an
    error in one of THIS ticket's own touched `.py` files. Writes nothing,
    read-only, unconditional -- called from `_land_core_prepare` for every
    profile, including `rapid`, because that is exactly the gap T-1907
    measured: under rapid, agents commonly verify with a scoped `frob
    check --ticket <id> --only ...` selection that omits the `ty` family
    entirely, land green, and the type error is only ever discovered by
    the DEFERRED post-land sweep -- against an already-published commit
    (T-1894/T-1896, both real `invalid-argument-type` errors that landed
    this way). `land()`'s own post-merge `check_gates()` re-verification
    does not close this gap either: it only ever executes when the
    ticket's Done report captured a claim to compare against
    (`_reverify_done_report_claims_post_merge`'s `claims is None: return
    Ok(None)` early-out) -- an agent whose done-report never captured
    gate state (or captured a scoped one) gets NO fresh gate re-check at
    land at all, silent unknown read as clean, precisely the "UNKNOWN is
    being read as CLEAN" framing T-1907's own investigation names.

    Scoped to `touched_paths` (T-1404's own diff-derived touched-file
    set, reused rather than a second hand-rolled diff) so this stays
    cheap -- a single `ty check <touched .py files>` invocation
    (`_ty_check_files`), not a full-tree run -- and restricted to files
    this ticket's own diff actually introduced, not a repo-wide type-debt
    refusal. An empty touched `.py` subset, or a spawn that could not run
    at all, is a no-op: there is nothing new to type-check (or nothing
    measurable), matching every other touched-set guard's degrade-to-no-
    op-not-refuse posture in this module when the touched set itself is
    unknown."""
    py_files = _touched_py_files(worktree, touched_paths)
    if not py_files:
        return
    parsed = _ty_check_files(worktree, py_files)
    if parsed is None:
        _log.warning(
            "ticket land: %s pre-land touched-file type check could not "
            "run -- skipped, not treated as a refusal",
            ticket_id,
        )
        return
    errors = [d for d in parsed.diagnostics if d.severity == "error"]
    if not errors:
        return
    _log.error(
        "ticket land: %s refused -- `ty check` found %d error(s) in this "
        "ticket's own touched file(s) (%s); a scoped `frob check --only "
        "ty`/`frob check` re-run before retrying `frob ticket land %s` "
        "names the exact line(s) (T-1907: this family is not relaxed by "
        "the rapid profile)",
        ticket_id,
        len(errors),
        ", ".join(py_files),
        ticket_id,
    )
    sys.exit(1)


# frob:ticket T-1593
# frob:ticket T-1692
# frob:ticket T-1845
def _land_core_prepare(root: Path, cfg: AppConfig, worktree: Path) -> tuple[Path, bool]:
    """Pre-merge setup seam of `_land_core` (T-1593 split): T-1175 auto-fix
    absorption, root resolution, T-1523 stale-marker reconciliation, T-1575
    profile check, the override-flag warning, and (T-1692) the
    backpressure check -- pure extraction of the original leading block,
    plus the new backpressure block appended after profile resolution.
    Returns `(resolved_root, rapid_land)`.

    T-1907: also runs `_assert_touched_files_type_check_pre_land`
    immediately after the T-1175 absorption step, UNCONDITIONALLY (every
    profile, including rapid) -- the minimum pre-land gate the rapid
    profile may not relax, per T-1907's own required fix (1)."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller

    # T-1175: fmt/sync-interface/Tier-A-fix absorption runs BEFORE land's
    # own merge, in dry-run and real mode alike (a dry run should preview
    # the exact same landed state a real run would produce) -- any file
    # rewritten here becomes an ordinary uncommitted change `land()`'s own
    # wip-commit step already picks up, so this needs no separate commit.
    _absorb_pre_land_fixes(worktree, cfg.ticket_id)

    # frob:ticket T-1907
    _assert_touched_files_type_check_pre_land(
        worktree, cfg.ticket_id, _land_touched_paths(worktree, cfg.ticket_id)
    )

    root = _resolve_land_root(root, worktree, cfg.ticket_id)

    # T-1523: reconcile any leftover post-land-verify-pending marker from
    # a PRIOR invocation crashing between its own commit and its own
    # verification tail, before this invocation touches anything new --
    # run against the RESOLVED root (the real primary checkout, not a
    # possibly-still-worktree-pointed cfg default).
    _report_stale_post_land_verify_markers(root)

    # T-1845: reconcile any leftover land-finish-pending marker from a
    # PRIOR invocation's `--finish`/`--retire-on-proof` being SIGTERM-
    # killed between the marker write and the mutation(s) finishing --
    # same "reconcile before this invocation touches anything new" timing
    # as its T-1523 sibling immediately above.
    _report_stale_land_finish_pending_markers(root)

    _warn_land_override_flags(cfg)

    # frob:ticket T-1575
    # T-1575: rapid profile skips the T-1514 pre-commit sweep ("single
    # post-land sweep with revert-on-red, no pre-commit sweep" -- this
    # ticket's own text). The T-1463 baseline-capture thread below still
    # runs even under rapid: it is ALSO what feeds the post-land sweep a
    # few lines further down (same thread/result, per T-1514's own
    # docstring), and rapid keeps that one -- only the pre-commit half is
    # skipped here. A fully baseline-thread-free rapid path is disclosed
    # as deferred follow-up, not implemented in this pass (see the T-1575
    # Done report).
    from frob.tickets._profile import ProfileName, effective_profile

    _profile_result = effective_profile(worktree)
    effective = (
        _profile_result.danger_ok if _profile_result.is_ok else ProfileName.STANDARD
    )
    rapid_land = effective is ProfileName.RAPID
    if rapid_land:
        _log.info(
            "ticket land: %s effective profile is rapid (T-1575) -- "
            "skipping the pre-commit sweep, single post-land sweep only",
            cfg.ticket_id,
        )

    _apply_backpressure(root, cfg, effective)
    return root, rapid_land


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1693
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_not_quarantined_is_unchanged  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_quarantined_forces_synchronous  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_corrupt_store_also_forces_synchronous  # noqa: E501
def _quarantine_override_ceilings(
    root: Path,
    ceilings,
    *,
    ticket_id: str | None,  # noqa: ANN001
):
    """T-1693: while quarantine is raised, deferred landing is OFF --
    this land either runs fully synchronous verification (the credit
    line is suspended, not the work) or blocks, per profile. Reuses the
    EXISTING `frob.verify.block_until_watermark_advances` mechanism
    (T-1692) as the enforcement point rather than adding a second,
    parallel gate: forcing `BackpressureCeilings(max_depth=0,
    max_age_s=0.0)` -- the same shape `ceilings_for_profile` already
    gives `fortress` -- makes ANY queued-but-unverified commit trip
    immediately, regardless of the land's own profile, exactly matching
    fortress's "refuse on red" posture for the duration of the
    quarantine.

    `is_quarantined`'s own `Err` (a corrupt `.frob/quarantine.json`) is
    treated the SAME as `True` here -- "cannot verify is never verified"
    extends to this call site too: an unreadable quarantine store must
    never be misread as "quarantine is not raised", the direction that
    would silently let deferred landing resume."""
    from frob.verify._backpressure import BackpressureCeilings
    from frob.verify._quarantine import is_quarantined

    quarantined = is_quarantined(root)
    if quarantined.is_ok and not quarantined.danger_ok:
        return ceilings

    _log.error(
        "ticket land: %s quarantine is raised (or its store could not be "
        "read) -- deferred landing is OFF, forcing fully-synchronous "
        "verification for this land regardless of profile (T-1693)",
        ticket_id if ticket_id is not None else "<no ticket id>",
    )
    return BackpressureCeilings(max_depth=0, max_age_s=0.0)


# frob:ticket T-1693
# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_no_quarantine_is_a_noop  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_real_attributed_finding_never_auto_clears  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_synthetic_finding_clears_once_status_is_untripped  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_synthetic_finding_stays_raised_while_still_tripped  # noqa: E501
def _auto_clear_synthetic_quarantine(root: Path, ceilings) -> None:  # noqa: ANN001
    """The ONLY case this land path ever auto-clears a raised quarantine:
    every recorded finding is `_raise_quarantine_on_persistent_block_
    timeout`'s own synthetic `"BACKPRESSURE_TIMEOUT"` marker (never a
    real T-1690-attributed finding), AND the underlying backpressure
    status (checked fresh, against `ceilings` -- the profile's REAL
    ceilings, not the T-1693 override `_quarantine_override_ceilings`
    forces while raised) is no longer tripped. This does not weaken
    T-1693's own "clears only on attribution, never on green" rule: a
    REAL attributed finding (any `disposition` other than the synthetic
    marker, or any finding this land path did not itself raise) is never
    eligible here, checked explicitly below -- only the coarse,
    self-raised timeout marker this SAME module created gets auto-
    dismissed once the specific condition that raised it has verifiably
    resolved. A no-op whenever nothing is quarantined, the store is
    unreadable, or any finding is not the synthetic marker."""
    from frob.verify._backpressure import current_status
    from frob.verify._quarantine import clear_quarantine, load_quarantine

    loaded = load_quarantine(root)
    if (
        loaded.is_err
        or loaded.danger_ok is None
        or loaded.danger_ok.cleared_at is not None
    ):
        return
    record = loaded.danger_ok
    if any(f.rule_id != "BACKPRESSURE_TIMEOUT" for f in record.findings):
        return

    status = current_status(root, ceilings)
    if status.is_err or status.danger_ok.tripped:
        return

    dispositions = {
        (f.rule_id, f.file, f.line): (
            "dismissed",
            "backpressure condition resolved -- watermark advanced past the "
            "timed-out batch (T-1693 auto-clear, synthetic finding only)",
        )
        for f in record.findings
    }
    cleared = clear_quarantine(
        root,
        dispositions=dispositions,
        reason="backpressure resolved -- synthetic BACKPRESSURE_TIMEOUT finding(s) "
        "only, no real attributed finding was ever recorded for this raise",
        actor="frob.app.ticket_runner._land_cmd._auto_clear_synthetic_quarantine",
    )
    if cleared.is_err:
        _log.error(
            "ticket land: auto-clear of a synthetic backpressure-timeout "
            "quarantine failed (%s)",
            cleared.danger_err,
        )


# frob:doc docs/modules/tickets.md#backpressure-t-1692
# frob:ticket T-1692
# frob:ticket T-1693
# frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_dry_run_skips_the_check  # noqa: E501
# frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_not_tripped_is_a_noop  # noqa: E501
# frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_tripped_blocks_then_proceeds  # noqa: E501
# frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_block_timeout_logs_and_proceeds  # noqa: E501
def _apply_backpressure(root: Path, cfg: AppConfig, profile) -> None:  # noqa: ANN001
    """T-1692: bound the unverified window before this land proceeds any
    further. Resolves `profile`'s ceilings (`frob.verify.
    ceilings_for_profile`) and, if the verify queue is currently past
    either ceiling, BLOCKS (`frob.verify.block_until_watermark_advances`)
    -- never refuses the land outright, per T-1692's own design: a refusal
    just makes the developer re-run the whole thing, a block pays back the
    deferred cost right here.

    Skipped entirely under `--dry-run`: a dry run previews what a land
    WOULD do without taking any real action, and blocking (which actively
    drains the queue as a side effect) is a real action -- see this
    function's own test, `test_dry_run_skips_the_check`.

    A block that times out (`BackpressureError.BlockTimedOut` -- a
    persistently red, quarantined batch) is logged at ERROR and the land
    PROCEEDS anyway rather than refusing: the backpressure axis exists to
    bound the deferred-verification WINDOW, not to become a second gate
    that can wedge every future land behind one unresolved batch forever.
    The error is already loud (this function's own log line plus every
    WARNING `block_until_watermark_advances` emitted while waiting) --
    that visibility is the safeguard, not an additional refusal on top of
    it."""
    if cfg.ticket_dry_run:
        return

    from frob.verify import ceilings_for_profile, block_until_watermark_advances

    ceilings = ceilings_for_profile(profile, root)
    _auto_clear_synthetic_quarantine(root, ceilings)
    ceilings = _quarantine_override_ceilings(root, ceilings, ticket_id=cfg.ticket_id)
    # T-1760: `cfg.ticket_id` is `str | None` on AppConfig, but backpressure
    # keys its own logging and watermark bookkeeping on a real ticket id.
    # A land without one has nothing to attribute the block to, so there is
    # nothing meaningful to bound -- skip rather than pass a placeholder,
    # which would make an unattributable block look like a real one.
    if cfg.ticket_id is None:
        _log.debug("ticket land: no ticket id, skipping the backpressure check")
        return
    blocked = block_until_watermark_advances(root, ceilings, cfg.ticket_id)
    if blocked.is_err:
        _log.error(
            "ticket land: %s backpressure block did not clear (%s) -- "
            "proceeding anyway; the batch is likely quarantined red and "
            "needs a human fix, see the WARNING lines above for depth/"
            "age/watermark",
            cfg.ticket_id,
            blocked.danger_err,
        )
        _raise_quarantine_on_persistent_block_timeout(root, cfg.ticket_id)


# frob:ticket T-1693
# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestRaiseQuarantineOnPersistentBlockTimeout.test_raises_with_a_synthetic_finding  # noqa: E501
# frob:tests tests/unit/test_land_cmd_quarantine.py::TestRaiseQuarantineOnPersistentBlockTimeout.test_already_quarantined_is_a_noop  # noqa: E501
def _raise_quarantine_on_persistent_block_timeout(
    root: Path, ticket_id: str | None
) -> None:
    """T-1693's own land-path raise site: a `block_until_watermark_
    advances` timeout means this land waited the ENTIRE backpressure
    timeout budget and the queue's ceiling never cleared -- the batch has
    been unable to go green for the whole window, a real (if coarser
    than T-1690's per-finding attribution) red-batch signal in its own
    right. Raises with a single UNATTRIBUTED `QuarantinedFinding`
    (`commit_sha`/`ticket_id` both `None` -- "cannot verify is never
    verified" extends to attribution too: this call site genuinely does
    not have per-finding attribution data, T-1690's `attribute_batch`
    output, only knows the WINDOW timed out, so it must not fabricate
    one).

    This is deliberately NOT the canonical raise call site the T-1693
    design describes (the batch-verification driver calling
    `raise_quarantine` directly off a red `attribute_batch` result,
    finding-by-finding) -- that driver
    (`src/frob/app/ticket_runner/_rapid_sweep.py`) was leased by a
    concurrent in-progress ticket for T-1693's entire working session
    and is out of its declared scope (disclosed in T-1693's Done report,
    follow-up filed as T-1791). This IS a real, independently
    correct trigger for the SAME breaker, not a placeholder -- a land
    that could not get past backpressure for the whole timeout window is
    exactly the situation deferred landing must stop happening for.

    A no-op if quarantine is already raised (idempotent, matching
    `raise_quarantine`'s own "overwrite, don't stack" contract) --
    checked here rather than relying on `raise_quarantine` itself, since
    re-raising with only this coarser synthetic finding would DISCARD a
    richer, already-recorded finding set from an earlier real batch
    raise."""
    from frob.verify._quarantine import (
        QuarantinedFinding,
        is_quarantined,
        raise_quarantine,
    )

    already = is_quarantined(root)
    if already.is_ok and already.danger_ok:
        _log.debug(
            "ticket land: %s quarantine already raised -- not overwriting "
            "with a coarser backpressure-timeout finding",
            ticket_id,
        )
        return

    raised = raise_quarantine(
        root,
        batch_commit_shas=(),
        findings=(
            QuarantinedFinding(
                rule_id="BACKPRESSURE_TIMEOUT",
                file=".",
                line=None,
            ),
        ),
    )
    if raised.is_err:
        _log.error(
            "ticket land: %s could not raise quarantine after a persistent "
            "backpressure timeout (%s)",
            ticket_id,
            raised.danger_err,
        )


# frob:ticket T-1593
def _land_core_start_baseline(  # noqa: ANN201
    root: Path, cfg: AppConfig, *, rapid_land: bool = False
):
    """Background-baseline seam of `_land_core` (T-1593 split): starts the
    T-1463 pre-land baseline capture thread, snapshot-isolated so it is
    safe to run concurrently with `land()`'s own merge/checks -- pure
    extraction of the original thread-start block, unchanged. Returns
    `(thread, holder)`; the caller joins `thread` and reads `holder[0]`
    once the `land()` call has returned.

    T-1684: `rapid_land` starts NO thread and returns a never-started
    stand-in (`join()` is a no-op, holder stays empty, so the caller's
    `pre_land_sha` is `None`). Rapid's post-land sweep is deferred to a
    detached child that diffs against its own rolling baseline
    (`frob.app.ticket_runner._rapid_sweep`), so this whole snapshot check
    -- a full `frob check` the land still had to JOIN before finishing --
    has no consumer under that profile. The baseline capture stays exactly
    as-is for `standard`/`fortress`."""
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller

    if rapid_land:
        import threading

        _log.info(
            "ticket land: %s profile=rapid -- skipping the T-1463 pre-land "
            "baseline snapshot check; the post-land sweep is deferred to a "
            "detached child with its own rolling baseline (T-1684)",
            cfg.ticket_id,
        )
        # Started (not merely constructed) so the caller's unconditional
        # `.join()` stays valid -- an unstarted Thread raises on join.
        noop = threading.Thread(
            target=lambda: None, name=f"frob-land-baseline-noop-{cfg.ticket_id}"
        )
        noop.start()
        return noop, []

    # T-1463: run concurrently with land()'s own merge/checks below -- see
    # `_capture_pre_land_baseline`'s docstring for why this is safe
    # (snapshot-isolated, not a read of root's live tree). T-1444: this is
    # still a PER-TICKET baseline capture even from inside `_land_drain`'s
    # loop -- sharing one baseline capture (and one post-drain sweep)
    # across a whole batch of N tickets is the "sublinear total
    # verification wall-clock" half of this ticket's acceptance criterion
    # and is disclosed as deferred follow-up work, not implemented here;
    # see the T-1444 Done report.
    import threading

    baseline_holder: list[tuple[str | None, frozenset[tuple[str, str]] | None]] = []
    baseline_thread = threading.Thread(
        target=lambda: baseline_holder.append(_capture_pre_land_baseline(root, cfg)),
        name=f"frob-land-baseline-{cfg.ticket_id}",
        daemon=True,
    )
    baseline_thread.start()
    return baseline_thread, baseline_holder


# frob:ticket T-1593
def _land_core_invoke(
    root: Path,
    cfg: AppConfig,
    worktree: Path,
    rapid_land: bool,
    baseline_thread,  # noqa: ANN001
    baseline_holder,  # noqa: ANN001
):  # noqa: ANN201
    """The actual `land()` call seam of `_land_core` (T-1593 split): wires
    every collaborator closure (T-0919 shared check spawn, T-1514
    pre-commit sweep, etc.) exactly as before -- pure extraction of the
    original `land(...)` call, unchanged."""
    from frob.tickets import land

    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller

    # T-0919: one shared spawn feeds BOTH check_gates/check_gate_findings
    # below instead of each running its own full `frob check --ticket`.
    _shared_spawn = _shared_check_spawn_fn(worktree, cfg.ticket_id)
    return land(
        root,
        cfg.ticket_id,
        worktree,
        dry_run=cfg.ticket_dry_run,
        collected=_land_collected_fn(worktree),
        passed=_land_passed_fn(worktree),
        covers_scope=_land_covers_scope_fn(worktree),
        bump_version=_land_bump_version_fn(),
        rebuild_natives=_land_rebuild_natives_fn(),
        sync_gate_rules=_land_sync_gate_rules_fn(),
        check_gates=_check_gates_summary_fn(
            worktree, cfg.ticket_id, spawn=_shared_spawn
        ),
        check_gate_findings=_check_gate_findings_fn(
            worktree, cfg.ticket_id, spawn=_shared_spawn
        ),
        check_gate_claims=_land_gate_claims_fn(worktree),
        skip_mutation_evidence=cfg.ticket_skip_mutation_evidence,
        allow_cross_ticket=cfg.ticket_allow_cross_ticket,
        pre_commit_sweep=(
            None
            if rapid_land
            else _land_pre_commit_sweep_fn(baseline_thread, baseline_holder, cfg)
        ),
    )


# frob:ticket T-1593
def _land_core_finish_post_land(
    root: Path,
    cfg: AppConfig,
    report,  # noqa: ANN001
    pre_land_sha: str | None,
    pre_land_findings: frozenset[tuple[str, str]] | None,
    *,
    rapid_land: bool = False,
):
    """T-1523 post-land verification seam of `_land_core` (T-1593 split):
    writes/clears the post-land-verify marker around the unscoped-error
    sweep and reports/returns the sweep's outcome -- pure extraction of
    the original trailing `if not report.dry_run and pre_land_sha is not
    None:` block, unchanged. Returns the same `Ok(report)`/`Err(...)`
    shape `_land_core` returned before the split (the caller passes its
    already-computed `result`/`report` through here unchanged on the
    skipped-sweep path)."""
    from frob.tickets._models import LandError

    assert cfg.ticket_id is not None  # narrows for the type checker; enforced by caller

    # T-1684: under rapid the sweep is the ONLY thing left between a
    # durable land commit and the developer's prompt, and it is a
    # multi-minute full-repo check. Hand it to a detached child and
    # return -- a red result becomes a filed bug ticket, never a revert of
    # a commit other agents may already have branched from.
    if rapid_land:
        if not report.dry_run and report.commit_sha is not None:
            from frob.app.ticket_runner._rapid_sweep import (
                spawn_deferred_post_land_sweep,
            )

            spawn_deferred_post_land_sweep(
                root, cfg.ticket_id, report.final_id, report.commit_sha
            )
        return Ok(report)

    if not report.dry_run and pre_land_sha is not None:
        # T-1523: the land commit (`report.commit_sha`) is ALREADY durably
        # on `root` at this point -- everything from here through the
        # sweep call below is the >540s-killable "post-land verification"
        # gap T-1495 point 4 named (the 2026-08-04 T-1464 incident's own
        # trigger). Marker written right before the sweep's own possible
        # `git reset --hard` (`_post_land_unscoped_error_sweep` ->
        # `_sweep_revert_land`), cleared right after -- a SIGTERM in
        # between leaves it for `_report_stale_post_land_verify_markers`
        # (called at the START of the NEXT `frob ticket land` invocation)
        # to surface instead of silently vanishing.
        from frob.tickets._land import (
            _clear_post_land_verify_marker,
            _write_post_land_verify_marker,
        )

        if report.commit_sha is not None:
            _write_post_land_verify_marker(root, cfg.ticket_id, report.commit_sha)
        swept = _post_land_unscoped_error_sweep(
            root, cfg.ticket_id, report.final_id, pre_land_sha, pre_land_findings
        )
        # Either outcome resolves the pending window: `swept=True` means
        # root is confirmed clean at `report.commit_sha`; `swept=False`
        # means the sweep already reverted root back to its pre-land tip
        # (nothing landed to verify anymore) -- neither leaves anything
        # for a later invocation to reconcile.
        _clear_post_land_verify_marker(root, cfg.ticket_id)
        if not swept:
            _log.error(
                "ticket land failed: %s post-land unscoped error sweep "
                "found residue no Tier-A auto-fix could resolve -- %s "
                "reverted to its pre-land state, land refused",
                report.final_id,
                root,
            )
            return Err(LandError.PostLandUnscopedSweepFailed)

    return Ok(report)


# frob:ticket T-1444
def _log_enqueue_failure(ticket_id: str, err: object) -> None:
    """`_land_enqueue`'s error-reporting branch, split out to keep that
    function's own decision-point count under ARCH103's threshold."""
    from frob.tickets import QueueError

    if err == QueueError.AlreadyQueued:
        _log.error(
            "ticket land --queue: %s already has a queued/landing entry "
            "-- inspect .frob/land-queue.json before re-enqueuing",
            ticket_id,
        )
    else:
        _log.error("ticket land --queue: %s failed to enqueue: %s", ticket_id, err)


# frob:ticket T-1444
def _queued_position(root: Path, ticket_id: str) -> str:
    """1-based position of `ticket_id`'s `queued` entry among every OTHER
    still-`queued` entry (FIFO order), or `"?"` if the queue file cannot
    be read -- split out of `_land_enqueue` for the same ARCH103 reason as
    `_log_enqueue_failure` above."""
    from frob.tickets import queue_status

    status = queue_status(root)
    if status.is_err:
        return "?"
    queued_ahead = [e for e in status.danger_ok if e.status == "queued"]
    for i, entry in enumerate(queued_ahead, start=1):
        if entry.ticket_id == ticket_id:
            return str(i)
    return "?"


# frob:ticket T-1444
def _land_enqueue(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> --queue`: enqueue instead
    of landing immediately -- appends a `queued` entry to
    `.frob/land-queue.json` (`frob.tickets._land_queue.enqueue`) and
    returns right away; a `--drain` invocation (`_land_drain`) processes
    it later, in FIFO order. Prints the assigned queue position
    (`_queued_position`) so the caller has some signal without having to
    poll `frob ticket land --queue-status`."""
    from frob.tickets import enqueue

    _require_land_args(cfg)
    assert cfg.ticket_id is not None
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    branch = worktree.name
    result = enqueue(root, cfg.ticket_id, worktree, branch)
    if result.is_err:
        _log_enqueue_failure(cfg.ticket_id, result.danger_err)
        sys.exit(1)

    _log.info(
        "ticket land --queue: %s enqueued (branch=%s), position %s -- "
        "run `frob ticket land --drain` to process the queue",
        cfg.ticket_id,
        branch,
        _queued_position(root, cfg.ticket_id),
    )


# frob:ticket T-1444
# frob:ticket T-1518
def _land_drain(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land --drain`: serially process every `queued` entry
    in `.frob/land-queue.json` via `frob.tickets._land_queue.drain_next`,
    calling `_land_core` (the SAME merge-check-splice-close-commit-sweep
    chain a direct `frob ticket land <id>` call runs) as its `land_fn`.
    Loops until the queue reports no more `queued` entries (`Ok(None)`)
    -- a single process, single invocation drain, not a long-running
    poll loop (see T-1444's own ticket body, design question 3: a
    long-running daemon needs its own lifecycle story and is deliberately
    NOT what this ships; a coordinator/scheduler calling `--drain`
    repeatedly is this increment's answer).

    Attribution: each entry's own `_print_land_proof` line (on success)
    or logged `LandError` (on failure) is printed as it resolves, so a
    caller reading this command's own log output can tell exactly which
    ticket landed and which was rejected back -- `drain_next`'s own
    policy (this module's docstring precedent, T-1345) never auto-retries
    a failed entry; it is dequeued and the loop moves to the next
    `queued` entry."""
    from frob.tickets import drain_next

    landed = 0
    failed = 0
    while True:

        def land_fn(entry):  # noqa: ANN001, ANN202
            per_entry_cfg = cfg.model_copy(
                update={
                    "ticket_id": entry.ticket_id,
                    "ticket_worktree": Path(entry.worktree),
                }
            )
            return _land_core(root, per_entry_cfg)

        outcome = drain_next(root, land_fn)
        if outcome.is_err:
            _log.error(
                "ticket land --drain: queue-level failure: %s", outcome.danger_err
            )
            sys.exit(1)
        entry = outcome.danger_ok
        if entry is None:
            break
        if entry.status == "landed" and entry.commit_sha is not None:
            landed += 1
            # T-1444: same LAND-PROOF contract a direct `frob ticket land
            # <id>` call prints -- report/finish (worktree removal) are
            # deliberately NOT run here, matching `--drain`'s own scope
            # (landing, not cleanup); a caller still runs `--finish`
            # per-ticket once it has verified the drain's own output.
            report = _LandReportShim(entry.commit_sha, entry.ticket_id)
            _print_land_proof(root, report)
            _log.info(
                "ticket land --drain: %s landed (commit=%s)",
                entry.ticket_id,
                entry.commit_sha,
            )
        else:
            failed += 1
            _log.warning(
                "ticket land --drain: %s failed to land (%s) -- rejected "
                "back, not retried; re-enqueue after fixing",
                entry.ticket_id,
                entry.error,
            )

    _log.info("ticket land --drain: done, %d landed, %d failed", landed, failed)
    _run_batch_mutation_sweep(root)


# frob:ticket T-1518
def _run_batch_mutation_sweep(root: Path) -> None:
    """T-1518's natural cadence point: after `--drain` finishes landing
    every queued entry, process any TEST016 mutation-evidence checks that
    `_land._check_mutation_evidence` deferred (every kind besides
    `security`, see `frob.tickets._mutation_sweep_queue`'s own docstring).
    A failure here is logged and swallowed, never raised -- this is a
    best-effort batch sweep riding along the merge-queue's own drain
    cadence, not a step the drain's own success/failure accounting
    depends on; a standalone `frob ticket land --run-mutation-sweep`
    invocation (e.g. a nightly cron) is the other sanctioned way to run
    it, for a deployment that never uses `--drain` at all."""
    from frob.tickets._mutation_sweep_queue import (
        pending_sweep_count,
        run_pending_sweep,
    )

    result = run_pending_sweep(root)
    if result.is_err:
        _log.warning(
            "ticket land --drain: batch mutation sweep failed: %s",
            result.danger_err,
        )
        return
    if result.danger_ok:
        _log.info(
            "ticket land --drain: batch mutation sweep processed %d "
            "deferred TEST016 entr%s",
            result.danger_ok,
            "y" if result.danger_ok == 1 else "ies",
        )
    remaining = pending_sweep_count(root)
    if remaining.is_ok and remaining.danger_ok:
        _log.warning(
            "ticket land --drain: %d entr%s still pending in the mutation "
            "sweep queue after this batch (likely enqueued mid-sweep) -- "
            "will be picked up next run",
            remaining.danger_ok,
            "y" if remaining.danger_ok == 1 else "ies",
        )


# frob:ticket T-1444
class _LandReportShim:
    """A minimal stand-in for `LandReport`'s two fields `_print_land_proof`
    actually reads (`commit_sha`, `final_id`) -- `drain_next`'s
    `QueueEntry` only carries `commit_sha` on a landed entry, not the full
    `LandReport` `land_fn` originally produced (the report itself is not
    threaded back through `drain_next`'s `QueueEntry`, by T-1345's own
    design: the queue's persisted record is a summary, not the full
    result object). Constructing this tiny shim is cheaper and less
    invasive than widening `QueueEntry`'s schema (outside this ticket's
    `src/frob/tickets/**`-adjacent-but-not-`_land_queue.py` scope) just to
    carry a report `_print_land_proof` only reads two fields of."""

    # frob:ticket T-1444
    def __init__(self, commit_sha: str | None, final_id: str) -> None:
        """Store the two fields `_print_land_proof` reads."""
        self.commit_sha = commit_sha
        self.final_id = final_id


# frob:ticket T-0631
# frob:waive ARCH103 reason="T-0977: push-after-successful-land helper -- runs `git \
# push`, logs the outcome, and decides whether a push failure should be fatal (see \
# docstring's dry-run/Err-path guard); the log+decide pair is the SAME single concern \
# (report the push result), not two"
def _push_after_land(root: Path, report) -> None:  # noqa: ANN001
    """`frob ticket land --push`: push `root`'s current branch to its
    upstream remote, but ONLY after a real (non-dry-run) land already
    fully succeeded -- `_land` calls this AFTER `land()` returned `Ok`,
    never on the `Err` exit path above, and never for `report.dry_run`
    (a dry run performs no durable commit to push, by design; pushing
    here would either push nothing new or push a stale prior state,
    neither of which honors "the push happens only after every land
    verification passed" for THIS run). Routed through
    `guarded_subprocess_run` (T-0778's exec guard, same as
    `_land_rebuild_natives_fn`'s `make core` spawn) so
    `FROB_DISABLE_EXEC=1` refuses this push too; a refusal or a non-zero
    `git push` exit is logged at ERROR and exits the process non-zero --
    the land itself already committed and closed the ticket by this
    point, so this failure is reported as a separate, later step rather
    than unwinding the land (there is nothing left to unwind: the
    landing commit already exists)."""
    if report.dry_run:
        _log.info(
            "ticket land --push: %s was a dry run -- nothing to push",
            report.ticket_id,
        )
        return

    from frob.gitio import current_branch

    branch = current_branch(root)
    if branch.is_err:
        _log.error(
            "ticket land --push: %s landed but could not determine "
            "root's current branch to push (%s)",
            report.ticket_id,
            branch.danger_err,
        )
        sys.exit(1)
    branch_name = branch.danger_ok

    from frob.app import ticket_runner as _ticket_runner

    guarded = _ticket_runner.guarded_subprocess_run(
        ["git", "-C", str(root), "push", "origin", branch_name],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if guarded.is_err:
        _log.error(
            "ticket land --push: %s landed (%s) but `git push` refused to "
            "spawn (%s) -- push it by hand: `git -C %s push origin %s`",
            report.ticket_id,
            report.commit_sha,
            ProcessGuardError.ExecDisabled,
            root,
            branch_name,
        )
        sys.exit(1)
    pushed = guarded.danger_ok
    if pushed.returncode != 0:
        _log.error(
            "ticket land --push: %s landed (%s) but `git push origin %s` "
            "exited %d -- stdout=%r stderr=%r -- push it by hand",
            report.ticket_id,
            report.commit_sha,
            branch_name,
            pushed.returncode,
            pushed.stdout[-2000:],
            pushed.stderr[-2000:],
        )
        sys.exit(1)
    _log.info(
        "ticket land --push: %s pushed %s to origin/%s",
        report.ticket_id,
        report.commit_sha,
        branch_name,
    )


# frob:ticket T-0323
def _require_merge_driver_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket merge-driver`'s
    three positional temp-file paths (%O/%A/%B, git's merge-driver
    protocol) are all present."""
    if (
        cfg.ticket_merge_base is None
        or cfg.ticket_merge_ours is None
        or cfg.ticket_merge_theirs is None
    ):
        _log.error(
            "frob ticket merge-driver requires %%O %%A %%B (base/ours/theirs "
            "temp file paths -- git supplies these when invoked as the "
            "registered merge driver, see .gitattributes / docs/modules/"
            "tickets.md#git-merge-driver)"
        )
        sys.exit(1)


# frob:ticket T-0323
def _merge_driver(root: Path, cfg: AppConfig) -> None:
    """`frob ticket merge-driver %O %A %B`: git's merge-driver entry point
    for `tickets.md` (docs/modules/tickets.md#git-merge-driver). Reads the
    `ours` (%A) and `theirs` (%B) temp files git hands it, splices them via
    the SAME `splice_ledger` `frob ticket land` uses (never a duplicate
    reimplementation), and overwrites `ours` in place with the result --
    the merge-driver protocol's contract: `ours`'s final content on disk
    IS the merge result git commits, regardless of exit status.

    T-1165 (T-1154 follow-up): `base` (%O) -- the true 3-way merge-base's
    ledger content, which git itself resolves and hands us as a ready-made
    temp file, no `git merge-base` shell-out needed the way `land`'s own
    internal `_true_merge_base` requires -- is now read and threaded
    through as `splice_ledger`'s `base_text` param, so a LIVE git merge
    through this driver gets the exact same wrong-side-merge tiebreak
    protection T-1154 gave `land`'s own internal splice call. Best-effort:
    a `base` file that is missing, unreadable, or fails to parse as a
    ledger degrades to `base_text=None` (the pre-T-1165 `_newer`-only
    tiebreak) rather than refusing the merge -- git always supplies %O for
    a registered 3-way merge driver, but a defensive read failure here
    must never turn a splice-able merge into a false conflict. Exits 0
    (git treats the auto-splice as a clean, non-conflicted merge) unless
    `ours`/`theirs` fail to parse as a ticket ledger, in which case it
    exits 1 and leaves `ours` untouched -- git then reports the usual
    conflict for a human to resolve by hand, exactly as if no driver were
    registered.

    T-1437: `archived_ids` is now resolved via `_archived_ids_for_merge_
    driver` (git-object reads of `HEAD`/`MERGE_HEAD`'s own committed
    `tickets-archive.md`), not a plain disk read of `root`'s current
    working-tree copy -- see that helper's docstring for the staleness
    defect this closes (a ticket archived on `main` after a worktree
    branched used to get resurrected into `tickets.md` on the worktree's
    next `git merge main`, because the disk read could never see the
    new archive content mid-merge)."""
    from frob.tickets import splice_ledger

    _require_merge_driver_args(cfg)
    assert cfg.ticket_merge_ours is not None  # narrows for the type checker
    assert cfg.ticket_merge_theirs is not None
    assert cfg.ticket_merge_base is not None
    ours_path, theirs_path = cfg.ticket_merge_ours, cfg.ticket_merge_theirs
    base_path = cfg.ticket_merge_base

    ours_text = ours_path.read_text(encoding="utf-8")
    theirs_text = theirs_path.read_text(encoding="utf-8")
    try:
        base_text: str | None = base_path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning(
            "ticket merge-driver: could not read base (%%O) file %s (%s) -- "
            "falling back to the pre-T-1165 _newer-only tiebreak",
            base_path,
            exc,
        )
        base_text = None

    spliced = splice_ledger(
        ours_text,
        theirs_text,
        archived_ids=_archived_ids_for_merge_driver(root),
        base_text=base_text,
    )
    if spliced.is_err:
        _log.error(
            "ticket merge-driver: splice_ledger failed (%s) -- leaving %s "
            "untouched for a manual conflict resolution",
            spliced.danger_err,
            ours_path,
        )
        sys.exit(1)

    ours_path.write_text(spliced.danger_ok, encoding="utf-8")
    _log.info(
        "ticket merge-driver: spliced %s (ours) + %s (theirs) -> %s",
        ours_path,
        theirs_path,
        ours_path,
    )

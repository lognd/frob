"""`frob ticket land` -- ledger merge/splice machinery.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land` (T-1186, following the verbatim-move
pattern `_evidence.py`/`_reporting.py` set at T-1171): the worktree/main
ledger-merge family (`splice_ledger`, per-ticket newest-wins resolution,
union-zone conflict-block resolution, out-of-scope conflict
auto-resolution, wip-commit staging) plus the small git-primitive
helpers (`_land_internal_git_env`, `_describe_git_failure`,
`_is_ignored_path_refusal`, `_rev_parse`, `_true_merge_base`) that both
this module and `_land_finalize` call into. Zero caller-visible behavior
change -- every moved function keeps its original body, docstring, and
`frob:ticket`/`frob:tests` directives verbatim; `frob.tickets._land`
re-exports the public surface (`splice_ledger`) via explicit import.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    LandError,
    Ticket,
    TicketError,
    TicketState,
    has_substantive_done_report,
    is_cmd_evidence,
    scope_matches,
    unbound_acceptance,
)
from frob.tickets._store import (
    _check_ledger_id_integrity,
    _parse_ledger,
    _render_ledger,
    archive_path,
    ledger_path,
)

_log = get_logger(__name__)


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


# frob:ticket T-0907
def _verified_reset_root(
    root: Path, pre_land_tip: str, ticket_id: str
) -> Result[None, LandError]:
    """Unwind `root`'s staged squash-apply back to `pre_land_tip` -- the
    T-0907 replacement for a bare `git reset --hard` (which resolves its
    target from whatever `HEAD` happens to be AT RESET TIME, the exact
    hazard the incident this ticket fixes exploited): resets to an
    EXPLICIT sha captured once at this run's start, and refuses loudly
    (`Err(GitFailed)`, no reset performed) if `root`'s current tip has
    already drifted from `pre_land_tip` by the time this runs -- root's
    tip must never move between this run's start and its own final commit
    (`_commit_squash_apply`), so any drift here means something else
    touched `root` mid-run and blindly resetting over it would risk
    exactly the T-0907 incident class."""
    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)
    if current.danger_ok != pre_land_tip:
        _log.error(
            "land: %s refused to unwind %s -- current tip is %s but this "
            "run's recorded pre-land tip is %s (drift detected mid-"
            "staging, T-0907) -- NOT resetting; inspect `git -C %s reflog` "
            "and `git -C %s log --oneline -5` by hand before retrying",
            ticket_id,
            root,
            current.danger_ok,
            pre_land_tip,
            root,
            root,
        )
        return Err(LandError.GitFailed)
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", pre_land_tip])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:doc docs/modules/tickets.md#frob-ticket-land
# frob:waive COV007 reason="T-1024: the land ordering rule this table is genuinely \
# documented at the public frob:doc anchor (frob ticket land's own section) -- no \
# separate public caller worth re-anchoring onto, same disposition as this module's \
# other private-table waivers"
_STATE_RANK: dict[TicketState, int] = {
    TicketState.QUEUED: 0,
    TicketState.PLANNED: 1,
    TicketState.IN_PROGRESS: 2,
    TicketState.BLOCKED: 2,
    TicketState.DROPPED: 3,
    TicketState.DONE: 3,
}


def _has_done_report(body: str) -> bool:
    """Whether `body` has a substantive '## Done report' section (D-03):
    thin wrapper delegating to the single shared implementation in
    `frob.tickets._models` -- dedupes the twin copy `tickets/__init__.py`
    used to carry (D-11)."""
    return has_substantive_done_report(body)


_TERMINAL_RANK = 3  # rank shared by TicketState.DONE and TicketState.DROPPED


# frob:ticket T-0682
# frob:invariant INV-043 establishes="_newer's qualified richness preference: among two non-terminal same-id ticket sides, the richer (Done-report/evidence/acceptance) side wins UNLESS the poorer side strictly outranks it by state -- a strictly-higher-rank poorer side always wins regardless of richness"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_report_side_still_wins_when_it_also_outranks_the_reportless_side  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_neither_side_reporting_still_falls_back_to_state_rank  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState.test_landing_tickets_in_progress_report_survives_the_merge_stage  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_terminal_side_always_wins_over_non_terminal kind="property"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_strictly_higher_rank_poorer_side_always_wins kind="property"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_richer_side_wins_at_equal_or_lower_rank kind="property"  # noqa: E501
def _newer(a: Ticket, b: Ticket) -> Ticket:
    """Which of two same-id ticket versions is "newer" (T-0682: Done-report
    presence now qualifies state-rank whenever NEITHER side has already
    reached a terminal state -- but does not blanket-override it).

    Three tiers, checked in order:

    1. TERMINAL SUPREMACY (unchanged from before T-0682): if either side is
       `done`/`dropped` (rank 3) and the other is not, the terminal side
       always wins, Done report or not -- a ticket main has already closed
       or dropped must never be resurrected to a lesser state just because
       a stale worktree copy happens to carry Done-report text (T-0537's
       regression lock; also the T-0479-adjacent race where main
       independently drops a ticket a worktree is still mid-flight on --
       `close` must still fail against the terminal state, not silently
       resurrect the worktree's in-progress copy).
    2. Otherwise, if Done-report presence DIFFERS between the two
       non-terminal sides, the reported side wins ONLY IF the reportless
       side does not STRICTLY outrank it. A substantive Done report is
       strong evidence of real, committed-to-land progress -- stronger
       than the bare `state:` field, which a stale copy can carry at an
       EQUAL or LOWER rank than a richer one for free (`queued`/`planned`/
       `in-progress` are all trivially reachable by hand-editing or a
       requeue) -- but it is not proof against a genuinely more-advanced
       rework on the OTHER side: a reviewer-caught inverse of the T-0682
       field incident found that an unqualified "report always wins" rule
       let a STALE report on a lower-rank block (e.g. a ticket requeued
       back down without ever stripping its old report body) beat a
       reportless side that had since made real further progress at a
       strictly higher rank. So: reportless-but-strictly-higher-rank wins
       over reported-but-lower-or-equal-rank; reported wins over
       reportless in every other differing-presence case (equal rank, or
       reported side itself at the higher rank). This still closes the
       original T-0682 incident (the reported side there was ALSO the
       higher-rank side -- in-progress+report vs main's bare queued --
       so it wins either way) while no longer resurrecting a stale report
       over genuine forward progress.
    3. Otherwise (Done-report presence is a wash -- both sides carry one,
       or neither does), fall back to the plain state-rank comparison,
       tie-broken by `b` (the incoming/theirs side) as the final
       deterministic pick -- never a coin flip.

    Either way, the winner's evidence AND acceptance bindings are UNIONED
    with the loser's (`_union_evidence`/`_union_acceptance`, D-09/T-0764)
    rather than the loser's side being silently dropped -- the old
    `len(a.evidence) != len(b.evidence)` tiebreak used to pick ONE side's
    evidence set wholesale, discarding the other side's ids entirely when
    two worktrees closed the same ticket with disjoint evidence.

    T-0764: step 2's Done-report-presence check generalized to a full
    RICHNESS score (`_richness`: Done-report presence, then evidence
    count, then bound-acceptance count, checked in that priority order) --
    the original T-0753 field incident was an IN-PROGRESS ticket with a
    `start`+evidence+bound-acceptance already recorded but NO Done report
    yet, tied in state-rank with main's bare `in-progress` (no evidence at
    all). Neither side differed on Done-report presence, so this used to
    fall straight through to the old step 3's arbitrary `b`-wins tiebreak
    -- which happened to discard the richer, evidence-bearing side. Using
    the same richness tuple for BOTH steps closes that gap while leaving
    every existing Done-report-differs case decided exactly as before,
    since Done-report presence is still the tuple's first (highest-
    priority) component."""
    winner = _newer_winner(a, b)
    return _union_acceptance(_union_evidence(winner, a, b), a, b)


# frob:ticket T-0976
def _newer_winner(a: Ticket, b: Ticket) -> Ticket:
    """`_newer`'s own three-tier winner selection (its docstring's tiers
    1-3), before the evidence/acceptance union that always follows --
    split out so `_newer` itself only owns that final union."""
    rank_a, rank_b = _STATE_RANK[a.state], _STATE_RANK[b.state]
    if _TERMINAL_RANK in (rank_a, rank_b) and rank_a != rank_b:
        return a if rank_a > rank_b else b
    richness_a, richness_b = _richness(a), _richness(b)
    if richness_a == richness_b:
        return b if rank_a == rank_b else (a if rank_a > rank_b else b)
    richer, richer_rank = (a, rank_a) if richness_a > richness_b else (b, rank_b)
    poorer, poorer_rank = (b, rank_b) if richness_a > richness_b else (a, rank_a)
    return poorer if poorer_rank > richer_rank else richer


def _richness(t: Ticket) -> tuple[int, int, int]:
    """T-0764: `(has_done_report, evidence_count, bound_acceptance_count)`
    -- the tiebreak signal `_newer` uses to prefer whichever same-id,
    same-terminality side carries more real recorded progress. Compared as
    a plain tuple, so Done-report presence dominates (matches the
    pre-T-0764 priority exactly), evidence count breaks a Done-report tie,
    and bound-acceptance count breaks an evidence-count tie."""
    bound_acceptance = sum(1 for c in t.acceptance if c.evidence)
    return (1 if _has_done_report(t.body) else 0, len(t.evidence), bound_acceptance)


def _union_evidence(winner: Ticket, a: Ticket, b: Ticket) -> Ticket:
    """D-09: never let a splice silently drop one side's evidence -- return
    `winner` with its evidence extended (deduplicated, winner's own ids
    first) by any id the OTHER of `a`/`b` carries that `winner` lacks."""
    if a.evidence == b.evidence:
        return winner
    other = b if winner is a else a
    merged = list(winner.evidence)
    merged.extend(e for e in other.evidence if e not in merged)
    if tuple(merged) == winner.evidence:
        return winner
    _log.info(
        "tickets: land splice -- unioned evidence for %s (%d -> %d id(s))",
        winner.id,
        len(winner.evidence),
        len(merged),
    )
    return winner.model_copy(update={"evidence": tuple(merged)})


# frob:ticket T-0764
def _union_acceptance(winner: Ticket, a: Ticket, b: Ticket) -> Ticket:
    """Never let a splice silently drop one side's acceptance BINDING: for
    each criterion `winner` carries, if the OTHER side has a same-text
    criterion with an evidence id `winner`'s copy lacks, extend `winner`'s
    binding with it (deduplicated, winner's own ids first) -- the
    acceptance-side twin of `_union_evidence` (D-09), closing the T-0764
    gap where `winner` could be the side whose criterion was never bound
    even though the loser's copy of the SAME criterion text already was.
    A criterion whose text does not appear on the other side at all (a
    genuinely new/edited criterion) is left untouched."""
    if a.acceptance == b.acceptance:
        return winner
    other = b if winner is a else a
    other_by_text = {c.text: c for c in other.acceptance}
    changed = False
    merged_criteria = []
    for criterion in winner.acceptance:
        other_criterion = other_by_text.get(criterion.text)
        if other_criterion is None or not other_criterion.evidence:
            merged_criteria.append(criterion)
            continue
        extra = [e for e in other_criterion.evidence if e not in criterion.evidence]
        if not extra:
            merged_criteria.append(criterion)
            continue
        changed = True
        merged_criteria.append(
            criterion.model_copy(
                update={"evidence": tuple(list(criterion.evidence) + extra)}
            )
        )
    if not changed:
        return winner
    _log.info(
        "tickets: land splice -- unioned acceptance binding(s) for %s",
        winner.id,
    )
    return winner.model_copy(update={"acceptance": tuple(merged_criteria)})


# frob:doc docs/modules/tickets.md#frob-ticket-land
# `archived_ids` (from main's `tickets-archive.md`, the only authoritative
# archive) is excluded from the merged result unconditionally, from
# EITHER side -- without this, a ticket main already archived reappears
# in the active ledger the moment a stale branch (whose own tickets.md
# still carries it as active, from before it was archived) lands,
# resurrecting exactly the active/archive duplicate-id class a human
# would otherwise have to hand-resolve at merge time (reviewer-caught,
# T-0176).
# frob:ticket T-0601
def splice_ledger(
    ours_text: str,
    theirs_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    base_text: str | None = None,
) -> Result[str, TicketError]:
    """Merge two `tickets.md` ledger texts at the ticket-id level, keeping the
    newest state per section (`_newer`) instead of trusting git's line-level
    textual merge -- the fix for the "both sides append a new ticket near
    the same line" false-conflict class (T-0176), and the tiebreak for a
    genuine same-id divergence (e.g. one side closed a ticket the other
    side is still mid-editing).

    T-1154: `base_text` (the true 3-way merge-base's ledger text, when the
    caller has one -- e.g. `git merge-base`'s tickets.md) sharpens that
    same-id tiebreak: a side unchanged since `base_text` never wins over a
    side that made a real edit, closing the wrong-side-merge class
    documented on `_merge_ledger_tickets`/`_resolve_divergence`. Optional
    and unparseable/`None` degrades to the pre-T-1154 `_newer`-only
    behavior, never a hard failure.

    T-0764: after the merge, refuses loudly (`Err(LedgerIntegrityViolation)`)
    if any id present on EITHER side vanished from the result without being
    an intentional `archived_ids` drop, or if the rendered text does not
    round-trip every surviving id back out with its marker intact
    (`_check_ledger_id_integrity`, the same guard `write_all`/`write_archive`
    run) -- the structural backstop for the T-0367 markerless-block
    incident class at the one place a git-merge-driver-triggered splice
    could otherwise commit a silent loss with no caller ever checking."""
    ours_parsed = _parse_ledger(ours_text)
    if ours_parsed.is_err:
        return Err(ours_parsed.danger_err)
    theirs_parsed = _parse_ledger(theirs_text)
    if theirs_parsed.is_err:
        return Err(theirs_parsed.danger_err)
    ours, theirs = ours_parsed.danger_ok, theirs_parsed.danger_ok
    base = None
    if base_text is not None:
        base_parsed = _parse_ledger(base_text)
        base = base_parsed.danger_ok if base_parsed.is_ok else None

    merged = _merge_ledger_tickets(ours, theirs, base=base)
    _drop_resurrected_ids(merged, archived_ids)
    _log.info(
        "tickets: land splice -- ours=%d theirs=%d merged=%d",
        len(ours),
        len(theirs),
        len(merged),
    )
    expected_ids = (set(ours) | set(theirs)) - archived_ids
    unintended_loss = expected_ids - set(merged)
    if unintended_loss:
        _log.error(
            "tickets: land splice refused -- id(s) %s vanished from the "
            "merge without being an intentional archive-resurrection drop "
            "(T-0764)",
            sorted(unintended_loss),
        )
        return Err(TicketError.LedgerIntegrityViolation)
    rendered = _render_ledger(merged)
    integrity = _check_ledger_id_integrity(merged, rendered)
    if integrity.is_err:
        return Err(integrity.danger_err)
    return Ok(rendered)


def _merge_ledger_tickets(
    ours: dict[str, Ticket],
    theirs: dict[str, Ticket],
    *,
    base: dict[str, Ticket] | None = None,
) -> dict[str, Ticket]:
    """Union `ours`/`theirs` by ticket id, keeping the newer state
    (`_newer`) on any id present in both with a genuine divergence.

    T-1154: when `base` (the true 3-way merge-base ledger, e.g. `git
    merge-base`'s tickets.md/tickets-archive.md content) is given, a
    same-id divergence is resolved by CHANGE-vs-BASE first, before ever
    falling back to `_newer`'s richness/rank tiebreak: whichever side is
    BYTE-IDENTICAL to `base[ticket_id]` made no deliberate edit at all and
    has no claim on the id, so the side that DID change wins outright. This
    is the fix for the wrong-side-merge corruption class (3rd occurrence,
    see this ticket's own Done report): `_newer`'s tier-3 fallback ties on
    same-rank/same-richness by construction (an unrelated content edit like
    an evidence-path migration inside an already-`done` Done report changes
    neither state nor evidence count) and then arbitrarily prefers `b`
    (`theirs`) -- which used to let a worktree's untouched, merely-STALE
    copy of a ticket main had since edited win the tie and revert main's
    edit. Only when BOTH sides differ from `base` (a genuine divergence,
    each side made its own edit) does this fall through to `_newer`
    unchanged, exactly as before `base` existed. A `ticket_id` absent from
    `base` (new on both sides, or `base` itself unavailable/unparseable)
    also falls straight through to the pre-T-1154 `_newer` behavior."""
    merged: dict[str, Ticket] = dict(ours)
    for ticket_id, ticket in theirs.items():
        if ticket_id not in merged:
            merged[ticket_id] = ticket
        elif merged[ticket_id] != ticket:
            merged[ticket_id] = _resolve_divergence(
                merged[ticket_id], ticket, base.get(ticket_id) if base else None
            )
    return merged


# frob:ticket T-1154
def _resolve_divergence(ours: Ticket, theirs: Ticket, base: Ticket | None) -> Ticket:
    """T-1154: single-id conflict resolution used by `_merge_ledger_tickets`
    -- prefer whichever of `ours`/`theirs` actually changed since `base`
    (the true 3-way merge-base state for this id); fall back to `_newer`
    when `base` is unavailable, or when both sides changed (a genuine
    divergence `_newer`'s richness/rank tiebreak is the right tool for)."""
    if base is not None:
        ours_changed, theirs_changed = ours != base, theirs != base
        if ours_changed and not theirs_changed:
            return ours
        if theirs_changed and not ours_changed:
            return theirs
    return _newer(ours, theirs)


def _drop_resurrected_ids(
    merged: dict[str, Ticket], archived_ids: frozenset[str]
) -> None:
    """Delete from `merged`, in place, any id already present in
    `archived_ids` (see `splice_ledger`'s resurrection-prevention doc)."""
    resurrected = archived_ids & set(merged)
    for ticket_id in resurrected:
        del merged[ticket_id]
    if resurrected:
        _log.info(
            "tickets: land splice -- dropped %d already-archived id(s): %s",
            len(resurrected),
            sorted(resurrected),
        )


# frob:ticket T-0577
def _preserve_sibling_done_reports(
    merged: dict[str, Ticket], worktree_tickets: dict[str, Ticket], landed_id: str
) -> None:
    """After `_splice_only_ticket` overlays ONLY `landed_id` from the
    worktree, every OTHER (sibling) ticket id comes from `main_tickets`
    untouched -- correct for the T-0479/T-0475 resurrection class (a
    worktree's stale, requeued-on-main sibling must never win), but it has
    a real cost: in a multi-ticket worktree, a sibling that is ALSO done
    (in-progress with a substantive Done report already written, awaiting
    its own `frob ticket land`) has that Done report silently discarded the
    moment ANY ticket in the same worktree lands first, because main's copy
    of that sibling is still a bare `queued`/`planned` block from before
    the worktree ever touched it (real incident: landing T-0386 erased
    T-0387/T-0388's Done reports and regressed them to queued).

    This closes that gap without reopening T-0479: for each sibling id
    present in `merged` (from main) that also exists in `worktree_tickets`,
    keep the WORKTREE's copy in place of main's ONLY when main's side has
    no substantive Done report yet worktree's does -- richer state
    (a Done report) always wins over a bare state block, but a genuine
    main-side requeue (main's side already carries no Done report AND the
    worktree's side is merely a stale advanced state with no Done report
    either, the T-0479 case) is untouched, since neither side satisfies
    the swap condition and main's existing entry is left as-is."""
    for ticket_id, ticket in worktree_tickets.items():
        if ticket_id == landed_id or ticket_id not in merged:
            continue
        main_side = merged[ticket_id]
        if main_side == ticket:
            continue
        main_has_done = _has_done_report(main_side.body)
        worktree_has_done = _has_done_report(ticket.body)
        if worktree_has_done and not main_has_done:
            _log.info(
                "tickets: land splice -- preserved %s's Done report from "
                "worktree (main's copy had none) while landing %s",
                ticket_id,
                landed_id,
            )
            merged[ticket_id] = _union_evidence(ticket, main_side, ticket)


# frob:ticket T-0637
# frob:tests tests/test_ticket_land.py::TestStandaloneSiblingDraftSurvivesLand.test_sibling_draft_ticket_finalized_and_lands_alongside  # noqa: E501
def _carry_forward_new_worktree_tickets(
    merged: dict[str, Ticket], worktree_tickets: dict[str, Ticket], landed_id: str
) -> None:
    """Carry over any ticket id present ONLY in `worktree_tickets` -- never
    yet on main/`merged`'s base -- that is not `landed_id` itself.

    `_splice_only_ticket`'s T-0479 scoping deliberately never lets a
    worktree's STALE view of an ALREADY-ON-MAIN ticket win (that is the
    sibling-resurrection class it closes) -- but a ticket main has never
    seen at all carries no stale state to protect against, so silently
    dropping it is pure data loss with no matching safety benefit. This was
    the T-0637 field incident: a standalone sibling draft ticket
    (`frob ticket new` filed mid-session off the default branch, T-0162)
    present only in the worktree's ledger vanished the moment ANY ticket
    from that worktree landed, because neither this overlay (before this
    fix) nor `_preserve_sibling_done_reports` (which only ever touches ids
    `merged` already has) ever considered an id absent from BOTH main and
    the overlay target. Skips `landed_id` (the caller's own overlay already
    handles it) and anything `merged` already has an entry for (that path
    is `_preserve_sibling_done_reports`'s job, not this one's)."""
    for ticket_id, ticket in worktree_tickets.items():
        if ticket_id == landed_id or ticket_id in merged:
            continue
        merged[ticket_id] = ticket
        _log.info(
            "tickets: land splice -- carried forward new sibling ticket %s "
            "(not previously on main) while landing %s",
            ticket_id,
            landed_id,
        )


# frob:ticket T-1179
def _overlay_landed_ticket(
    merged: dict[str, Ticket], ticket_id: str, incoming: Ticket
) -> Result[None, TicketError]:
    """`_splice_only_ticket`'s own id overlay, split out to keep both under
    the ARCH001 line budget: write `incoming` into `merged[ticket_id]`,
    resolving a genuine divergence via `_newer` -- unless main's CURRENT
    block under this id has a DIFFERENT title than `incoming` (T-1179
    acceptance [1], defense in depth alongside the id-ceiling fix in
    `finalize_draft_for_land`): two unrelated tickets collided on one id,
    not a genuine same-ticket state divergence `_newer` should arbitrate,
    so this refuses loudly instead of silently picking a winner and
    discarding the other ticket's content wholesale (the 2026-07-29
    incident: 46a115c4 clobbered by 17c6ca89)."""
    if ticket_id not in merged or merged[ticket_id] == incoming:
        merged[ticket_id] = incoming
        return Ok(None)
    existing = merged[ticket_id]
    if existing.title != incoming.title:
        _log.error(
            "tickets: land splice refused -- %s exists on main as %r but "
            "this land is finalizing a DIFFERENT ticket %r under the same "
            "id (T-1179 id/title-mismatch guard)",
            ticket_id,
            existing.title,
            incoming.title,
        )
        return Err(TicketError.IdTitleMismatch)
    merged[ticket_id] = _newer(existing, incoming)
    return Ok(None)


# frob:ticket T-0479
def _splice_only_ticket(
    main_text: str,
    worktree_text: str,
    ticket_id: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
) -> Result[str, TicketError]:
    """Merge `tickets.md` by taking MAIN's ledger as the base and overlaying
    ONLY `ticket_id`'s own block from `worktree_text` (T-0479): every other
    ticket id comes from `main_text` untouched. `splice_ledger`'s original
    whole-ledger, keep-newest-per-id merge let a worktree's stale view of a
    SIBLING ticket (in-progress in the worktree from before that sibling was
    later requeued back to queued on main) win the `_newer` state-rank
    comparison and resurrect the stale state on main (T-0475) -- state-rank
    assumes forward-only progress and cannot tell a genuine advance from a
    requeue's backward transition. Scoping the overlay to just the one
    ticket actually being landed makes that whole class of resurrection
    structurally impossible: a sibling ticket's ledger entry is never even
    considered here, no matter what the worktree's copy says. If `ticket_id`
    is present in both with a genuine divergence, `_newer` still resolves
    the winner (and unions evidence) for that one id, exactly as before.
    A `ticket_id` that exists only in `worktree_text` (not yet in
    `main_text`, e.g. a fresh/draft ticket) is still applied -- `land`
    lands one ticket per call, and this is that ticket's own first entry
    onto main."""
    main_parsed = _parse_ledger(main_text)
    if main_parsed.is_err:
        return Err(main_parsed.danger_err)
    worktree_parsed = _parse_ledger(worktree_text)
    if worktree_parsed.is_err:
        return Err(worktree_parsed.danger_err)
    main_tickets, worktree_tickets = main_parsed.danger_ok, worktree_parsed.danger_ok

    merged = dict(main_tickets)
    incoming = worktree_tickets.get(ticket_id)
    if incoming is not None:
        overlaid = _overlay_landed_ticket(merged, ticket_id, incoming)
        if overlaid.is_err:
            return Err(overlaid.danger_err)
    _preserve_sibling_done_reports(merged, worktree_tickets, ticket_id)
    _carry_forward_new_worktree_tickets(merged, worktree_tickets, ticket_id)
    _drop_resurrected_ids(merged, archived_ids)
    _log.info(
        "tickets: land splice (ticket-scoped) -- %s only, main=%d ticket(s), merged=%d",
        ticket_id,
        len(main_tickets),
        len(merged),
    )
    rendered = _render_ledger(merged)
    # frob:ticket T-0740
    # T-0740: this scoped splice was the one wholesale-ledger-commit site
    # that did NOT run the T-0764 `_check_ledger_id_integrity` backstop
    # (`splice_ledger` and `write_all`/`write_archive` all do). By
    # construction `_render_ledger` cannot itself drop a marker today, so
    # this was not a live reproduction of the T-0367 incident -- but it was
    # a real defense-in-depth gap: `frob ticket land`'s per-ticket path is
    # the MOST common land shape (T-0479 scoping) and previously had no
    # backstop at all if a future refactor of `_render_ledger`/
    # `_render_section` ever regressed. Closing it here so every wholesale
    # ledger-write path shares the same guard.
    integrity = _check_ledger_id_integrity(merged, rendered)
    if integrity.is_err:
        return Err(integrity.danger_err)
    return Ok(rendered)


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


# frob:ticket T-1002
class _UnionZone:
    """One registered append-only merge zone (T-1002): a file glob plus how
    to union two sides' concurrent appends inside it instead of leaving a
    real git conflict. `kind="keyed_lines"` unions per-key chunks (each
    chunk is zero or more leading comment/blank lines followed by exactly
    one line matching `key_regex`) between `marker_start`/`marker_end`
    (docs/audits/coordination-churn.md item 3's `[gates.severity]` and
    `_KNOWN_GATE_RULES` hotspots); `kind="append_only"` treats the whole
    conflicted region as two blocks of pure appended text with no per-line
    key at all (the `docs/audits/*.md` remediation-log hotspot). Both kinds
    refuse (return `None`) rather than guess whenever the two sides
    genuinely disagree about the same key's value -- a true contradiction,
    not a concurrent append, and left for manual resolution same as before
    this ticket."""

    __slots__ = ("glob", "kind", "key_regex", "marker_start", "marker_end")

    def __init__(
        self,
        glob: str,
        kind: str,
        *,
        key_regex: re.Pattern[str] | None = None,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        """Register one union zone; see the class docstring for the field
        semantics."""
        self.glob = glob
        self.kind = kind
        self.key_regex = key_regex
        self.marker_start = marker_start
        self.marker_end = marker_end


# frob:ticket T-1002
# The three chronic conflict hotspots from docs/audits/coordination-churn.md
# item 3 (~8 occurrences, always resolved keep-both-chronological by hand
# before this ticket). Each source file carries `# frob-zone-start
# <name> T-1002` / `# frob-zone-end <name> T-1002` marker comments
# delimiting the exact region this registry is allowed to touch.
_UNION_ZONES: tuple[_UnionZone, ...] = (
    _UnionZone(
        "frob.toml",
        "keyed_lines",
        key_regex=re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*="),
        marker_start="# frob-zone-start gates.severity T-1002",
        marker_end="# frob-zone-end gates.severity T-1002",
    ),
    _UnionZone(
        "src/frob/gates/__init__.py",
        "keyed_lines",
        key_regex=re.compile(r'^\s*"(?P<key>[A-Za-z0-9_-]+)",\s*$'),
        marker_start="# frob-zone-start known-gate-rules T-1002",
        marker_end="# frob-zone-end known-gate-rules T-1002",
    ),
    _UnionZone("docs/audits/*.md", "append_only"),
)


def _zone_for_path(path: str) -> _UnionZone | None:
    """The registered `_UnionZone` matching `path`, or `None` if `path` is
    not a union zone at all (T-1002)."""
    for zone in _UNION_ZONES:
        if fnmatch.fnmatch(path, zone.glob):
            return zone
    return None


_CONFLICT_BLOCK_RE = re.compile(
    r"<<<<<<< [^\n]*\n"
    r"(?P<ours>.*?)"
    r"(?:\|\|\|\|\|\|\| [^\n]*\n.*?)?"
    r"=======\n"
    r"(?P<theirs>.*?)"
    r">>>>>>> [^\n]*\n",
    re.DOTALL,
)


def _chunk_by_key(
    text: str, key_regex: re.Pattern[str]
) -> list[tuple[str | None, str]]:
    """Split `text` into `(key, chunk_text)` pairs for `_union_keyed_chunks`
    (T-1002): each chunk is the run of lines up to and including the next
    line matching `key_regex` (so leading comments stay attached to the
    entry they annotate); any trailing lines with no further key match form
    one final `(None, ...)` chunk."""
    lines = text.splitlines(keepends=True)
    chunks: list[tuple[str | None, str]] = []
    buf: list[str] = []
    for line in lines:
        buf.append(line)
        m = key_regex.match(line)
        if m:
            chunks.append((m.group("key"), "".join(buf)))
            buf = []
    if buf:
        chunks.append((None, "".join(buf)))
    return chunks


# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_composes  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_refuses  # noqa: E501
def _union_keyed_chunks(
    ours_text: str, theirs_text: str, key_regex: re.Pattern[str]
) -> str | None:
    """Union-merge two sides of a keyed-lines conflict block (T-1002):
    every key present on either side survives, in ours'-then-theirs'-new-
    only order; a key present on BOTH sides with differing chunk text is a
    true contradiction, not a concurrent append, and this returns `None`
    (refuse) rather than pick a side silently."""
    ours_chunks = _chunk_by_key(ours_text, key_regex)
    theirs_chunks = _chunk_by_key(theirs_text, key_regex)
    ours_by_key = {k: text for k, text in ours_chunks if k is not None}
    seen = set(ours_by_key)
    merged = [text for _, text in ours_chunks]
    theirs_only: list[str] = []
    for key, text in theirs_chunks:
        if key is None:
            continue
        if key in seen:
            if text.strip() != ours_by_key[key].strip():
                return None
            continue
        theirs_only.append(text)
        seen.add(key)
    return "".join(merged) + "".join(theirs_only)


def _union_append_only(ours_text: str, theirs_text: str) -> str:
    """Union-merge two sides of an append-only conflict block (T-1002): pure
    concatenation (ours' new content, then theirs') since there is no
    per-line key to reconcile by -- both sides only ever append whole
    sections (e.g. a `## Remediation log (...)` block). Identical sides
    (a no-op re-append) collapse to one copy."""
    if ours_text.strip() == theirs_text.strip():
        return ours_text
    return ours_text.rstrip("\n") + "\n\n" + theirs_text.lstrip("\n")


def _resolve_conflict_blocks(raw_text: str, zone: _UnionZone) -> str | None:
    """Resolve every `<<<<<<<`/`=======`/`>>>>>>>` conflict block in
    `raw_text` via `zone`'s union strategy, or `None` if any block is a true
    contradiction (`_union_keyed_chunks` refused) or (for a marker-delimited
    zone) any block falls outside the `marker_start`/`marker_end` region --
    a conflict there is not this zone's business to silently resolve, and
    the caller leaves the file conflicted exactly as before T-1002."""
    if zone.marker_start is not None:
        start = raw_text.find(zone.marker_start)
        end = raw_text.find(zone.marker_end or "")
        if start == -1 or end == -1 or end < start:
            return None
        zone_end = end + len(zone.marker_end or "")
        for m in _CONFLICT_BLOCK_RE.finditer(raw_text):
            if not (start <= m.start() and m.end() <= zone_end):
                return None

    def _resolve_one(m: re.Match[str]) -> str | None:
        ours, theirs = m.group("ours"), m.group("theirs")
        if zone.kind == "keyed_lines":
            assert zone.key_regex is not None
            return _union_keyed_chunks(ours, theirs, zone.key_regex)
        return _union_append_only(ours, theirs)

    out: list[str] = []
    cursor = 0
    for m in _CONFLICT_BLOCK_RE.finditer(raw_text):
        resolved = _resolve_one(m)
        if resolved is None:
            return None
        out.append(raw_text[cursor : m.start()])
        out.append(resolved)
        cursor = m.end()
    out.append(raw_text[cursor:])
    return "".join(out)


# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_resolve_stages  # noqa: E501
def _resolve_union_zone_conflicts(
    cwd: Path, conflicted: set[str]
) -> Result[frozenset[str], LandError]:
    """After a merge/squash leaves `conflicted` paths unmerged in `cwd`,
    resolve every one that matches a registered `_UNION_ZONE` via its union
    strategy and `git add` the result; returns whatever is STILL conflicted
    (union zones that refused a true contradiction, or were left alone
    because they are not a registered zone at all) for the caller to treat
    exactly as before T-1002 (fall through to the existing out-of-scope
    auto-resolve / hard-abort path)."""
    still_conflicted: set[str] = set()
    for path in sorted(conflicted):
        zone = _zone_for_path(path)
        if zone is None:
            still_conflicted.add(path)
            continue
        full_path = cwd / path
        if not full_path.exists():
            still_conflicted.add(path)
            continue
        raw_text = full_path.read_text(encoding="utf-8")
        resolved = _resolve_conflict_blocks(raw_text, zone)
        if resolved is None:
            _log.warning(
                "land: union-zone merge for %s left a true contradiction "
                "(or a conflict outside its registered marker region) -- "
                "leaving it conflicted for manual resolution",
                path,
            )
            still_conflicted.add(path)
            continue
        full_path.write_text(resolved, encoding="utf-8")
        add = run_argv(["git", "-C", str(cwd), "add", "--", path])
        if add.is_err or add.danger_ok.returncode != 0:
            still_conflicted.add(path)
            continue
        _log.info(
            "land: union-zone merge composed concurrent appends in %s "
            "(zone=%s) with no manual resolution",
            path,
            zone.glob,
        )
    return Ok(frozenset(still_conflicted))


def _deletion_glob_too_broad(glob: str) -> bool:
    """Whether a scope glob is too broad to trust for authorizing a
    DELETION (D-12): a bare top-level directory (`src/`, expanded to
    `src/**`) or the whole-tree `.`/`*` pattern. `scope_matches`'s
    ordinary dir-glob expansion (T-0241) is correct for the general
    "is this file in scope" question, but a ticket scoped only to a
    single top-level directory silently authorizes deleting ANYTHING
    under it -- exactly the stale-base incident class this filter exists
    to catch. A more specific glob (`src/frob/`, `src/frob/tickets/**`)
    is still trusted."""
    stripped = glob.removesuffix("/**").removesuffix("/*").rstrip("/")
    if stripped in ("", ".", "*"):
        return True
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


def _validate_closeable(ticket: Ticket) -> Result[None, LandError]:
    """The evidence + Done-report + acceptance-binding preconditions
    `transition(..., DONE)` will enforce anyway -- checked here FIRST,
    before any git mutation, so a landing never merges main (and commits a
    merge/finalize commit) into the worktree only to discover at close time
    that it must be unwound (the exact ordering hazard T-0176 exists to
    close, and T-0763's own closeability-preflight-before-merge fix: every
    close precondition that is knowable from the PRE-merge ticket alone --
    evidence present, Done report present, evidence-kind consistency
    (T-0215), and now unbound acceptance criteria (T-0572) -- is checked
    here, before `_land_merge_stage` ever runs `git merge`. `EvidenceScopeUnbound`
    is checked separately, by `_land_precheck`'s own
    `_validate_scope_covered_preflight` call (T-0774), not inside this
    function: it needs the injected `covers_scope` callable (`frob.gates`'s
    job, which `frob.tickets` cannot import -- docs/rework.md cycle-
    avoidance), which this function does not receive. That preflight is a
    PRE-merge simulation against the worktree's current tree, closing the
    residual fail-after-merge class this docstring used to describe as
    permanent; `_land_finalize_and_close` still re-checks `covers_scope`
    unconditionally against the actual POST-merge tree as the authoritative
    check. Also re-checks the T-0215 kind-consistency rule (`_transition_guard`'s
    DONE-path twin): a non-docs-kind ticket carrying any `cmd:` evidence
    entry -- kind hand-edited after the entry was recorded, or the entry
    hand-pasted directly into the ledger -- must never land, mirroring the
    write-time gate in `add_cmd_evidence`."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.error(
            "land: %s cannot land -- missing evidence or a Done report; "
            "record evidence (`frob ticket evidence %s <node-id>...`, or for "
            "a docs-kind ticket `frob ticket close %s --evidence-cmd "
            "'<command>'`) and add a '## Done report' section under %s's "
            "entry in tickets.md, then retry `frob ticket land %s`",
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    kind_check = _validate_evidence_kind_consistency(ticket)
    if kind_check.is_err:
        return kind_check
    return _validate_acceptance_bound(ticket)


def _validate_acceptance_bound(ticket: Ticket) -> Result[None, LandError]:
    """`Err(NotCloseable)`, naming the specific unbound criterion/criteria,
    if `ticket` carries any acceptance criterion with no resolving evidence
    id (T-0572's `unbound_acceptance`, mirrored here pre-merge so a landing
    never merges/finalizes only to fail this same check at close time --
    T-0763). A ticket with no acceptance criteria declared is unaffected,
    matching `unbound_acceptance`'s own T-0572 backward-compat rule."""
    unbound = unbound_acceptance(ticket)
    if unbound:
        _log.error(
            "land: %s cannot land -- unbound acceptance criterion/criteria "
            "(no evidence id resolves them): %s; bind evidence to the "
            "criterion (`frob ticket evidence %s <node-id>... "
            "--accepts <index>`, 0-based) and retry `frob ticket land %s`",
            ticket.id,
            [c.text for c in unbound],
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


# frob:waive DUP001 reason="T-1186 split-induced false positive: the DUP001 template \
# similarity heuristic matches this guard-clause shape (early-return Result validation \
# over a small enum-kind check) against several unrelated validators across the repo \
# (invariants.py, _elaborate.py, _scope.py, _evidence.py) purely on control-flow \
# resemblance -- none share this function's domain (cmd-evidence-kind-vs-ticket-kind \
# closeability); this function moved verbatim from frob.tickets._land (pre-existing, \
# unwaived there because the pre-move DUP scan never paired it against these \
# particular unrelated files) as part of T-1186's _land.py split"
def _validate_evidence_kind_consistency(ticket: Ticket) -> Result[None, LandError]:
    """`Err(NotCloseable)` if `ticket`'s kind disallows cmd: evidence but it
    carries some anyway (see `_validate_closeable`'s T-0215 doc)."""
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.error(
            "land: %s cannot land -- kind=%s carries cmd: evidence, only "
            "allowed for kind in %s; fix the ticket's kind or replace the "
            "cmd: entry with real pytest --evidence node ids, then retry "
            "`frob ticket land %s`",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


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


def _splice_and_stage(
    checkout: Path,
    pre_text: str,
    incoming_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    ticket_id: str | None = None,
) -> Result[str, LandError]:
    """Write the ledger splice of `pre_text`/`incoming_text` to `checkout`'s
    tickets.md and `git add` it; overrides whatever git's own textual merge
    produced -- tickets.md is ALWAYS resolved via a splice, never via git's
    line-level algorithm, so a both-sides-append never false-conflicts and a
    same-id divergence always keeps the newest state (T-0176).

    `ticket_id`, when given, scopes the splice to ONLY that ticket's own
    block via `_splice_only_ticket` (T-0479) -- every other id comes from
    `pre_text` untouched, so a worktree's stale sibling-ticket state can
    never overlay main's newer one. `ticket_id=None` (the default) keeps the
    original whole-ledger `splice_ledger` merge, used only where BOTH sides
    are pulling in each other's full set of tickets on purpose (there is no
    "one ticket being landed" to scope to). `archived_ids` excludes anything
    main has already archived from ever re-entering the merged active
    ledger, either way."""
    if ticket_id is not None:
        spliced = _splice_only_ticket(
            pre_text, incoming_text, ticket_id, archived_ids=archived_ids
        )
    else:
        spliced = splice_ledger(pre_text, incoming_text, archived_ids=archived_ids)
    if spliced.is_err:
        _log.error(
            "land: tickets.md splice failed (%s) -- resolve manually in %s",
            spliced.danger_err,
            checkout,
        )
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
    class this closes. tickets.md's own splice (`_splice_and_stage`) does
    not need this: `ticket_id`-scoping (T-0479) already makes every sibling
    id come from `main_text` untouched, so the archive file -- whose splice
    is NOT scoped to one id -- is the one exposed to this class."""
    pre_text = _read_ledger_text_or_empty(worktree)
    main_text = _read_ledger_text_or_empty(root)
    # frob:ticket T-0959
    pre_archive_text = _read_archive_text_or_empty(worktree)
    main_archive_text = _read_archive_text_or_empty(root)
    # frob:ticket T-1154
    base_sha = _true_merge_base(worktree, main_branch)
    base_archive_text = (
        _read_text_at_ref(worktree, base_sha.danger_ok, "tickets-archive.md")
        if base_sha.is_ok
        else None
    )

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
    # sibling ticket's state come from main untouched, unconditionally --
    # only the ticket actually being landed is ever taken from the
    # worktree.
    spliced = _splice_and_stage(
        worktree,
        main_text,
        pre_text,
        archived_ids=_archived_ids(root),
        ticket_id=ticket.id,
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


_KIND_TO_COMMIT_TYPE = {
    "feature": "feat",
    "bug": "fix",
    "security": "fix",
    "ux": "fix",
    "docs": "docs",
    "invariant": "test",
    "incident": "fix",
}


def _commit_message(ticket: Ticket, final_id: str) -> str:
    """Conventional-commit message for the landing commit (ASCII, no
    trailing period, no Co-Authored-By -- repo convention)."""
    commit_type = _KIND_TO_COMMIT_TYPE.get(ticket.kind.value, "chore")
    subject = f"{commit_type}(tickets): land {final_id} {ticket.title}"
    return subject[:120]


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

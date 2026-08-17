"""`frob ticket land` -- ledger-merge/newest-wins family.

See docs/modules/tickets-landing.md#frob-ticket-land.

Split out of `frob.tickets._land_merge` (T-1194, continuing the one-family-
per-land discipline T-1186/T-1187/T-1188/T-1189/T-1192 established): the
per-ticket-id newest-wins ledger merge machinery (`splice_ledger`,
`_merge_ledger_tickets`, `_resolve_divergence`, `_newer`/`_newer_winner`/
`_richness`, `_union_evidence`/`_union_acceptance`, `_drop_resurrected_ids`,
`_preserve_sibling_done_reports`, `_carry_forward_new_worktree_tickets`,
`_overlay_landed_ticket`, `_splice_only_ticket`). Zero caller-visible
behavior change -- every moved function keeps its original body, docstring,
and `frob:ticket`/`frob:tests` directives verbatim; `frob.tickets._land_merge`
imports `splice_ledger`/`_splice_only_ticket`/`_merge_ledger_tickets` back for
its own `_splice_and_stage`/`_splice_and_stage_archive` use, and
`frob.tickets._land` continues to re-export `splice_ledger` unchanged via
`frob.tickets._land_merge`.
"""

from __future__ import annotations

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import (
    Ticket,
    TicketError,
    TicketState,
    has_substantive_done_report,
)
from frob.tickets._store import (
    _check_ledger_id_integrity,
    _parse_ledger,
    _render_ledger,
)

_log = get_logger(__name__)

# frob:doc docs/modules/tickets-landing.md#frob-ticket-land
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


# frob:doc docs/modules/tickets-landing.md#frob-ticket-land
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


# frob:ticket T-1721
# frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_worktree_only_edit_is_carried_forward  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_main_only_edit_is_left_alone  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_the_same_way_converges_silently  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_differently_refuses  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_no_base_available_falls_back_to_done_report_heuristic  # noqa: E501
def _carry_forward_or_refuse_sibling_edits(
    merged: dict[str, Ticket],
    worktree_tickets: dict[str, Ticket],
    landed_id: str,
    base_tickets: dict[str, Ticket] | None,
) -> Result[None, TicketError]:
    """T-1721: `_splice_only_ticket`'s general sibling-edit rule, replacing
    `_preserve_sibling_done_reports`'s narrower Done-report-only special
    case with a full base-aware 3-way comparison, when a `base_tickets`
    snapshot (the true merge-base's ledger, T-1154's `_true_merge_base` +
    `_read_text_at_ref`) is available.

    For each sibling id (not `landed_id`) present in both `merged` (from
    main) and `worktree_tickets`, compare all three of main's current
    copy, the worktree's copy, and the common base's copy:

    - worktree unchanged since base: main's copy stands (the ordinary
      T-0479 case -- nothing to carry).
    - worktree changed, main unchanged since base: the worktree made a
      real, isolated edit main never touched -- safe to carry forward.
      This is the T-1637 shape this ticket exists to fix: an evidence
      rebind on an unrelated DONE sibling, made mid-another-ticket's-work,
      previously silently dropped by T-0479's blanket main-wins default.
    - both sides changed but converged to the same content: nothing to do,
      already resolved.
    - both sides changed to DIFFERENT content: neither side is stale --
      both made a real, independent edit since the same base. This is the
      case `_newer`'s old richness heuristic could not actually answer
      (T-0682/T-0764's tiebreak compares state-rank and Done-report/
      evidence/acceptance richness, never raw content, so a same-rank,
      same-richness divergence was resolved by an arbitrary positional
      tiebreak that silently discarded whichever side lost). Per the
      T-1721 finding: silently choosing is the bug, not which side it
      chooses -- refused instead (`Err(SiblingLedgerEditConflict)`),
      naming the id, so an operator resolves the real conflict by hand
      instead of a land quietly deciding it for them.

    `base_tickets=None` (git could not resolve the true merge-base, or its
    ledger text failed to parse) degrades to the pre-T-1721
    `_preserve_sibling_done_reports` heuristic -- never a hard failure
    just because the sharper comparison was unavailable this once."""
    if base_tickets is None:
        _preserve_sibling_done_reports(merged, worktree_tickets, landed_id)
        return Ok(None)
    for ticket_id, worktree_ticket in worktree_tickets.items():
        if ticket_id == landed_id or ticket_id not in merged:
            continue
        main_ticket = merged[ticket_id]
        if main_ticket == worktree_ticket:
            continue
        resolved = _resolve_one_sibling_edit(
            merged, ticket_id, main_ticket, worktree_ticket, base_tickets, landed_id
        )
        if resolved.is_err:
            return resolved
    return Ok(None)


# frob:ticket T-1721
def _resolve_one_sibling_edit(
    merged: dict[str, Ticket],
    ticket_id: str,
    main_ticket: Ticket,
    worktree_ticket: Ticket,
    base_tickets: dict[str, Ticket],
    landed_id: str,
) -> Result[None, TicketError]:
    """`_carry_forward_or_refuse_sibling_edits`'s own per-id 3-way decision
    (ARCH001 split): mutates `merged[ticket_id]` in place when the
    worktree's edit should be carried forward, returns
    `Err(SiblingLedgerEditConflict)` on a genuine both-sides divergence,
    `Ok(None)` otherwise (including every "nothing to do" case) -- see the
    caller's own docstring for the full decision table this implements."""
    base_ticket = base_tickets.get(ticket_id)
    if base_ticket is None:
        # No base-era record for this id (e.g. finalized from a draft
        # since the fork point) -- the 3-way comparison has nothing to
        # compare against; fall back to the narrow Done-report rule for
        # this one id, same posture as the no-base-at-all case.
        if _has_done_report(worktree_ticket.body) and not _has_done_report(
            main_ticket.body
        ):
            merged[ticket_id] = _union_evidence(
                worktree_ticket, main_ticket, worktree_ticket
            )
        return Ok(None)
    worktree_changed = worktree_ticket != base_ticket
    main_changed = main_ticket != base_ticket
    if not worktree_changed:
        return Ok(None)
    if not main_changed:
        _log.info(
            "tickets: land splice -- carried forward %s's edit from "
            "the worktree (main unchanged since the common base) "
            "while landing %s",
            ticket_id,
            landed_id,
        )
        merged[ticket_id] = worktree_ticket
        return Ok(None)
    _log.error(
        "tickets: land splice refused -- %s was independently edited "
        "on both main and the worktree since their common base, in "
        "ways that do not converge (T-1721) -- resolve %s by hand "
        "(or land it on its own first), then retry landing %s",
        ticket_id,
        ticket_id,
        landed_id,
    )
    return Err(TicketError.SiblingLedgerEditConflict)


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
    incident: 46a115c4 clobbered by 17c6ca89).

    T-2220: `land_commit` is carried forward from whichever side has it if
    `_newer`'s winner would otherwise drop it -- the exact same "never
    silently discard a richer side's data" principle `_newer` already
    applies to evidence/acceptance (D-09/T-0764), extended to this field.
    Without this, a RETRY of the same worktree (T-1001's own no-op-
    absorption path) always picks the worktree's own committed copy as
    the tie-break winner (`_newer`'s step 3, `b` wins on a full tie) --
    but the worktree's copy was committed BEFORE `_record_land_commit`
    (`frob.tickets._land_squash`) ever wrote this field onto main, so it
    never carries it, and a naive overlay would silently erase main's
    already-recorded land_commit on every subsequent retry/sibling land
    in the same worktree."""
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
    winner = _newer(existing, incoming)
    if winner.land_commit is None and existing.land_commit is not None:
        winner = winner.model_copy(update={"land_commit": existing.land_commit})
    merged[ticket_id] = winner
    return Ok(None)


# frob:ticket T-1721
_SpliceOnlySides = tuple[
    dict[str, Ticket], dict[str, Ticket], "dict[str, Ticket] | None"
]


# frob:ticket T-1721
def _parse_splice_only_sides(
    main_text: str, worktree_text: str, base_text: str | None
) -> Result[_SpliceOnlySides, TicketError]:
    """`_splice_only_ticket`'s own parse-every-side prelude (ARCH001
    split): parses `main_text`/`worktree_text` (either failure is a hard
    `Err`, exactly as before) and best-effort parses `base_text` (a
    failure there degrades to `None`, never a hard error -- the 3-way
    comparison is a sharpening of the existing splice, not a new hard
    requirement, matching `base_text`'s own docstring contract)."""
    main_parsed = _parse_ledger(main_text)
    if main_parsed.is_err:
        return Err(main_parsed.danger_err)
    worktree_parsed = _parse_ledger(worktree_text)
    if worktree_parsed.is_err:
        return Err(worktree_parsed.danger_err)
    base_tickets = None
    if base_text is not None:
        base_parsed = _parse_ledger(base_text)
        base_tickets = base_parsed.danger_ok if base_parsed.is_ok else None
    return Ok((main_parsed.danger_ok, worktree_parsed.danger_ok, base_tickets))


# frob:ticket T-0479
# frob:ticket T-1721
def _splice_only_ticket(
    main_text: str,
    worktree_text: str,
    ticket_id: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    base_text: str | None = None,
) -> Result[str, TicketError]:
    """Merge `tickets.md` by taking MAIN's ledger as the base and overlaying
    ONLY `ticket_id`'s own block from `worktree_text` (T-0479): every other
    ticket id comes from `main_text` untouched BY DEFAULT. `splice_ledger`'s
    original whole-ledger, keep-newest-per-id merge let a worktree's stale
    view of a SIBLING ticket (in-progress in the worktree from before that
    sibling was later requeued back to queued on main) win the `_newer`
    state-rank comparison and resurrect the stale state on main (T-0475) --
    state-rank assumes forward-only progress and cannot tell a genuine
    advance from a requeue's backward transition. Scoping the overlay to
    just the one ticket actually being landed makes that whole class of
    resurrection structurally impossible: a sibling ticket's ledger entry is
    never even considered for OVERWRITE here, no matter what the worktree's
    copy says. If `ticket_id` is present in both with a genuine divergence,
    `_newer` still resolves the winner (and unions evidence) for that one
    id, exactly as before. A `ticket_id` that exists only in `worktree_text`
    (not yet in `main_text`, e.g. a fresh/draft ticket) is still applied --
    `land` lands one ticket per call, and this is that ticket's own first
    entry onto main.

    T-1721: `base_text` (the true merge-base's ledger text, when the caller
    has one -- `_true_merge_base` + `_read_text_at_ref`, mirroring T-1154's
    identical pattern for the archive splice) sharpens what happens to
    SIBLING ids beyond T-0479's blanket "main wins" default:
    `_carry_forward_or_refuse_sibling_edits` carries forward a sibling edit
    the worktree made that main never touched since the same base (the
    T-1637 field incident this exists to fix -- a legitimate cross-ticket
    ledger correction, silently dropped before this fix, no matter which
    ticket's land carried it), and REFUSES loudly
    (`Err(SiblingLedgerEditConflict)`) rather than silently picking a side
    when both main and the worktree independently edited the same sibling
    id to DIFFERENT content since that base. `base_text=None` (the default)
    degrades to the pre-T-1721 `_preserve_sibling_done_reports` heuristic,
    never a hard requirement."""

    parsed_sides = _parse_splice_only_sides(main_text, worktree_text, base_text)
    if parsed_sides.is_err:
        return Err(parsed_sides.danger_err)
    main_tickets, worktree_tickets, base_tickets = parsed_sides.danger_ok

    merged = dict(main_tickets)
    incoming = worktree_tickets.get(ticket_id)
    if incoming is not None:
        overlaid = _overlay_landed_ticket(merged, ticket_id, incoming)
        if overlaid.is_err:
            return Err(overlaid.danger_err)
    sibling_result = _carry_forward_or_refuse_sibling_edits(
        merged, worktree_tickets, ticket_id, base_tickets
    )
    if sibling_result.is_err:
        return Err(sibling_result.danger_err)
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

"""frob.tickets._evidence -- the evidence/transition family (T-1152,
T-1123/T-1108/T-1103 residue): the state-machine transition guard chain
(`transition`, `reverify_close_guard`, the `_done_transition_*` guard
family), pytest-node-id evidence (`add_evidence`), non-pytest command
evidence (`run_cmd_evidence`/`add_cmd_evidence`/`reverify_cmd_evidence`),
Done-report evidence rendering/recovery (`render_evidence_block`,
`replay_evidence_from_done_report`), and the git-diff-derived Done-report
helpers (`base_ref_resolvable`, `compute_changed_lines`,
`render_changed_block`) -- split out of `frob.tickets.__init__` following
T-1103's per-family extraction pattern (verbatim moves, directives intact,
public surface re-exported via explicit imports, zero caller-visible
behavior change).

Kept together because every one of these functions ultimately feeds or
guards the same DONE-transition decision: evidence is recorded here,
verified here, and the guard chain that decides whether a ticket may close
on it lives here too -- one cohesive "can this ticket legally close, and
what proves it" concern.

`_OPEN_STATES`, `_TRANSITIONS`, `_load_ticket_and_queue`, `_load_one`,
`validate_evidence`, and `_validate_evidence_list` intentionally STAY in
`frob.tickets.__init__` (all six are shared by several non-evidence
families still there -- `mutate_labels`, `add_acceptance`, `new_ticket`,
the done-report/review/drop/attach family not yet extracted) -- this
module late-imports every one of them from the package at call time
rather than at load time, the same load-order-safe indirection
`_setters.py`/`_scope.py` use for `_load_ticket_and_queue`, since
`__init__` imports THIS module before any of the six exist yet at its own
module scope.
"""
# frob:waive ARCH102 reason="the naming/usage clustering heuristic groups these 26 \
# exports into 4 clusters by surface-level name prefix and direct call edges \
# (transition/reverify_*/guard-shaped names vs evidence/cmd_evidence-shaped names vs \
# render_*/compute_*/base_ref_resolvable Done-report helpers vs replay_evidence_ \
# from_done_report's own recovery path); the module docstring above already names the \
# real cohesion -- every one of these functions feeds or guards the SAME DONE- \
# transition decision (evidence recorded here, verified here, guard chain that decides \
# closability lives here) -- coupled by the shared TicketQueue/Ticket state machine \
# this family exists to enforce, not by call-graph adjacency alone; same T-1103/T-1108 \
# precedent as frob.tickets.__init__'s own ARCH102 waiver for the identical reason \
# (one deliberately centralized concern, not several bolted together)"
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_evidence.py's exclusivity-vocabulary hits are source-level \
# design-rationale prose (docstrings describing already-implemented internal behavior, \
# verifiable by reading the code they annotate) rather than a separate cross-module \
# contract needing its own tracked invariant; disposed as a calibration batch, not \
# claim-by-claim -- module prose carried verbatim from frob.tickets.__init__ (T-1152 \
# split, same INV006-on-split-modules precedent as 0abc4e3a/T-1151)"

from __future__ import annotations

import hashlib
import re
import shlex
import subprocess
from collections.abc import Sequence
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.tickets._live_tracker import live_tracker_citations
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    TicketTier,
    _done_report_section_lines,
    has_substantive_done_report,
    is_cmd_evidence,
    matches_collected,
    unbound_acceptance,
)
from frob.tickets._new_gate_rule_acceptance import (
    missing_acceptance_for_new_rules,
    new_gate_rule_ids,
)
from frob.tickets._store import ledger_lock
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)


def _has_done_report(body: str) -> bool:
    """Whether `body` has a substantive '## Done report' section (D-03):
    thin wrapper kept for call-site stability, delegating to
    `frob.tickets._models.has_substantive_done_report` (the single
    heading-plus-content implementation, dedupe of D-11's twin)."""
    return has_substantive_done_report(body)


def _start_blockers(ticket: Ticket, queue: dict[str, Ticket]) -> list[str]:
    """Blocker ids of `ticket` that are unknown or still in an open state."""
    from frob.tickets import _OPEN_STATES

    return [
        b for b in ticket.blocked_by if b not in queue or queue[b].state in _OPEN_STATES
    ]


# frob:ticket T-0417
# frob:ticket T-1384
def _transition_guard(
    root: Path,
    ticket: Ticket,
    to: TicketState,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
    own_obligations_clean: bool | None = None,
) -> Result[None, TicketError]:
    """Enforce start-blocker and done-evidence preconditions for `to`."""
    if to == TicketState.IN_PROGRESS:
        open_ids = _start_blockers(ticket, queue)
        if open_ids:
            _log.warning(
                "tickets: %s cannot start, open blockers %s", ticket.id, open_ids
            )
            return Err(TicketError.BlockerOpen)
    if to == TicketState.DONE:
        return _done_transition_guard(
            root,
            ticket,
            queue,
            covers_scope=covers_scope,
            reviewed=reviewed,
            mutation_evidence=mutation_evidence,
            evidence_reverified=evidence_reverified,
            own_obligations_clean=own_obligations_clean,
        )
    return Ok(None)


# frob:ticket T-0715
def _open_descendant_ids(ticket: Ticket, queue: dict[str, Ticket]) -> tuple[str, ...]:
    """Ids of every descendant of `ticket` (via the `parent` chain, any
    depth) whose state is not done/dropped -- the T-0715 structural rule an
    EPIC/STORY's DONE transition enforces: it cannot close while any
    descendant is still open. Mirrors `epic_rollup`'s own parent-chain BFS
    (kept separate: that one builds a full rollup for display, this is a
    cheap open/closed check for a single guard)."""
    from frob.tickets import _OPEN_STATES

    children_of: dict[str, list[Ticket]] = {}
    for t in queue.values():
        if t.parent is not None:
            children_of.setdefault(t.parent, []).append(t)
    open_ids: list[str] = []
    frontier = [ticket.id]
    seen = {ticket.id}
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, ()):
            if child.id in seen:
                continue
            seen.add(child.id)
            if child.state in _OPEN_STATES:
                open_ids.append(child.id)
            frontier.append(child.id)
    return tuple(sorted(open_ids))


# T-0215 review round 2: a cmd: entry is only ever valid evidence on a
# docs-kind ticket (COV003 mirrors this at check time). Re-check HERE too,
# not just at add_cmd_evidence write time -- a ticket's kind can be
# hand-edited after evidence was recorded, or a cmd: entry can be
# hand-pasted directly into the ledger, either of which would otherwise
# slip a code-kind ticket through close on unverifiable evidence.
# frob:ticket T-0417
# frob:ticket T-0976
def _done_transition_structural_guard(
    ticket: Ticket, queue: dict[str, Ticket], *, covers_scope: bool | None
) -> Result[None, TicketError]:
    """`_done_transition_guard`'s structural (non-diff-derived) checks:
    evidence + Done report present, open descendants, disallowed cmd:
    evidence, injected `covers_scope`, and unbound acceptance criteria --
    split from its review/mutation/reverify/diff-derived checks."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.warning(
            "tickets: %s cannot close, missing evidence or a substantive Done report",
            ticket.id,
        )
        return Err(TicketError.MissingEvidence)
    if ticket.tier is not TicketTier.TICKET:
        open_descendants = _open_descendant_ids(ticket, queue)
        if open_descendants:
            _log.warning(
                "tickets: %s (tier=%s) cannot close, open descendant(s): %s",
                ticket.id,
                ticket.tier,
                open_descendants,
            )
            return Err(TicketError.OpenDescendant)
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.warning(
            "tickets: %s is kind=%s but carries cmd: evidence, only "
            "allowed for kind in %s",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
        )
        return Err(TicketError.EvidenceKindNotAllowed)
    if covers_scope is False:
        _log.warning(
            "tickets: %s cannot close, no evidence id covers a touched/scope symbol",
            ticket.id,
        )
        return Err(TicketError.EvidenceScopeUnbound)
    unbound = unbound_acceptance(ticket)
    if unbound:
        _log.warning(
            "tickets: %s cannot close, unbound acceptance criterion/criteria: %s",
            ticket.id,
            [c.text for c in unbound],
        )
        return Err(TicketError.AcceptanceUnbound)
    return Ok(None)


# frob:ticket T-1384
def _done_transition_guard(
    root: Path,
    ticket: Ticket,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
    own_obligations_clean: bool | None = None,
) -> Result[None, TicketError]:
    """Enforce DONE-transition preconditions: evidence + substantive Done
    report present, no cmd: evidence on a kind that disallows it, (T-0715)
    an EPIC/STORY refuses to close while any descendant (via the `parent`
    chain) is still open, (D-02,
    when the caller supplies `covers_scope`) at least one evidence id binds
    to a touched/scope symbol, (T-0572) every declared acceptance criterion
    has at least one resolving evidence id -- see `unbound_acceptance` (a
    ticket with an empty `acceptance` list is unaffected, T-0572 backward
    compat) -- (T-0571, when the caller supplies `reviewed`) at least
    one approve-verdict review record naming the current commit, (T-0844,
    when the caller supplies `mutation_evidence=False`) that the ticket
    does not carry an unwaived ERROR-severity TEST016 confirmatory-only-
    evidence finding, mirroring `frob.tickets._land._check_mutation_
    evidence`'s land-time refusal so a security/bug ticket closed directly
    (never landed) is not exempt from the same obligation, (T-0417 N-02,
    when the caller supplies `evidence_reverified=False`) that a fresh
    re-run of the ticket's own non-cmd evidence ids against the CURRENT
    tree still passes -- closing must never trust a stale record-time
    "passed" observation the way `land`'s own `_reverify_evidence_post_
    merge` already refuses to for the merge path (D-05); this is the
    direct-close twin of that same obligation, and (T-0854,
    ALWAYS, not injected) that no registry disposition or waiver still
    cites `ticket.id` as its live tracker (`frob.tickets._live_tracker.
    live_tracker_citations`) -- the T-0605-orphaned-41-rows incident class.

    (T-1384, when the caller supplies `own_obligations_clean=False`) that
    the ticket's OWN diff leaves no new-symbol `frob:doc` edge, testsuite
    declaration, or REL001 bump outstanding -- see `TicketError.
    OwnObligationsUnclean`'s docstring for the incident this closes
    (T-1377/T-1379/T-1381 all closed clean and left exactly this residue
    for the very next unscoped `frob check` to surprise-discover).

    `covers_scope`/`reviewed`/`mutation_evidence`/`evidence_reverified`/
    `own_obligations_clean` are injected, never computed here: answering
    "does an evidence id cover a touched/scope symbol" needs the obligation
    graph (`frob.graph`) and the `TESTS`-edge index `frob.testing`/
    `frob.gates` already build, answering "is there an approve review
    naming HEAD" needs `git rev-parse` under the caller's root, answering
    "did the bound evidence kill a mutant" needs `frob.gates.mutation_
    evidence_violations`, answering "does the evidence still pass right
    now" needs a real test-runner spawn, and answering "does this diff's
    own new-symbol doc/testsuite/REL001 obligations resolve" needs the
    same `frob.gates` COV001/SELFAUDIT/REL machinery `frob check` itself
    runs -- `frob.tickets` deliberately stays free of all five
    dependencies (docs/rework.md cycle-avoidance -- `frob.gates`/
    `frob.app` are the layers allowed to join graph/runner + tickets).
    `None` (the default, matching every caller before D-02/T-0571/T-0844/
    T-0417/T-1384) skips each check entirely, so existing callers/tests
    are unaffected; a caller with the needed context (`frob.gates.
    evidence_covers_scope`, `has_approved_review_for_commit`, `frob.gates.
    mutation_evidence_violations`, `frob.app.ticket_runner._reverify_
    evidence_for_close`, a `frob check --ticket`-scoped COV001/SELFAUDIT/
    REL001 sweep over the ticket's own diff, or its own equivalent) opts
    in by passing an explicit `True`/`False`.
    `live_tracker_citations`, by contrast, is a plain `git
    grep` under `root` (against `current_branch(root)` as the diff base,
    T-0854 rework's diff-aware exemption -- see the module docstring in
    `frob.tickets._live_tracker`) -- cheap enough (T-0854's own PERF
    guard: "a targeted grep-shaped scan, not a full registry parse per
    close") to run unconditionally here, so every caller (direct `frob
    ticket close` and `land`'s own post-merge finalize call) gets it for
    free with no injection plumbing to wire; an unresolvable branch (not a
    git work tree) degrades to skipping the check, matching T-0844's own
    `_close_mutation_evidence_for_ticket` posture for the identical
    failure mode."""
    structural = _done_transition_structural_guard(
        ticket, queue, covers_scope=covers_scope
    )
    if structural.is_err:
        return structural
    if reviewed is False:
        _log.warning(
            "tickets: %s cannot close --strict, no approve-verdict review "
            "record names the current commit",
            ticket.id,
        )
        return Err(TicketError.MissingApprovedReview)
    if mutation_evidence is False:
        _log.warning(
            "tickets: %s cannot close, confirmatory-only evidence (TEST016 "
            "ERROR) for kind=%s -- strengthen the named evidence tests or "
            "retry with --skip-mutation-evidence",
            ticket.id,
            ticket.kind,
        )
        return Err(TicketError.EvidenceConfirmatoryOnly)
    if evidence_reverified is False:
        _log.warning(
            "tickets: %s cannot close, a fresh re-run of its own recorded "
            "evidence against the current tree did not pass -- the "
            "work was tested once but has since regressed; fix the break "
            "or re-record evidence (`frob ticket evidence %s <node-id>...`) "
            "and retry",
            ticket.id,
            ticket.id,
        )
        return Err(TicketError.EvidenceNotPassing)
    if own_obligations_clean is False:
        _log.warning(
            "tickets: %s cannot close, this ticket's own diff leaves a "
            "new-symbol doc edge, testsuite declaration, or REL001 bump "
            "outstanding -- run `frob check --delta` (or the named gate) "
            "and resolve the finding(s) it names, then retry",
            ticket.id,
        )
        return Err(TicketError.OwnObligationsUnclean)
    return _done_transition_diff_derived_guard(root, ticket)


# frob:ticket T-0976
def _done_transition_diff_derived_guard(
    root: Path, ticket: Ticket
) -> Result[None, TicketError]:
    """`_done_transition_guard`'s two diff-derived, ALWAYS-run (not
    injected) DONE-transition checks: T-0854's live-tracker-citation
    refusal, and T-0756's new-gate-rule-needs-acceptance refusal. Both
    resolve `current_branch(root)` once and degrade to skipping the check
    when it is unresolvable (not a git work tree), matching this module's
    other diff-derived checks' failure posture."""
    from frob.gitio import current_branch

    branch = current_branch(root)
    citations = (
        live_tracker_citations(root, ticket.id, base_ref=branch.danger_ok)
        if branch.is_ok
        else ()
    )
    if citations:
        _log.warning(
            "tickets: %s cannot close, %d site(s) still cite it as their "
            "live tracker (registry deferred:/tracked_by: disposition or a "
            "waiver ticket= attribute): %s -- file a successor ticket and "
            "re-point these rows, or re-point them in this same change",
            ticket.id,
            len(citations),
            list(citations),
        )
        return Err(TicketError.LiveTrackerCited)
    new_rule_ids = (
        new_gate_rule_ids(root, base_ref=branch.danger_ok) if branch.is_ok else ()
    )
    unaccepted = missing_acceptance_for_new_rules(ticket, new_rule_ids or ())
    if unaccepted:
        _log.warning(
            "tickets: %s cannot close, adds new gate rule id(s) %s with no "
            "bound before-fails/after-passes fixture acceptance criterion "
            "(T-0756) -- record one proving the rule fires through the "
            "production invocation, then retry",
            ticket.id,
            list(unaccepted),
        )
        return Err(TicketError.NewGateRuleUnaccepted)
    return Ok(None)


# frob:ticket T-0976
def _recover_missing_evidence_for_done(
    root: Path,
    ticket_id: str,
    ticket: Ticket,
    queue: dict[str, Ticket],
    to: "TicketState",
) -> tuple[Ticket, dict[str, Ticket]]:
    """T-0357 best-effort evidence recovery for `transition`: a ticket
    closed straight from a hand-merged worktree (bypassing `frob ticket
    land`'s ledger splice) can arrive with an empty structured `evidence:`
    field even though its Done report prose already carries the rendered
    ids -- replay it before the DONE guard would otherwise reject as
    MissingEvidence. A no-op (returns `(ticket, queue)` unchanged) unless
    `to` is DONE, evidence is already empty is false, or the replay
    itself fails."""
    if to != TicketState.DONE or ticket.evidence:
        return ticket, queue
    replayed = replay_evidence_from_done_report(root, ticket_id)
    if replayed.is_err:
        return ticket, queue
    recovered = replayed.danger_ok
    updated_queue = dict(queue)
    updated_queue[ticket_id] = recovered
    return recovered, updated_queue


# frob:invariant INV-002
# invariant spec: [INV-002](invariants/INV-002.md)
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_rejects_when_mutation_evidence_false  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_allows_when_mutation_evidence_true  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_permissive_when_mutation_evidence_none  # noqa: E501
# frob:tests tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard.test_epic_close_refused_with_open_descendant  # noqa: E501
# frob:tests tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard.test_epic_close_allowed_once_descendant_done  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_rejects_when_evidence_reverified_false  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_permissive_when_evidence_reverified_none  # noqa: E501
# frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_rejects_when_own_obligations_clean_false  # noqa: E501
# frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_allows_when_own_obligations_clean_true  # noqa: E501
# frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_permissive_when_own_obligations_clean_none  # noqa: E501
# frob:ticket T-0715
# frob:ticket T-0417
# frob:ticket T-1384
def transition(
    root: Path,
    ticket_id: str,
    to: TicketState,
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
    own_obligations_clean: bool | None = None,
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a
    substantive Done report, (D-02) an evidence id covering a touched/
    scope symbol whenever the caller supplies `covers_scope=False`,
    (T-0571) an approve-verdict review record naming the current commit
    whenever the caller supplies `reviewed=False`, (T-0844) refuses on
    an unwaived ERROR-severity TEST016 confirmatory-only-evidence finding
    whenever the caller supplies `mutation_evidence=False`, (T-0417
    N-02) refuses when a fresh re-run of the ticket's recorded evidence
    against the CURRENT tree no longer passes, whenever the caller
    supplies `evidence_reverified=False`, and (T-1384) refuses when the
    ticket's own diff leaves a new-symbol doc/testsuite/REL001 obligation
    outstanding, whenever the caller supplies
    `own_obligations_clean=False` (see `_done_transition_guard`'s
    docstring for why these are injected rather than computed here)."""
    from frob.tickets import _TRANSITIONS, _load_ticket_and_queue, write_ticket

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_ticket_and_queue(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket, queue = loaded.danger_ok
    ticket, queue = _recover_missing_evidence_for_done(
        root, ticket_id, ticket, queue, to
    )

    allowed = _TRANSITIONS.get(ticket.state, frozenset())
    if to not in allowed:
        _log.warning(
            "tickets: %s illegal transition %s -> %s", ticket_id, ticket.state, to
        )
        return Err(TicketError.InvalidTransition)

    guard = _transition_guard(
        root,
        ticket,
        to,
        queue,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        own_obligations_clean=own_obligations_clean,
    )
    if guard.is_err:
        return Err(guard.danger_err)

    updated = ticket.model_copy(update={"state": to})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s transitioned %s -> %s", ticket_id, ticket.state, to)
    _sync_cross_worktree_lease(root, ticket_id, ticket.state, to, updated.scope)
    return Ok(updated)


# frob:ticket T-1005
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_passes_on_strengthened_don\
# e_ticket
# frob:tests \
# tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_fails_loudly_on_now_failin\
# g_evidence
# frob:tests \
# tests/test_ticket_reverify.py::TestReverifyCloseGuard.test_refuses_non_done_ticket
# frob:ticket T-1384
def reverify_close_guard(
    root: Path,
    ticket_id: str,
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
    own_obligations_clean: bool | None = None,
) -> Result[Ticket, TicketError]:
    """`frob ticket reverify`'s (T-1005) state-machine half: re-run the
    EXACT SAME `_done_transition_guard` check `transition(..., TicketState.
    DONE, ...)` runs at close time -- structural (evidence + Done report
    present, no open descendants, no disallowed cmd: evidence, D-02
    covers_scope, T-0572 acceptance binding), T-0571 reviewed (when
    injected), T-0844 mutation_evidence (when injected), T-0417
    evidence_reverified (when injected), T-1384 own_obligations_clean
    (when injected), and the two ALWAYS-run diff-derived checks (T-0854
    live-tracker citation, T-0756 new-gate-rule acceptance) -- against a
    ticket that is ALREADY `done`, with NO write and NO state transition
    attempted either way. This closes churn item 6 (docs/audits/
    coordination-churn.md): after a post-close send-back (e.g. a TEST016
    strengthening) lands new scope/evidence/done-report edits on a done
    ticket, nothing could previously re-run close's own verification
    suite (`close` itself refuses done->done via the state machine;
    `start`/`sweep` both refuse a done ticket outright) -- lands
    proceeded on trust in the stale recap alone.

    Refuses immediately (`TicketError.InvalidTransition`, matching the
    state machine's own vocabulary for "wrong state to do this in") unless
    `ticket.state is TicketState.DONE` -- reverify is specifically the
    post-close re-check, not a substitute for `close` on an in-progress
    ticket. `covers_scope`/`reviewed`/`mutation_evidence`/
    `evidence_reverified`/`own_obligations_clean` are injected exactly
    like `transition`'s own parameters of the same names (the caller,
    `frob.app.ticket_runner._reverify`, computes them via the identical
    `_close_guards_for_ticket` helper `_close` itself calls -- no
    duplicated guard-computation logic, only the write/transition step is
    skipped here)."""
    from frob.tickets import _load_ticket_and_queue

    loaded = _load_ticket_and_queue(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket, queue = loaded.danger_ok
    if ticket.state is not TicketState.DONE:
        _log.warning(
            "tickets: %s reverify requires state=done (current: %s) -- "
            "reverify re-checks an already-closed ticket, it does not "
            "close one",
            ticket_id,
            ticket.state,
        )
        return Err(TicketError.InvalidTransition)
    guard = _done_transition_guard(
        root,
        ticket,
        queue,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
        own_obligations_clean=own_obligations_clean,
    )
    if guard.is_err:
        return Err(guard.danger_err)
    _log.info(
        "tickets: %s reverify: full close-time verification suite passed, "
        "state unchanged (done)",
        ticket_id,
    )
    return Ok(ticket)


# frob:ticket T-0473
def _sync_cross_worktree_lease(
    root: Path,
    ticket_id: str,
    from_state: TicketState,
    to_state: TicketState,
    scope: tuple[str, ...],
) -> None:
    """Keep the cross-worktree lease side-channel (`frob.tickets._leases`,
    T-0473) in sync with every `transition` call: record a lease on entering
    `IN_PROGRESS`, release it on leaving. Best-effort -- `_leases` degrades
    every failure to a logged warning internally, never raising here, so a
    side-channel write failure can never turn a successful ledger
    transition into a reported one."""
    from frob.tickets._leases import record_lease, release_lease

    if to_state is TicketState.IN_PROGRESS:
        record_lease(root, ticket_id, scope)
    elif from_state is TicketState.IN_PROGRESS:
        release_lease(root, ticket_id)


# frob:doc docs/modules/tickets.md#public-api
# frob:waive ARCH001 reason="a typani Result guard chain (lease, schema, resolution, pass-check, then acceptance-range) where each stage is already its own dedicated helper (_check_evidence_resolution, _check_evidence_passing, ...); the length is the sequence of early-return guard calls itself, matching this module's own idiomatic and_then style -- splitting further would just rename the same guard clauses behind a second layer of indirection"  # noqa: E501
def add_evidence(
    root: Path,
    ticket_id: str,
    node_ids: Sequence[str],
    collected: frozenset[str] | None = None,
    passed: frozenset[str] | None = None,
    accepts: Sequence[int] | None = None,
) -> Result[Ticket, TicketError]:
    """Validate `node_ids` against `collected` pytest node ids and (D-01)
    against `passed` -- the ids a caller has actually observed PASS on a
    real run -- and append the resolvable, passing ones to the ticket's
    structured evidence list; rejecting the whole batch
    (Err(UnknownEvidence) / Err(EvidenceNotPassing)) if any id fails either
    check, so neither a typo'd id NOR a red/failing test can sneak into
    evidence and surface only at close time (the failure mode this command
    exists to close at write time).

    `collected`/`passed` are supplied by the caller (frob.testing) rather
    than fetched here, keeping this library free of the frob.graph
    dependency frob.testing pulls in. `collected=None` skips resolution
    (schema validation still applies) -- the T-0102 in-process path where
    no collector is available. `passed=None` (default, matching every
    caller before D-01) skips pass-verification the same way -- a caller
    with no test-run oracle available is unaffected; a caller that actually
    ran the tests (`frob.testing.run_selected` or equivalent) opts in by
    passing the observed-passing subset. cmd: evidence entries are exempt
    from `passed` (verified by their own exit-code/digest channel instead,
    see `add_cmd_evidence`/`reverify_cmd_evidence`).

    `accepts` (T-0572) is a list of 0-based `ticket.acceptance` indices:
    every `node_ids` entry is ALSO bound onto each named acceptance
    criterion's own `evidence` tuple, in the same write as the evidence-list
    append -- the CLI surface for closing the "closed but not what was
    asked" hole (`--accepts N` on `frob ticket evidence`/`close`).
    `accepts=None` (default) binds nothing, matching every caller before
    T-0572. An out-of-range index rejects the whole batch
    (`Err(AcceptanceIndexOutOfRange)`) before anything is written -- a
    typo'd index must never silently bind evidence to the wrong criterion
    or to nothing at all."""
    from frob.tickets import _validate_evidence_list

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    validated = _validate_evidence_list(tuple(node_ids))
    if validated.is_err:
        return Err(validated.danger_err)
    # T-0293: validation normalizes a dot-separated Class.method suffix to
    # the pytest Class::method form -- resolution, pass-checking, and the
    # persisted evidence must all use the NORMALIZED ids from here on, or a
    # dot-form id would still be checked/stored under its original,
    # never-resolving spelling.
    normalized_ids = validated.danger_ok
    from frob.tickets import _load_one

    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    resolution = _check_evidence_resolution(ticket_id, normalized_ids, collected)
    if resolution.is_err:
        return Err(resolution.danger_err)

    passing = _check_evidence_passing(ticket_id, normalized_ids, passed)
    if passing.is_err:
        return Err(passing.danger_err)

    if accepts is not None:
        out_of_range = [i for i in accepts if i < 0 or i >= len(ticket.acceptance)]
        if out_of_range:
            _log.warning(
                "tickets: %s --accepts index/indices out of range %s "
                "(ticket has %d acceptance item(s))",
                ticket_id,
                out_of_range,
                len(ticket.acceptance),
            )
            return Err(TicketError.AcceptanceIndexOutOfRange)

    return _append_evidence_and_write(root, ticket, ticket_id, normalized_ids, accepts)


def _check_evidence_resolution(
    ticket_id: str, node_ids: Sequence[str], collected: frozenset[str] | None
) -> Result[None, TicketError]:
    """`Err(UnknownEvidence)` if any of `node_ids` fails to resolve against
    `collected`; `collected=None` skips resolution entirely (D-08: this is
    the "unresolved" path -- always logged at WARNING so a `collected=None`
    call is never silent about the gap, even though it cannot reject)."""
    if collected is None:
        _log.warning(
            "tickets: %s evidence %s recorded UNRESOLVED -- no collector "
            "supplied, existence against the current test suite was not "
            "checked (run `frob check` to catch a stale id via COV003)",
            ticket_id,
            list(node_ids),
        )
        return Ok(None)
    unresolved = [nid for nid in node_ids if not matches_collected(nid, collected)]
    if unresolved:
        _log.warning(
            "tickets: %s evidence rejected, unresolved id(s) %s "
            "(the collection cache self-refreshes on the next `frob test` "
            "/ `frob check` run; if it still does not resolve, delete "
            ".frob/pytest-collect.json (or .frob/cargo-collect.json for "
            "rust) to force a rebuild, or fix the id)",
            ticket_id,
            unresolved,
        )
        return Err(TicketError.UnknownEvidence)
    return Ok(None)


def _check_evidence_passing(
    ticket_id: str, node_ids: Sequence[str], passed: frozenset[str] | None
) -> Result[None, TicketError]:
    """`Err(EvidenceNotPassing)` if any non-cmd id in `node_ids` is absent
    from `passed` (D-01); `passed=None` skips the check entirely (no
    pass/fail oracle supplied -- back-compat default, see `add_evidence`)."""
    if passed is None:
        return Ok(None)
    failing = [
        nid for nid in node_ids if not is_cmd_evidence(nid) and nid not in passed
    ]
    if failing:
        _log.warning(
            "tickets: %s evidence rejected, did not pass on last run: %s "
            "(re-run `frob test`, fix the failure, then re-record evidence)",
            ticket_id,
            failing,
        )
        return Err(TicketError.EvidenceNotPassing)
    return Ok(None)


def _append_evidence_and_write(
    root: Path,
    ticket: Ticket,
    ticket_id: str,
    node_ids: Sequence[str],
    accepts: Sequence[int] | None = None,
) -> Result[Ticket, TicketError]:
    """Merge new `node_ids` into `ticket.evidence` (deduplicated), bind them
    onto each `accepts`-named acceptance criterion's own `evidence` tuple
    (T-0572, also deduplicated), and write the updated ticket in one atomic
    write -- the append and the acceptance binding are never split across
    two writes, so a crash between them can never leave evidence recorded
    without its acceptance mapping (or vice versa)."""
    from frob.tickets import write_ticket

    merged = ticket.evidence + tuple(
        nid for nid in node_ids if nid not in ticket.evidence
    )
    acceptance = ticket.acceptance
    if accepts:
        acceptance = tuple(
            c.model_copy(
                update={
                    "evidence": c.evidence
                    + tuple(nid for nid in node_ids if nid not in c.evidence)
                }
            )
            if i in accepts
            else c
            for i, c in enumerate(acceptance)
        )
    updated = ticket.model_copy(update={"evidence": merged, "acceptance": acceptance})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s recorded %d evidence id(s) (%d total)",
        ticket_id,
        len(node_ids),
        len(updated.evidence),
    )
    return Ok(updated)


# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_cmd_evidence.py::TestCmdEvidence.test_exit_zero
# frob:tests tests/test_tickets_cmd_evidence.py::TestCmdEvidence.test_nonzero_exit
def run_cmd_evidence(command: str, cwd: Path | None = None) -> Result[str, TicketError]:
    """Run `command` as an argv (no shell, T-0805) and fold its outcome
    into one evidence string (`cmd:<command> exit=0 sha256=<12-hex>`) --
    the non-pytest
    evidence primitive `add_cmd_evidence` records for docs/design tickets
    (T-0215). A nonzero exit or a command that fails to launch at all is
    Err(EvidenceCmdFailed): a broken or never-run command can never
    masquerade as evidence just by being named. The digest is taken over
    stdout only (deterministic across whitespace-only stderr noise) so the
    same command run twice against the same repo state records the same
    entry instead of appending a new one every time.

    `cwd` (T-0834) is where `command` is actually run -- `add_cmd_evidence`
    passes the ticket's resolved `--path` root so a relative-path probe
    (`grep`/`test` over ticket scope files) runs against the worktree the
    evidence claim is ABOUT, not whatever directory happened to invoke the
    CLI. `None` (the `reverify_cmd_evidence` re-check path) keeps the
    previous behavior of inheriting the current process cwd.
    """
    from frob.tickets import validate_evidence

    completed = _run_evidence_command(command, cwd=cwd)
    if completed.is_err:
        return Err(completed.danger_err)
    digest = hashlib.sha256(completed.danger_ok.stdout.encode("utf-8")).hexdigest()[:12]
    entry = f"cmd:{command} exit=0 sha256={digest}"
    return validate_evidence(entry)


_CMD_EVIDENCE_PARSE_RE = re.compile(
    r"^cmd:(?P<command>.+) exit=0 sha256=(?P<sha>[0-9a-f]{12})$"
)


# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_true_when_command_still_reproduces  # noqa: E501
def reverify_cmd_evidence(entry: str) -> Result[bool, TicketError]:
    """Re-run the command a `cmd:` evidence entry recorded and confirm it
    still exits 0 with the SAME stdout digest (D-10): `run_cmd_evidence`'s
    sha256 is otherwise a record-time-only attestation nothing ever
    re-checks. `Ok(True)`/`Ok(False)` report whether the command still
    reproduces; `Err(MalformedEvidence)` if `entry` is not a well-formed
    `cmd:` entry at all.

    Deliberately opt-in, not wired into `_done_transition_guard`/COV003 by
    default: re-running an arbitrary recorded command on every check is
    exactly the cost/non-idempotence tradeoff `_evidence_valid_for_ticket`
    already documents choosing NOT to pay unconditionally (a docs command
    may be slow, or legitimately non-deterministic in a way that does not
    indicate the underlying claim is false). A caller that wants the
    stronger guarantee for a specific entry calls this directly."""
    match = _CMD_EVIDENCE_PARSE_RE.match(entry)
    if match is None:
        _log.warning("tickets: reverify_cmd_evidence: not a cmd: entry: %r", entry)
        return Err(TicketError.MalformedEvidence)
    command, recorded_sha = match.group("command"), match.group("sha")
    completed = _run_evidence_command(command)
    if completed.is_err:
        _log.warning("tickets: reverify_cmd_evidence: %r no longer exits 0", command)
        return Ok(False)
    digest = hashlib.sha256(completed.danger_ok.stdout.encode("utf-8")).hexdigest()[:12]
    matches = digest == recorded_sha
    if not matches:
        _log.warning(
            "tickets: reverify_cmd_evidence: %r stdout digest changed (%s -> %s)",
            command,
            recorded_sha,
            digest,
        )
    return Ok(matches)


def _run_evidence_command(
    command: str,
    cwd: Path | None = None,
) -> Result[subprocess.CompletedProcess, TicketError]:
    """Spawn `command` as an argv (never through a shell) and return its
    completed process; `Err(EvidenceCmdFailed)` if it fails to parse, fails
    to launch, or exits nonzero.

    `cwd` (T-0834) is forwarded straight to `guarded_subprocess_run`/
    `subprocess.run`; `None` inherits the current process's cwd (the
    pre-T-0834 default, still used by `reverify_cmd_evidence`). A relative-
    path command (a `grep`/`test` probe over ticket scope files) is only
    meaningful relative to the ticket's own worktree, not wherever the CLI
    happened to be invoked from -- see `run_cmd_evidence`.

    T-0805: previously ran `command` with `shell=True` -- ticket YAML
    (`cmd:` evidence entries) is repo-writable by any agent/tool, so a
    string handed to a shell is an injection-adjacent surface, not a
    hardened one, even though evidence commands are a sanctioned feature
    (T-0215). A survey of every `cmd:` entry actually recorded in
    `tickets.md`/`tickets-archive.md` at the time of this fix found five
    distinct commands; four are plain argv (`grep -n ...`, `grep -q ...`,
    `python3 <script>`, `uv run frob check --only docblocks`) and parse
    unchanged under `shlex.split`. Exactly one (an already-closed,
    archived ticket's evidence, `test "$(grep -c ...)" = N && test ...`)
    relies on shell command substitution and `&&` sequencing and cannot be
    expressed as a single argv; that entry is dead (its ticket is `done`,
    nothing re-verifies it live) and is the documented migration case --
    future evidence needing multi-step or substitution logic should shell
    out to a checked-in script (`cmd:python3 <script>` or
    `cmd:bash <script>`) invoked as a single argv entry instead of relying
    on inline shell syntax.

    Routed through `guarded_subprocess_run` (T-0778) so `FROB_DISABLE_EXEC`
    stops evidence commands too, not just `frob check`'s own tool runners.
    """
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        _log.error(
            "tickets: evidence command %r failed to parse as argv: %s", command, exc
        )
        return Err(TicketError.EvidenceCmdFailed)
    if not argv:
        _log.error("tickets: evidence command %r parsed to an empty argv", command)
        return Err(TicketError.EvidenceCmdFailed)
    try:
        guarded = guarded_subprocess_run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
    except OSError as exc:
        _log.error(
            "tickets: evidence command %r failed to launch (cwd=%s): %s",
            command,
            cwd,
            exc,
        )
        return Err(TicketError.EvidenceCmdFailed)
    if guarded.is_err:
        _log.error(
            "tickets: evidence command %r refused: %s", command, guarded.danger_err
        )
        return Err(TicketError.EvidenceCmdFailed)
    completed = guarded.danger_ok
    if completed.returncode != 0:
        _log.warning(
            "tickets: evidence command %r exited %d (cwd=%s, stderr tail: %r)",
            command,
            completed.returncode,
            cwd,
            completed.stderr[-500:],
        )
        return Err(TicketError.EvidenceCmdFailed)
    return Ok(completed)


# frob:waive DUP001 reason="dup grouped this tiny kind-in-allowlist guard clause with \
# several unrelated small validators across the repo (src/frob/gates/invariants.py, \
# src/frob/strata/_elaborate.py, src/frob/tickets/_land.py, \
# src/frob/tickets/_scope.py) purely on the generic 'check membership, log, return \
# Err/Ok' shape (rung=r2, low precision on functions this small) -- each guards a \
# completely different domain-specific allowlist, not a copy of this one; surfaced \
# fresh by the T-1152 evidence-family module split (file-identity is part of the dup \
# pairing key), same false-positive class as the T-0861 DEBT001/DEPR001/TEST010 \
# precedent"
def _check_cmd_evidence_kind(
    ticket_id: str, kind: TicketKind
) -> Result[None, TicketError]:
    """`Err(EvidenceKindNotAllowed)` unless `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS`."""
    if kind not in CMD_EVIDENCE_ALLOWED_KINDS:
        _log.warning(
            "tickets: %s is kind=%s, cmd evidence only allowed for kind in %s",
            ticket_id,
            kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
        )
        return Err(TicketError.EvidenceKindNotAllowed)
    return Ok(None)


# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_cmd_evidence.py::TestKindGate.test_docs_kind_closes
# frob:tests tests/test_tickets_cmd_evidence.py::TestKindGate.test_bug_kind_rejected
def add_cmd_evidence(
    root: Path,
    ticket_id: str,
    command: str,
    accepts: Sequence[int] | None = None,
) -> Result[Ticket, TicketError]:
    """Kind-gated non-pytest evidence channel (T-0215): runs `command` via
    `run_cmd_evidence` and appends the resulting entry to `ticket_id`'s
    structured evidence list. Only tickets whose `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS` (currently just `docs`) may use this --
    code-kind tickets (bug/feature/security/ux/invariant/incident) always
    still require real pytest node ids via `add_evidence`, enforced here
    with Err(EvidenceKindNotAllowed) so a code change can never close on an
    unrelated shell command's exit status alone.

    `accepts` (T-0796) mirrors `add_evidence`'s acceptance-binding: a list
    of 0-based `ticket.acceptance` indices the recorded cmd-evidence entry
    is ALSO bound onto, in the same write as the evidence-list append. Its
    validation is identical to `add_evidence` -- an out-of-range index
    rejects the whole call (`Err(AcceptanceIndexOutOfRange)`) before
    anything is written. Before T-0796 this parameter did not exist, so
    `--accepts` passed alongside `--evidence-cmd` on the CLI was silently
    dropped and docs-kind tickets closed with UNBOUND acceptance despite
    the operator's explicit binding request.
    """
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    kind_check = _check_cmd_evidence_kind(ticket_id, ticket.kind)
    if kind_check.is_err:
        return Err(kind_check.danger_err)

    if accepts is not None:
        out_of_range = [i for i in accepts if i < 0 or i >= len(ticket.acceptance)]
        if out_of_range:
            _log.warning(
                "tickets: %s --accepts index/indices out of range %s "
                "(ticket has %d acceptance item(s))",
                ticket_id,
                out_of_range,
                len(ticket.acceptance),
            )
            return Err(TicketError.AcceptanceIndexOutOfRange)

    # T-0834: run the command from the ticket's own resolved `--path` root,
    # not the invoking process's cwd -- the evidence claim is about the
    # worktree named by `root`, and a relative-path probe (grep/test over
    # scope files) silently ran against whatever directory happened to
    # invoke the CLI before this, with no indication of which cwd it used.
    recorded = run_cmd_evidence(command, cwd=root)
    if recorded.is_err:
        return Err(recorded.danger_err)
    entry = recorded.danger_ok

    return _append_evidence_and_write(root, ticket, ticket_id, (entry,), accepts)


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestRenderEvidenceBlock.test_mixed_cmd_and_pytest_ids  # noqa: E501
def render_evidence_block(evidence: Sequence[str]) -> str:
    """Auto-fill a Done report's Evidence section from a ticket's already-
    recorded evidence ids alone (T-0458 REFINEMENT).

    No fresh collection or test run is needed here: every id in `evidence`
    was ALREADY validated resolvable-and-passing (pytest, `add_evidence`'s
    D-01 `passed` check) or exit=0 (`cmd:` entries, `add_cmd_evidence`) at
    the moment it was accepted into the ticket -- so this just renders what
    frob already knows to be true, instead of the agent retyping node ids
    and pass counts by hand (the class of drift that produced this
    session's stale-evidence-id incidents).
    """
    if not evidence:
        return "(no evidence recorded)"
    lines = []
    for eid in evidence:
        if is_cmd_evidence(eid):
            lines.append(f"- `{eid}` (cmd evidence, exit=0)")
        else:
            lines.append(f"- `{eid}` (pytest node id, verified passing when recorded)")
    return "\n".join(lines)


# frob:ticket T-0357
_EVIDENCE_LINE_RE = re.compile(r"^- `([^`]+)` \((?:pytest node id|cmd evidence)")


def _parse_evidence_ids_from_done_report(body: str) -> tuple[str, ...]:
    """Recover evidence ids from a ticket's rendered '## Done report' ->
    '### Evidence' section text, the inverse of `render_evidence_block`
    (T-0357). A worktree's structured `evidence:` field is the source of
    truth in the ordinary case; this exists only for the recovery path
    where that field is empty (or was lost by a hand-merge that bypassed
    the ledger splice) but the committed Done report prose still carries
    the rendered ids -- so a coordinator merging a worktree branch by hand
    (`git merge --no-ff` + `frob ticket close` on main, T-0248/T-0266) is
    never stuck re-typing node ids by hand. Returns ids in the order they
    appear, deduplicated; `()` if no '### Evidence' section or no
    recognizable rendered lines are found."""
    section = _done_report_section_lines(body)
    if section is None:
        return ()
    ids: list[str] = []
    in_evidence = False
    for line in section:
        stripped = line.strip()
        if stripped.startswith("### "):
            in_evidence = stripped == "### Evidence"
            continue
        if not in_evidence:
            continue
        match = _EVIDENCE_LINE_RE.match(stripped)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return tuple(ids)


# frob:ticket T-0357
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_recovers_ids_when_structured_evidence_empty  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_noop_when_evidence_already_present  # noqa: E501
def replay_evidence_from_done_report(
    root: Path, ticket_id: str
) -> Result[Ticket, TicketError]:
    """Recover `ticket_id`'s structured `evidence:` field from its own
    committed Done report prose when the field is empty (T-0357): the
    coordinator-land bug where evidence recorded via `frob ticket evidence`
    in a worktree never made it into main's ledger in a form `frob ticket
    close` recognizes (a hand `git merge --no-ff` that bypassed the T-0176/
    T-0479 ledger splice, or a splice that otherwise dropped the field
    while the Done report text survived). Best-effort and idempotent: a
    ticket that already carries structured evidence is returned unchanged
    (`Ok`, no write); a ticket with no evidence and no recognizable
    rendered ids in its Done report returns `Err(MissingEvidence)`
    unchanged -- there is nothing to replay. Recovered ids are NOT
    re-validated against a fresh pytest collection or pass/fail run (no
    such oracle is available here, and re-validating would defeat the
    point of a same-repo-state recovery); callers that need that guarantee
    should follow up with `frob check`'s COV003/TEST001 gates, which
    re-verify independently."""
    from frob.tickets import _load_one, write_ticket

    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        if ticket.evidence:
            return Ok(ticket)
        recovered = _parse_evidence_ids_from_done_report(ticket.body)
        if not recovered:
            _log.warning(
                "tickets: %s has no structured evidence and no recoverable "
                "ids in its Done report -- nothing to replay",
                ticket_id,
            )
            return Err(TicketError.MissingEvidence)
        updated = ticket.model_copy(update={"evidence": recovered})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.warning(
        "tickets: %s replayed %d evidence id(s) from its Done report text "
        "(structured evidence: field was empty) -- %s",
        ticket_id,
        len(recovered),
        list(recovered),
    )
    return Ok(updated)


# frob:ticket T-0887
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_unresolvable_ref_in_a_real_repo_is_false  # noqa: E501
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_resolvable_ref_is_true  # noqa: E501
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_non_git_root_is_none  # noqa: E501
def base_ref_resolvable(root: Path, base_ref: str) -> bool | None:
    """Bounded (`run_argv`'s own timeout, never unbounded) check of whether
    `base_ref` resolves to a real commit in `root`'s clone, via `git
    rev-parse --verify --quiet <base_ref>^{commit}` -- the fail-fast guard
    `set_done_report` runs before any other work (T-0887: a typo'd or
    unfetched base ref used to be discovered only indirectly, minutes
    later, via a silently-empty `git diff --stat` or a downstream `frob
    check --ticket` spawn, rather than on the ref itself in seconds).

    Returns `True`/`False` when `root` is a real git checkout (ref
    resolves or does not); returns `None` when `root` itself is not a git
    checkout at all (git's own `not a git repository` exit code, 128) --
    that is a DIFFERENT failure than an unresolvable ref, and callers
    must treat it as "unknown", never as "unresolvable", to preserve the
    pre-T-0887 best-effort behavior for non-git roots (`compute_changed_
    lines`'s own long-standing contract, and every existing `set_done_
    report` caller in the test suite that passes a bare `tmp_path` with
    no git init at all)."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{base_ref}^{{commit}}",
        ]
    )
    if spawned.is_err:
        return None
    result = spawned.danger_ok
    if result.returncode == 128:
        # Not a git repository at all -- unrelated to the ref itself.
        return None
    return result.returncode == 0


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComputeChangedLines.test_non_git_root_returns_empty  # noqa: E501
def compute_changed_lines(root: Path, base_ref: str = "main") -> tuple[str, ...]:
    """Best-effort `git diff --stat <base_ref>...HEAD` lines for a Done
    report's Changed section (T-0458 REFINEMENT) -- pulled straight from
    git, never retyped by the agent (the exact class of error that dropped
    `render.md` / mis-listed files by hand this session).

    Returns an empty tuple (never raises, never Err) if `root` is not a git
    checkout or the diff itself fails -- the Changed block is auxiliary
    evidence for the report, not a precondition for writing one; a caller
    that wants a hard failure on a broken git state should check `root`
    itself before calling `set_done_report`.
    """
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "diff", "--stat", f"{base_ref}...HEAD"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "tickets: git diff --stat %s...HEAD unavailable for done-report "
            "Changed block (root=%s)",
            base_ref,
            root,
        )
        return ()
    return tuple(line for line in spawned.danger_ok.stdout.splitlines() if line.strip())


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestRenderChangedBlock.test_lines_rendered_fenced  # noqa: E501
def render_changed_block(lines: Sequence[str]) -> str:
    """Render `compute_changed_lines`'s output as a Done report Changed
    section (fenced verbatim, since git's `--stat` output is already
    human-readable columns) (T-0458)."""
    if not lines:
        return "(no changed files detected)"
    return "```\n" + "\n".join(lines) + "\n```"

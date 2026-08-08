"""
frob.tickets -- statically-checkable ticket and feature queue (docs/modules/tickets.md).

A git-tracked queue of tickets (features, bugs, audits, invariant work) with
a state machine, blockers, evidence, failure memory, and image attachments --
the shared work surface for the human and every agent. No dependency on
frob.graph or frob.lang by design (see docs/rework.md cycle-avoidance).
"""
# frob:waive ARCH102 reason="108 of 116 exports form one connected cluster around the \
# ticket state machine this docstring names (transition/ \
# doable/new_ticket/add_evidence/mutate_scope/... all threading the same \
# TicketQueue/Ticket model); the remaining 6 (migrate, sprint_view, board_view, \
# epic_rollup, closed_ticket_ids, and the small display_state/ \
# has_approved_review_for_commit/has_live_lease trio) are small read-only \
# views/reports over that exact same queue, coupled to it by the shared data model \
# rather than by direct calls into the state-machine functions -- this is the single \
# ticket-queue module the docstring deliberately centralizes (no frob.graph/frob.lang \
# dependency by design), not several concerns bolted together"

from __future__ import annotations

import subprocess  # noqa: F401 -- re-exported: tests/test_tickets_cmd_evidence.py's

# TestRunCmdEvidenceLaunchFailure monkeypatches `tickets_mod.subprocess.run`
# (the PACKAGE attribute, predating the T-1152 evidence-family split) to
# simulate an OSError on launch -- `subprocess` is one shared module object
# process-wide, so this binding only needs to exist here for the patch to
# reach `_evidence._run_evidence_command`'s own `guarded_subprocess_run`
# call, which shells out through the SAME `subprocess` module.
import tomllib
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._accept import amend_acceptance, remove_acceptance
from frob.tickets._archive import (
    _load_merged,
    archive,
    load_active,
    load_queue,
    migrate,
)
from frob.tickets._doable import (
    _repo_files,  # noqa: F401 -- re-exported so `_doable.scope_breadth_context`'s own
    # late `from frob.tickets import _repo_files` (monkeypatch-indirection, T-1108)
    # resolves; not referenced by name elsewhere in this module.
    _repo_files_git,  # noqa: F401 -- re-exported: tests/test_tickets_lease.py's
    # TestBreadthPerf imports this directly off the package (`from frob.tickets
    # import _repo_files_git`), predating this split.
    already_landed_markers,
    dispatch_stale_hours,
    display_state,
    doable,
    doable_blocked,
    has_live_lease,
    large_glob_warnings,
    leased_by,
    scope_breadth_context,
    undispatched_stale,
)
from frob.tickets._draft_finalize import finalize_draft, finalize_draft_for_land
from frob.tickets._evidence import (
    _check_evidence_resolution,  # noqa: F401 -- re-exported: `_new_renumber.new_ticket`'s
    # own late `from frob.tickets import _check_evidence_resolution` (T-1103's
    # documented load-time-circular-import workaround) resolves against this
    # package attribute; not referenced by name elsewhere in this module.
    _run_evidence_command,  # noqa: F401 -- re-exported: tests/test_tickets_evidence_cli.py's
    # TestRunEvidenceCommandNoShell imports this directly off the package
    # (`from frob.tickets import _run_evidence_command`), predating the
    # T-1152 evidence-family split; not referenced by name elsewhere in
    # this module.
    add_cmd_evidence,
    add_evidence,
    base_ref_resolvable,
    compute_changed_lines,
    render_changed_block,
    render_evidence_block,
    replace_evidence,
    replay_evidence_from_done_report,
    reverify_close_guard,
    reverify_cmd_evidence,
    run_cmd_evidence,
    transition,
)
from frob.tickets._land import land, land_plan, splice_ledger
from frob.tickets._land_queue import (
    QueueEntry,
    QueueError,
    drain_next,
    enqueue,
    queue_status,
)
from frob.tickets._leases import (
    LeaseError,
    is_lease_ttl_expired,
    lease_age_seconds,
    leases_dir,
    read_all_leases,
    resolve_lease,
    sweep_worktrees,
    warn_if_worktree_stale,
)
from frob.tickets._models import (
    BOARD_STATES,
    PRIORITY_RANK,
    AcceptanceAmendmentEntry,
    AcceptanceAmendmentOp,
    AcceptanceCriterion,
    Attachment,
    AttachmentSource,
    BoardColumn,
    DoneReportClaims,
    EpicRollup,
    FailureEntry,
    LandError,
    LandPlanReport,
    LandReport,
    Origin,
    Priority,
    ReviewEntry,
    ReviewVerdict,
    ScopeChangeEntry,
    ScopeChangeOp,
    SprintReport,
    SprintTransition,
    SprintVelocityReport,
    Stride,
    Ticket,
    TicketError,
    TicketFlowReport,
    TicketFlowRow,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    TicketTier,
    is_cmd_evidence,
    is_valid_ticket_ref,
    parse_claims_from_done_report,
    recover_done_report_why,
    render_claims_block,
    scope_matches,
    scope_overlap_globs,
    unbound_acceptance,
)
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)
from frob.tickets._new_renumber import (
    new_ticket,
    renumber,
    renumber_one,
)
from frob.tickets._reconcile import ReconcileReport, reconcile
from frob.tickets._reporting import (
    AttachError,
    attach,
    brief_cluster,
    brief_ticket,
    compose_done_report,
    drop_ticket,
    has_approved_review_for_commit,
    mutate_labels,
    record_failure,
    record_review,
    set_done_report,
)
from frob.tickets._scope import mutate_scope
from frob.tickets._setters import (
    set_component,
    set_designated_repro_test,
    set_kind,
    set_priority,
    set_runs_last,
    set_scope_breadth_ack,
    set_sprint,
    set_tier,
    sprint_velocity,
    sprint_view,
    ticket_flow,
)
from frob.tickets._store import (
    ledger_lock,
    load_all,
    write_ticket,
)
from frob.tickets._worktree_guard import agent_env_exports, enforce_worktree_lease
from frob.tickets.clipboard import clipboard_has_image

_log = get_logger(__name__)

# state machine: legal `from` -> {legal `to` states}
_TRANSITIONS: dict[TicketState, frozenset[TicketState]] = {
    TicketState.QUEUED: frozenset({TicketState.PLANNED, TicketState.DROPPED}),
    TicketState.PLANNED: frozenset({TicketState.IN_PROGRESS, TicketState.DROPPED}),
    TicketState.IN_PROGRESS: frozenset(
        {
            TicketState.DONE,
            TicketState.BLOCKED,
            TicketState.QUEUED,
            TicketState.DROPPED,
        }
    ),
    TicketState.BLOCKED: frozenset({TicketState.IN_PROGRESS, TicketState.DROPPED}),
    TicketState.DONE: frozenset(),
    TicketState.DROPPED: frozenset(),
}

_OPEN_STATES = frozenset(
    s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
)

# frob:ticket T-0453
_LARGE_GLOB_DEFAULT_MAX_FILES = 25


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `scope_breadth_context` (public),
# which already carries the same docs/modules/tickets.md#public-api
# anchor (COV007).
def _load_large_glob_max_files(root: Path) -> int:
    """Read `[tickets] large_glob_max_files` from `frob.toml` -- the
    tunable file-count threshold `large_glob_warnings`/`leased_by` flag a
    scope glob against (T-0453). Absent config, an unreadable/malformed
    file, or a non-positive value all fall back to
    `_LARGE_GLOB_DEFAULT_MAX_FILES` rather than erroring, matching
    `frob.excludes.load_exclude_globs`'s degrade-quietly posture for
    optional config. Thin wrapper over `_leases.load_positive_int_config`
    (T-1059, DUP001: extracted the shared parse/fallback chain this and
    `_leases._load_stale_worktree_warn_commits` both needed)."""
    from frob.tickets._leases import load_positive_int_config

    return load_positive_int_config(
        root, "large_glob_max_files", _LARGE_GLOB_DEFAULT_MAX_FILES
    )


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_defaults_false_with_no_frob_toml  # noqa: E501
# frob:tests \
# tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_true_when_configured
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_false_when_absent_from_section  # noqa: E501
def load_require_review_for_close(root: Path) -> bool:
    """Read `[tickets] require_review_for_close` from `frob.toml` (T-0571):
    the strict-mode gate that requires `close` to see at least one
    `verdict: approve` review record naming the current commit. Absent
    config, an unreadable/malformed file, or a non-bool value all default to
    `False` -- off by default for backward compat, matching every other
    optional `[tickets]` toggle here (`_load_large_glob_max_files`)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("tickets: could not parse %s: %s", toml_path, exc)
        return False
    value = doc.get("tickets", {}).get("require_review_for_close")
    return value is True


# frob:ticket T-1029
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets.py::TestAddAcceptance.test_appends_criteria_to_existing_ticket
# frob:tests tests/test_tickets.py::TestAddAcceptance.test_empty_criteria_is_rejected
# frob:tests tests/test_tickets.py::TestAddAcceptance.test_blank_criteria_are_dropped
def add_acceptance(
    root: Path, ticket_id: str, criteria: Sequence[str]
) -> Result[Ticket, TicketError]:
    """Append one or more acceptance criteria to an EXISTING ticket (T-1029)
    -- before this, `frob ticket new --acceptance` was the ONLY way to
    attach a criterion at all, so a ticket that needed one added after
    filing (T-0894's agent hit this closing a new-gate-rule ticket) had no
    CLI path and had to hand-edit `tickets.md`, exactly the single-writer
    violation `frob.tickets` otherwise structurally prevents.

    Each of `criteria` becomes a fresh, UNBOUND `AcceptanceCriterion`
    (`evidence=()`) appended to the ticket's existing `acceptance` tuple --
    it does not touch or reorder anything already there, only adds. Blank
    entries (empty after `.strip()`) are silently dropped, matching
    `mutate_labels`'s comma-split normalization posture; if NOTHING
    survives that filter, this is an error (`AcceptanceChangeEmpty`) rather
    than a silent no-op write, the same "don't call this for nothing"
    discipline `mutate_scope`/`mutate_labels` already enforce.

    Held under `ledger_lock` end to end (load, write) so this can never
    interleave with a concurrent ledger mutation (T-0458 single-writer
    invariant) -- no hand-edit of `tickets.md` is ever involved."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    texts = [c.strip() for c in criteria if c.strip()]
    if not texts:
        return Err(TicketError.AcceptanceChangeEmpty)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        new_items = tuple(AcceptanceCriterion(text=t) for t in texts)
        updated = ticket.model_copy(
            update={"acceptance": ticket.acceptance + new_items}
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s acceptance +%d criteria, now %d total",
        ticket_id,
        len(new_items),
        len(updated.acceptance),
    )
    return Ok(updated)


# frob:ticket T-0409
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestClosedTicketIds.test_returns_done_and_dropped_only  # noqa: E501
def closed_ticket_ids(queue: TicketQueue) -> tuple[str, ...]:
    """Ids in `queue` (whatever store it was loaded from -- active-only or
    merged) whose state is DONE or DROPPED, oldest-first (T-0409): the
    ledger-hygiene gate's (TICK003, `frob.gates.tickets_gate`) building
    block for "how many closed tickets are sitting un-archived" -- called
    with `load_active`'s active-only queue there, since an ARCHIVED closed
    ticket is by definition no longer a hygiene problem. Kept here (not
    computed inline in `frob.gates`) so the "closed" predicate has exactly
    one definition, reused by anything that needs to answer the same
    question (`frob ticket archive`'s own move-eligibility check already
    uses the equivalent inline predicate; this is the reusable, testable
    form of it)."""
    closed = [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.DONE, TicketState.DROPPED)
    ]
    return tuple(t.id for t in sorted(closed, key=lambda t: (t.created, t.id)))


# frob:ticket T-0411
# frob:tests tests/test_tickets_priority.py::TestDoablePriorityOrdering.test_high_priority_surfaces_before_older_low_priority  # noqa: E501
def _doable_sort_key(t: Ticket) -> tuple[int, date, str]:
    """`doable`/`doable_blocked` ordering key (T-0411): highest PRIORITY_RANK
    first, then oldest-created, then id -- priority is the primary axis so a
    high-value ticket never rots behind a pile of older low-value ones, with
    age still breaking ties within the same priority (the prior behavior for
    tickets that were all effectively MEDIUM)."""
    return (-PRIORITY_RANK[t.priority], t.created, t.id)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_organization.py::TestBoardView.test_columns_in_fixed_order
def board_view(
    queue: TicketQueue,
    *,
    component: str | None = None,
    label: str | None = None,
) -> tuple[BoardColumn, ...]:
    """`frob ticket board`: every ticket grouped into `BOARD_STATES` columns,
    each priority-then-age ordered (`_doable_sort_key`, T-0411) -- a
    priority-ordered, at-a-glance view of the whole queue instead of one
    flat id-ordered list (T-0454). Optional `component`/`label` filters
    narrow to one area/tag; a ticket must match BOTH when both are given.
    Every column is always present, even empty, so the shape of the board
    never depends on what happens to be in flight right now."""
    tickets = list(queue.tickets.values())
    if component is not None:
        tickets = [t for t in tickets if t.component == component]
    if label is not None:
        tickets = [t for t in tickets if label in t.labels]
    columns = []
    # frob:waive PERF004 reason="one sorted() call per BOARD_STATES entry -- a fixed \
    # 6-iteration loop over the queue's own ticket count, not an unbounded \
    # hoisted-sort opportunity"
    for state in BOARD_STATES:
        in_state = sorted(
            (t for t in tickets if t.state is state), key=_doable_sort_key
        )
        columns.append(BoardColumn(state=state, tickets=tuple(in_state)))
    return tuple(columns)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_organization.py::TestEpicRollup.test_counts_done_and_total
def epic_rollup(queue: TicketQueue, epic_id: str) -> Result[EpicRollup, TicketError]:
    """`frob ticket epic <id>`: the full descendant subtree of `epic_id` via
    the `parent` chain (any depth, not just direct children), plus a
    done/total rollup and the ids of any LEAF descendant (no children of
    its own) that is currently BLOCKED -- the two things a human scanning
    an epic wants first, computed once instead of hand-counted (T-0454).
    `NotFound` if `epic_id` itself does not resolve in `queue`."""
    epic = queue.tickets.get(epic_id)
    if epic is None:
        return Err(TicketError.NotFound)
    children_of: dict[str, list[Ticket]] = {}
    for t in queue.tickets.values():
        if t.parent is not None:
            children_of.setdefault(t.parent, []).append(t)
    descendants: list[Ticket] = []
    frontier = [epic_id]
    seen = {epic_id}
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, ()):
            if child.id in seen:
                continue
            seen.add(child.id)
            descendants.append(child)
            frontier.append(child.id)
    done = sum(1 for t in descendants if t.state is TicketState.DONE)
    blocked_leaves = tuple(
        t.id
        for t in descendants
        if t.state is TicketState.BLOCKED and t.id not in children_of
    )
    # frob:waive PERF004 reason="single sorted() call over the finished descendants \
    # list, not inside the BFS while-loop above it -- the checker's whole-function \
    # loop scan flags it textually, not per-iteration"
    return Ok(
        EpicRollup(
            epic=epic,
            descendants=tuple(sorted(descendants, key=lambda t: t.id)),
            done=done,
            total=len(descendants),
            blocked_leaves=blocked_leaves,
        )
    )


def _load_one(root: Path, ticket_id: str) -> Result[Ticket, TicketError]:
    """Load a single ticket by id from whichever backend the repo uses."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok.get(ticket_id)
    if ticket is None:
        _log.warning("tickets: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)
    return Ok(ticket)


_MAX_EVIDENCE_LEN = 300


# frob:ticket T-0293
# frob:doc docs/modules/tickets.md#public-api
def normalize_evidence_separator(entry: str) -> str:
    """Canonicalize a `path::Class.method` (dot) evidence id to the pytest-
    collected `path::Class::method` (double-colon) form.

    T-0282 and T-0217 both had evidence hand-recorded with a dot before the
    final segment (`Class.method`), which never resolves against real
    pytest node ids (`Class::method`) and only surfaces late as a confusing
    COV003 at check time. This rewrites the single dot immediately after
    the `::`-qualified prefix into `::`, so the wrong-separator id resolves
    the same as the correct one instead of silently failing later. Returns
    `entry` unchanged when it does not match that specific dot-before-last-
    segment shape (no `::` at all, or the remainder after `::` already
    contains its own `::`, or there is no dot to rewrite).
    """
    if "::" not in entry:
        return entry
    path, _, remainder = entry.partition("::")
    if "::" in remainder:
        return entry
    dot_idx = remainder.find(".")
    if dot_idx <= 0:
        return entry
    head, tail = remainder[:dot_idx], remainder[dot_idx + 1 :]
    if not head.isidentifier() or not tail:
        return entry
    return f"{path}::{head}::{tail}"


# frob:ticket T-1706
def _has_excess_separator_segments(entry: str) -> bool:
    """`True` when `entry` has THREE OR MORE `::`-separated segments (e.g.
    `path::Class::method::extra`) -- a shape no real pytest node id or
    `cmd:` evidence entry ever takes (T-1706). Deliberately narrower than
    "any id with a remainder already containing `::`":
    `normalize_evidence_separator`'s own early-return already leaves a
    legitimate 2-segment pytest id (`path::Class::method`) untouched on
    purpose (that shape resolves fine against `matches_collected`, which
    needs the exact pytest form) -- this only catches genuinely malformed
    ids one level past that, never the ordinary pytest shape a caller
    copy-pastes straight from `pytest --collect-only` output."""
    if "::" not in entry:
        return False
    _, _, remainder = entry.partition("::")
    return remainder.count("::") >= 2


# frob:ticket T-0102
# frob:ticket T-1706
# frob:doc docs/modules/tickets.md#public-api
def validate_evidence(entry: str) -> Result[str, TicketError]:
    """One evidence string's schema: non-empty, single-line, bounded length,
    and not a 3+-segment `::`-separated shape no real pytest node id ever
    takes (T-1706).

    Writers (`new_ticket`, `add_evidence`) call this before a Ticket ever
    reaches `write_ticket`, so a malformed entry is rejected in-process
    instead of landing as broken YAML that only surfaces later when
    `load_queue` (and therefore every `frob check` gate) fails to parse it
    (T-0102 companion fix -- the vacuous-pass class started with a hand-
    edited evidence block that bypassed this validation entirely).

    Also normalizes a dot-separated `Class.method` suffix to the pytest
    `Class::method` form (T-0293) before the schema checks below run, so a
    mis-separated id is fixed at write time instead of landing as evidence
    that can never resolve.

    T-1706: checked on the RAW (pre-normalize) `entry`, not the normalized
    `stripped` result -- `normalize_evidence_separator` converts a valid
    dotted 1-`::`-segment id INTO the pytest 2-segment form, so checking
    post-normalize could not tell a legitimate dotted id apart from a
    genuinely malformed one that happened to normalize to the same segment
    count. A caller's typo'd `path::Class::method::extra` (or deeper) is
    rejected here with a specific message; a real 1-or-2-segment pytest id
    -- dotted or already `::`-separated -- is never touched by this check,
    only by resolution (`_check_evidence_resolution`) downstream."""
    if _has_excess_separator_segments(entry):
        _log.warning(
            "tickets: rejected evidence entry with 3+ '::'-separated "
            "segments (not a real pytest node id shape): %r",
            entry,
        )
        return Err(TicketError.MalformedEvidence)
    stripped = normalize_evidence_separator(entry.strip())
    if not stripped:
        _log.warning("tickets: rejected empty evidence entry")
        return Err(TicketError.MalformedEvidence)
    if "\n" in entry or "\r" in entry:
        _log.warning("tickets: rejected multi-line evidence entry %r", entry)
        return Err(TicketError.MalformedEvidence)
    if len(stripped) > _MAX_EVIDENCE_LEN:
        _log.warning(
            "tickets: rejected evidence entry over %d chars", _MAX_EVIDENCE_LEN
        )
        return Err(TicketError.MalformedEvidence)
    return Ok(stripped)


def _validate_evidence_list(
    entries: tuple[str, ...],
) -> Result[tuple[str, ...], TicketError]:
    """Validate every entry in `entries`, or the first schema failure."""
    validated: list[str] = []
    for entry in entries:
        result = validate_evidence(entry)
        if result.is_err:
            return Err(result.danger_err)
        validated.append(result.danger_ok)
    return Ok(tuple(validated))


# Blocker resolution needs archived tickets too (a blocker archived after
# `done` must still read as closed, not unknown/open) -- the ticket being
# transitioned itself is always still in the active store (archived
# tickets are done/dropped, terminal, so a lookup that only ever finds one
# there fails the state machine correctly, T-0096).
def _load_ticket_and_queue(
    root: Path, ticket_id: str
) -> Result[tuple[Ticket, dict[str, Ticket]], TicketError]:
    """Load the merged active+archive queue and look up `ticket_id` in it."""
    loaded = _load_merged(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    queue = loaded.danger_ok
    ticket = queue.get(ticket_id)
    if ticket is None:
        _log.warning("tickets: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)
    return Ok((ticket, queue))


__all__ = [
    "AcceptanceAmendmentEntry",
    "AcceptanceAmendmentOp",
    "AcceptanceCriterion",
    "Attachment",
    "AttachError",
    "AttachmentSource",
    "BOARD_STATES",
    "BoardColumn",
    "ClipboardError",
    "DoneReportClaims",
    "EpicRollup",
    "FailureEntry",
    "LandError",
    "LandPlanReport",
    "LandReport",
    "Origin",
    "PRIORITY_RANK",
    "Priority",
    "QueueEntry",
    "QueueError",
    "ReviewEntry",
    "ReviewVerdict",
    "ScopeChangeEntry",
    "ScopeChangeOp",
    "SprintReport",
    "SprintTransition",
    "SprintVelocityReport",
    "Ticket",
    "TicketError",
    "TicketFlowReport",
    "TicketFlowRow",
    "TicketKind",
    "TicketQueue",
    "TicketSpec",
    "TicketState",
    "TicketTier",
    "add_acceptance",
    "add_cmd_evidence",
    "add_evidence",
    "already_landed_markers",
    "amend_acceptance",
    "archive",
    "attach",
    "base_ref_resolvable",
    "clipboard_has_image",
    "compose_done_report",
    "compute_changed_lines",
    "dispatch_stale_hours",
    "display_state",
    "doable",
    "doable_blocked",
    "drain_next",
    "drop_ticket",
    "enqueue",
    "has_approved_review_for_commit",
    "has_live_lease",
    "is_cmd_evidence",
    "is_valid_ticket_ref",
    "land",
    "land_plan",
    "large_glob_warnings",
    "leased_by",
    "ledger_lock",
    "load_active",
    "load_queue",
    "load_require_review_for_close",
    "mutate_labels",
    "mutate_scope",
    "queue_status",
    "remove_acceptance",
    "set_component",
    "set_designated_repro_test",
    "set_kind",
    "set_priority",
    "set_runs_last",
    "set_scope_breadth_ack",
    "set_sprint",
    "set_tier",
    "sprint_velocity",
    "sprint_view",
    "ticket_flow",
    "Stride",
    "board_view",
    "brief_cluster",
    "brief_ticket",
    "epic_rollup",
    "finalize_draft",
    "finalize_draft_for_land",
    "migrate",
    "new_ticket",
    "renumber",
    "renumber_one",
    "record_failure",
    "record_review",
    "reconcile",
    "ReconcileReport",
    "parse_claims_from_done_report",
    "recover_done_report_why",
    "render_changed_block",
    "render_claims_block",
    "render_evidence_block",
    "replace_evidence",
    "replay_evidence_from_done_report",
    "reverify_close_guard",
    "reverify_cmd_evidence",
    "run_cmd_evidence",
    "scope_breadth_context",
    "scope_matches",
    "scope_overlap_globs",
    "set_done_report",
    "splice_ledger",
    "transition",
    "unbound_acceptance",
    "undispatched_stale",
    "validate_evidence",
    "LeaseError",
    "is_lease_ttl_expired",
    "lease_age_seconds",
    "leases_dir",
    "read_all_leases",
    "resolve_lease",
    "sweep_worktrees",
    "warn_if_worktree_stale",
    "ConfirmatoryFinding",
    "MutationEvidenceError",
    "check_ticket_mutation_evidence",
    "agent_env_exports",
]

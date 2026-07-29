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
# frob:waive INV006 reason="the T-1152 evidence-family split moved this file's only \
# frob:invariant INV-002 anchor (transition's docstring) out to \
# src/frob/tickets/_evidence.py, leaving the remaining 'only' claims here \
# (docstrings/comments describing already-implemented internal behavior, e.g. \
# _load_ticket_and_queue's archive-lookup fallback, add_acceptance's append-only \
# semantics) unanchored -- same T-0585 INV006 first-turn-on calibration-batch \
# disposition already applied to every sibling split module (_setters.py, \
# _doable.py, _evidence.py itself), not a newly-introduced normative claim"

from __future__ import annotations

import hashlib
import re
import subprocess  # noqa: F401 -- re-exported: tests/test_tickets_cmd_evidence.py's

# TestRunCmdEvidenceLaunchFailure monkeypatches `tickets_mod.subprocess.run`
# (the PACKAGE attribute, predating the T-1152 evidence-family split) to
# simulate an OSError on launch -- `subprocess` is one shared module object
# process-wide, so this binding only needs to exist here for the patch to
# reach `_evidence._run_evidence_command`'s own `guarded_subprocess_run`
# call, which shells out through the SAME `subprocess` module.
import tomllib
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
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
from frob.tickets._evidence import (
    _check_evidence_resolution,  # noqa: F401 -- re-exported: `_new_renumber.new_ticket`'s
    # own late `from frob.tickets import _check_evidence_resolution` (T-1103's
    # documented load-time-circular-import workaround) resolves against this
    # package attribute; not referenced by name elsewhere in this module.
    add_cmd_evidence,
    add_evidence,
    base_ref_resolvable,
    compute_changed_lines,
    render_changed_block,
    render_evidence_block,
    replay_evidence_from_done_report,
    reverify_close_guard,
    reverify_cmd_evidence,
    run_cmd_evidence,
    transition,
)
from frob.tickets._land import land, splice_ledger
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
    DONE_REPORT_HEADING,
    DROP_REASON_HEADING,
    FAILURE_LOG_HEADING,
    PRIORITY_RANK,
    AcceptanceCriterion,
    Attachment,
    AttachmentSource,
    BoardColumn,
    DoneReportClaims,
    EpicRollup,
    FailureEntry,
    LandError,
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
    replace_done_report_section,
    scope_matches,
    scope_overlap_globs,
    unbound_acceptance,
)
from frob.tickets._models import _split_scope_entries as _normalize_scope_entries
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)
from frob.tickets._new_renumber import (
    finalize_draft,
    new_ticket,
    renumber,
    renumber_one,
)
from frob.tickets._reconcile import ReconcileReport, reconcile
from frob.tickets._scope import mutate_scope
from frob.tickets._setters import (
    set_component,
    set_kind,
    set_priority,
    set_sprint,
    set_tier,
    sprint_velocity,
    sprint_view,
    ticket_flow,
)
from frob.tickets._store import (
    atomic_write,
    attachments_dir,
    ledger_lock,
    load_all,
    slugify,
    tickets_dir,
    write_ticket,
)
from frob.tickets._worktree_guard import agent_env_exports, enforce_worktree_lease
from frob.tickets.clipboard import ClipboardError, clipboard_has_image, clipboard_image

_log = get_logger(__name__)

AttachError = TicketError | ClipboardError

_MAX_WARN_BYTES = 1024 * 1024

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

# frob:ticket T-0579
# `frob ticket drop` writes its dated reason line under this heading instead
# of the hand-edited freeform prose the pre-T-0579 workflow used.
#
# T-0848: these are `frob.tickets._models`'s own `FAILURE_LOG_HEADING` /
# `DROP_REASON_HEADING` re-exported under this module's private naming
# convention, not a second hand-typed copy -- `_models._done_report_
# section_end`'s structural-sentinel set must never drift out of sync with
# the headings this module actually writes.
_FAILURE_LOG_HEADING = FAILURE_LOG_HEADING
_DROP_REASON_HEADING = DROP_REASON_HEADING


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
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_true_when_configured  # noqa: E501
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


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestMutateLabels.test_add_and_remove_labels  # noqa: E501
def mutate_labels(
    root: Path,
    ticket_id: str,
    *,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
) -> Result[Ticket, TicketError]:
    """Add/remove freeform `labels` on `ticket_id` (T-0454) -- orthogonal to
    `scope`'s lease-aware `mutate_scope`: a label is a plain organizational
    tag, never a filesystem glob, so it carries no lease-conflict check and
    no audit trail the way a scope mutation does. `add`/`remove` may be
    combined in one call; each is comma-split the same way `scope`/`labels`
    entries always are (`_split_scope_entries`, T-0241's normalization
    reused here). A no-op call (nothing to add or remove) is an error --
    same "don't call this for nothing" discipline `mutate_scope` enforces."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    add_labels = _normalize_scope_entries(tuple(add))
    remove_labels = _normalize_scope_entries(tuple(remove))
    if not add_labels and not remove_labels:
        return Err(TicketError.LabelChangeEmpty)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        new_labels = tuple(lbl for lbl in ticket.labels if lbl not in remove_labels)
        for label in add_labels:
            if label not in new_labels:
                new_labels += (label,)
        updated = ticket.model_copy(update={"labels": new_labels})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s labels changed (+%d/-%d), now %s",
        ticket_id,
        len(add_labels),
        len(remove_labels),
        list(updated.labels),
    )
    return Ok(updated)


# frob:ticket T-1029
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets.py::TestAddAcceptance.test_appends_criteria_to_existing_ticket  # noqa: E501
# frob:tests tests/test_tickets.py::TestAddAcceptance.test_empty_criteria_is_rejected  # noqa: E501
# frob:tests tests/test_tickets.py::TestAddAcceptance.test_blank_criteria_are_dropped  # noqa: E501
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
# frob:tests tests/test_tickets_organization.py::TestBoardView.test_columns_in_fixed_order  # noqa: E501
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
    # frob:waive PERF004 reason="one sorted() call per BOARD_STATES entry -- a fixed 6-iteration loop over the queue's own ticket count, not an unbounded hoisted-sort opportunity"  # noqa: E501
    for state in BOARD_STATES:
        in_state = sorted(
            (t for t in tickets if t.state is state), key=_doable_sort_key
        )
        columns.append(BoardColumn(state=state, tickets=tuple(in_state)))
    return tuple(columns)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestEpicRollup.test_counts_done_and_total  # noqa: E501
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
    # frob:waive PERF004 reason="single sorted() call over the finished descendants list, not inside the BFS while-loop above it -- the checker's whole-function loop scan flags it textually, not per-iteration"  # noqa: E501
    return Ok(
        EpicRollup(
            epic=epic,
            descendants=tuple(sorted(descendants, key=lambda t: t.id)),
            done=done,
            total=len(descendants),
            blocked_leaves=blocked_leaves,
        )
    )


# frob:ticket T-0568
# frob:doc docs/modules/tickets.md#frob-ticket-brief-t-0568
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing
def brief_ticket(root: Path, ticket_id: str) -> Result[str, TicketError]:
    """`frob ticket brief <id>` (T-0568): compose the complete agent
    mission briefing text (`frob.tickets._brief.compose_brief`) for
    `ticket_id` -- replacing the ~400 words of hand-typed dispatch
    boilerplate a coordinator otherwise repeats per ticket. `Err(NotFound)`
    if `ticket_id` does not resolve."""
    from frob.tickets._brief import compose_brief

    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    queue_result = load_queue(root)
    holders: tuple[tuple[str, str], ...] = ()
    if queue_result.is_ok:
        holders = leased_by(queue_result.danger_ok, ticket, root)

    return Ok(compose_brief(root, ticket, holders))


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


# frob:ticket T-0102
# frob:doc docs/modules/tickets.md#public-api
def validate_evidence(entry: str) -> Result[str, TicketError]:
    """One evidence string's schema: non-empty, single-line, bounded length.

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
    """
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


_LEADING_DONE_REPORT_HEADING_RE = re.compile(
    r"\A(?:[ \t]*\n)*[ \t]*#{1,6}[ \t]+done report[ \t]*\n?", re.IGNORECASE
)


# frob:ticket T-0826
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def _strip_leading_done_report_heading(why: str) -> str:
    """Strip a leading '## Done report' (any `#` level, any case, optional
    leading blank lines) heading line from `why` (T-0826): `compose_done_
    report` always prepends its own canonical `DONE_REPORT_HEADING`, so a
    caller-supplied `why` (typically `--why-file` content an agent already
    wrote with its own heading) that starts with one too would otherwise
    render TWO headings back to back -- a recurring cosmetic ledger-noise
    finding reviewers kept re-flagging. Only a LEADING heading is
    stripped -- one appearing later in the narrative body is left alone,
    since it is not a duplicate of the one this function's caller is about
    to prepend."""
    return _LEADING_DONE_REPORT_HEADING_RE.sub("", why, count=1)


# frob:ticket T-0458
# frob:ticket T-0826
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_composes_all_three_sections  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def compose_done_report(
    why: str,
    changed_lines: Sequence[str],
    evidence: Sequence[str],
    claims: DoneReportClaims | None = None,
) -> str:
    """Compose a full '## Done report' section: the caller's narrative
    `why` plus AUTO-FILLED Changed (`render_changed_block`), Evidence
    (`render_evidence_block`), and (T-0754, when `claims` is given) Captured
    claims (`render_claims_block`) sections -- the mechanical parts are
    always generated, never hand-typed, so they can never drift from what
    frob, git, and a real test/gate run actually observed. `claims=None`
    (the default) omits the Captured claims section entirely, matching
    every caller before T-0754.

    T-0826: if `why` itself already begins with a '## Done report' heading
    (case-insensitive, possibly preceded by blank lines -- e.g. an agent's
    `--why-file` content that already carries its own heading, a recurring
    cosmetic ledger noise reviewers kept flagging), that leading heading
    line is stripped BEFORE composing so the rendered block always has
    exactly one heading, never two."""
    why_text = _strip_leading_done_report_heading(why).strip() or (
        "(no narrative supplied)"
    )
    changed_block = render_changed_block(changed_lines)
    evidence_block = render_evidence_block(evidence)
    claims_section = f"\n\n{render_claims_block(claims)}" if claims is not None else ""
    return (
        f"{DONE_REPORT_HEADING}\n\n"
        f"{why_text}\n\n"
        f"### Changed\n{changed_block}\n\n"
        f"### Evidence\n{evidence_block}{claims_section}\n"
    )


# frob:ticket T-0976
def _capture_done_report_claims(
    ticket_id: str,
    ticket: Ticket,
    run_tests: Callable[[Sequence[str]], int] | None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None,
) -> "DoneReportClaims | None":
    """`set_done_report`'s T-0754/T-0832/T-0846 Captured-claims computation,
    split from its load-compose-write body: `None` unless BOTH `run_tests`
    and `check_gates` were supplied, else a `DoneReportClaims` with gate
    counts recorded as unmeasured (`None`, never a `-1` sentinel, T-0832)
    when `check_gates()` itself returns `None`."""
    if run_tests is None or check_gates is None:
        return None
    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    gate_result = check_gates()
    if gate_result is None:
        # T-0832: never embed a -1 sentinel -- record the gate half of the
        # claim as explicitly unmeasured instead.
        _log.warning(
            "ticket %s: fresh `frob check --ticket %s` produced no "
            "parsable gate-summary -- recording the Captured "
            "claims gate-state as unmeasured (the test-count claim "
            "is unaffected)",
            ticket_id,
            ticket_id,
        )
        gate_errors = gate_warnings = gate_waived = None
    else:
        gate_errors, gate_warnings, gate_waived = gate_result
    error_findings = check_gate_findings() if check_gate_findings is not None else None
    return DoneReportClaims(
        test_count=run_tests(non_cmd),
        evidence_count=len(non_cmd),
        gate_errors=gate_errors,
        gate_warnings=gate_warnings,
        gate_waived=gate_waived,
        error_findings=error_findings,
    )


# frob:ticket T-0458
# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_composes_and_writes_atomically  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_caller_never_touches_markdown  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_claims_captured_from_real_callables  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity kind="integration"  # noqa: E501
def set_done_report(
    root: Path,
    ticket_id: str,
    *,
    why: str,
    base_ref: str = "main",
    run_tests: Callable[[Sequence[str]], int] | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
) -> Result[Ticket, TicketError]:
    """THE single write path for a ticket's Done report (T-0458): compose
    `why` (the caller's narrative -- the ONLY thing the caller supplies)
    with auto-filled Changed (`compute_changed_lines` vs `base_ref`) and
    Evidence (`render_evidence_block`, from the ticket's own recorded
    evidence) sections, then splice the result into `body`'s '## Done
    report' section via `replace_done_report_section` -- the caller never
    parses or edits markdown directly, and never re-derives block
    boundaries by hand (the exact failure mode -- a dropped marker, a
    mis-listed Changed/Evidence block, an Edit landing mid-section -- that
    repeatedly corrupted `tickets.md` when done by hand).

    T-0754: when BOTH `run_tests` and `check_gates` are supplied, this also
    CAPTURES (never lets the caller type) a `### Captured claims` section:
    `run_tests(non_cmd_evidence_ids)` actually runs the ticket's own
    recorded non-cmd evidence and returns the real passing count, and
    `check_gates()` runs a fresh `frob check --ticket` and returns its
    `(errors, warnings, waived)` COUNTS -- deliberately not that run's
    free-text summary line, whose per-gate timing blob is nondeterministic
    even against an unchanged tree (T-0754 review round 2's FATAL fix) --
    both rendered via `render_claims_block` into the same Done report
    `set_done_report` already writes, and later re-verified against the
    post-merge tree by `frob.tickets._land`'s
    `_reverify_done_report_claims_post_merge` (T-0754's land-side half).
    Either or both omitted (the default, `None`) skips the Captured claims
    section entirely -- unchanged behavior for every caller before T-0754,
    since computing either needs `frob.testing`/`frob.gates`/subprocess
    access `frob.tickets` deliberately does not have (docs/rework.md
    cycle-avoidance); the `frob ticket done-report` CLI supplies both by
    default (see `ticket_runner.py`'s `_done_report`).

    T-0832: `check_gates()` returning `None` means the fresh `frob check
    --ticket` it ran produced no parsable gate-summary (no lease, a crash,
    unparsable output) -- this is recorded as an UNMEASURED gate-state
    claim (`DoneReportClaims.gate_errors=None`, etc.), logged as a
    warning, and rendered via the explicit `unmeasured` marker
    (`render_claims_block`), never as a `-1` sentinel. A `-1` sentinel
    written here previously could later compare equal to another `-1`
    land observed post-merge, passing a re-verification that had actually
    measured nothing on either side (the T-0830 incident). The test-count
    half of the claim is unaffected -- `run_tests` always returns a real
    measured count whenever it runs at all.

    T-0846: `check_gate_findings()` (opt-in, additional to `check_gates`)
    returns a `frozenset[(rule_id, file)]` of the SAME fresh check's error
    findings -- captured alongside the plain count so `land`'s
    re-verification can compare identities (rule id + file) rather than a
    scope-wide total. A count-only comparison let a land whose own diff
    introduced N new errors sail through whenever an unrelated fix on the
    same branch removed more than N (a self-introduced regression
    laundered by a net-better total) -- the gap the count-only T-0846 `>`
    fix left open. `check_gate_findings=None` (the default) records no
    identity set (`DoneReportClaims.error_findings=None`), matching every
    caller before this addition; `_reverify_done_report_claims_post_merge`
    falls back to the count-only comparison whenever either side of the
    claim lacks an identity set.

    T-0887: `base_ref` is validated (`base_ref_resolvable`) BEFORE any
    other work -- an unresolvable ref (in a real git checkout) returns
    `Err(TicketError.BaseRefUnresolvable)` immediately rather than being
    discovered minutes later via a silently-empty diff or a downstream
    `frob check` spawn. T-0887 also moves the (potentially slow, up to
    two 600s `frob check --ticket` subprocess spawns via `check_gates`/
    `check_gate_findings`) claims capture OUTSIDE the `ledger_lock` --
    those are read-only and do not need the single-writer lock at all;
    holding the lock across them used to serialize every OTHER concurrent
    ticket mutation on this ledger behind up to ~20 minutes of subprocess
    spawns (the observed "hangs under concurrent tickets.md lock
    contention" symptom class). Only the final load-compose-write is now
    held under `ledger_lock` end to end, so a concurrent `set_done_
    report`/`add_evidence`/`new_ticket` call on the same ledger still can
    never interleave with THAT part (T-0458 single-writer invariant) --
    the narrow tradeoff is that `ticket.evidence` used to compute the
    non-cmd id list fed to `run_tests`/claims is read once, before the
    lock, and could in principle be stale if evidence changes
    concurrently between that read and the final write; the Evidence
    section itself is always rendered from the freshly-reloaded ticket
    inside the lock, so the written report's Evidence block can never be
    stale, only (rarely) the Captured claims' `evidence_count`."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)

    resolvable = base_ref_resolvable(root, base_ref)
    if resolvable is False:
        _log.error(
            "ticket %s: done-report --base-ref %r does not resolve to a "
            "commit in this clone -- fetch it or pass a base ref that "
            "exists",
            ticket_id,
            base_ref,
        )
        return Err(TicketError.BaseRefUnresolvable)

    preloaded = _load_one(root, ticket_id)
    if preloaded.is_err:
        return Err(preloaded.danger_err)
    changed_lines = compute_changed_lines(root, base_ref)
    claims = _capture_done_report_claims(
        ticket_id, preloaded.danger_ok, run_tests, check_gates, check_gate_findings
    )

    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        report = compose_done_report(why, changed_lines, ticket.evidence, claims)
        updated = ticket.model_copy(
            update={"body": replace_done_report_section(ticket.body, report)}
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s Done report set (%d evidence id(s), %d changed line(s)%s)",
        ticket_id,
        len(ticket.evidence),
        len(changed_lines),
        f", claims={claims.test_count}/{claims.evidence_count} tests"
        if claims is not None
        else "",
    )
    return Ok(updated)


# frob:doc docs/modules/tickets.md#public-api
def record_failure(
    root: Path, ticket_id: str, entry: FailureEntry
) -> Result[Ticket, TicketError]:
    """Append entry to the '## Failure log' body section, creating it if absent."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {entry.date.isoformat()} attempt {entry.attempt}: {entry.summary}"
    new_body = _append_to_section(ticket.body, _FAILURE_LOG_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s recorded failure attempt %d", ticket_id, entry.attempt)
    return Ok(updated)


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:waive COV007 reason="docs/modules/tickets.md#public-api individually names \
# _resolve_review_commit by name (T-0529 precedent: a deliberate architecture-doc \
# callout of the never-store-abbreviated-SHA security behavior, not accidental drift \
# onto a private helper)"
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_unresolvable_commit_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_short_sha_normalized_to_full_sha  # noqa: E501
def _resolve_review_commit(root: Path, commit: str) -> Result[str, TicketError]:
    """Resolve `commit` (a short SHA, ref name, `HEAD`, ...) to its full
    40-char SHA via `git rev-parse` under `root` (T-0571 review round 2):
    `record_review` must NEVER store a caller-supplied commit verbatim --
    `has_approved_review_for_commit` does a plain string-equality
    comparison against a full `rev-parse HEAD` sha, so an abbreviated
    value (e.g. copied from `git log --oneline`) would silently never
    match and make `close --strict` permanently unsatisfiable for that
    review. `Err(ReviewCommitUnresolvable)` on any git failure (unknown
    ref, not a git repo, ...) -- an unresolvable input is never stored
    raw."""
    from frob.gitio import run_argv

    resolved = run_argv(["git", "-C", str(root), "rev-parse", commit])
    if (
        resolved.is_err
        or resolved.danger_ok.returncode != 0
        or not resolved.danger_ok.stdout.strip()
    ):
        _log.warning(
            "tickets: review --commit %r did not resolve under %s", commit, root
        )
        return Err(TicketError.ReviewCommitUnresolvable)
    return Ok(resolved.danger_ok.stdout.strip())


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#structured-review-channel-t-0571
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_appends_approve_entry  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_blank_findings_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_multiple_reviews_append_only  # noqa: E501
def record_review(
    root: Path,
    ticket_id: str,
    *,
    verdict: ReviewVerdict,
    reviewer: str,
    findings: str,
    commit: str,
) -> Result[Ticket, TicketError]:
    """Append a structured `ReviewEntry` to `ticket_id`'s append-only
    `reviews` list (T-0571) -- the first-class evidence channel for
    adversarial review, replacing a verdict pasted only into dispatch
    chat. `Err(ReviewFindingsMissing)` if `findings` is blank: a review
    record with no findings text is indistinguishable from one nobody
    actually read. `commit` is normalized to its full SHA via
    `_resolve_review_commit` before storage (T-0571 review round 2):
    `Err(ReviewCommitUnresolvable)` if it does not resolve, rather than
    storing an abbreviated/unnormalized value that could never satisfy
    `close --strict`'s exact-match comparison later. Never validates
    `verdict` against the ticket's own state beyond schema -- `close
    --strict` is what decides whether a given review record actually
    satisfies the gate."""
    if not findings.strip():
        return Err(TicketError.ReviewFindingsMissing)
    resolved_commit = _resolve_review_commit(root, commit)
    if resolved_commit.is_err:
        return Err(resolved_commit.danger_err)
    commit = resolved_commit.danger_ok
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    entry = ReviewEntry(
        verdict=verdict,
        reviewer=reviewer,
        findings=findings.strip(),
        commit=commit,
        at=date.today(),
    )
    updated = ticket.model_copy(update={"reviews": ticket.reviews + (entry,)})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s recorded review verdict=%s reviewer=%s commit=%s",
        ticket_id,
        verdict.value,
        reviewer,
        commit,
    )
    return Ok(updated)


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestHasApprovedReviewForCommit.test_true_only_for_matching_approve  # noqa: E501
def has_approved_review_for_commit(ticket: Ticket, commit: str) -> bool:
    """Whether `ticket` carries at least one `verdict: approve` review
    record naming exactly `commit` (T-0571) -- the predicate `close
    --strict` gates on. A ticket with zero review records, or reviews that
    only name earlier commits (the code moved since the last review), both
    return `False`: a stale approval is not an approval of the CURRENT
    final commit."""
    return any(
        r.verdict == ReviewVerdict.APPROVE and r.commit == commit
        for r in ticket.reviews
    )


# frob:ticket T-0579
# frob:doc docs/modules/tickets.md#public-api
def drop_ticket(
    root: Path, ticket_id: str, reason: str, *, absorbed_by: str | None = None
) -> Result[Ticket, TicketError]:
    """First-class `frob ticket drop` (T-0579): append a dated reason line
    under '## Drop reason' (creating the section if absent, same pattern as
    `record_failure`'s '## Failure log'), then transition to DROPPED through
    the normal state machine so a held worktree lease is released the same
    way any other terminal transition releases one
    (`_sync_cross_worktree_lease`) -- this replaces the pre-T-0579 workflow
    of hand-editing `state: dropped` directly, which left leases dangling
    and never recorded why. `Err(DropReasonMissing)` if `reason` is blank:
    a drop with no reason is indistinguishable from a silent discard later.
    `absorbed_by` (a ticket id) is appended parenthetically to the line when
    given, but is NOT validated against the queue -- it is a cross-reference
    note, not a `blocked_by`-style edge."""
    if not reason.strip():
        return Err(TicketError.DropReasonMissing)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {date.today().isoformat()}: {reason.strip()}"
    if absorbed_by:
        line += f" (absorbed by {absorbed_by})"
    new_body = _append_to_section(ticket.body, _DROP_REASON_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)

    transitioned = transition(root, ticket_id, TicketState.DROPPED)
    if transitioned.is_err:
        _log.error(
            "tickets: %s drop reason recorded but transition failed: %s",
            ticket_id,
            transitioned.danger_err,
        )
        return Err(transitioned.danger_err)
    _log.info("tickets: %s dropped: %s", ticket_id, reason.strip())
    return transitioned


def _append_to_section(body: str, heading: str, line: str) -> str:
    """Append `line` under `heading` in body; create the section at the end if gone."""
    lines = body.splitlines()
    for i, text in enumerate(lines):
        if text.strip() != heading:
            continue
        insert_at = i + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        while insert_at > i + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, line)
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")
    separator = (
        ""
        if not body or body.endswith("\n\n")
        else ("\n" if body.endswith("\n") else "\n\n")
    )
    return f"{body}{separator}{heading}\n{line}\n"


def _attachment_bytes(
    ticket_id: str, source: AttachmentSource
) -> Result[tuple[bytes, str], AttachError]:
    """Read attachment `(data, suffix)` from the clipboard or `source.path`."""
    if source.path is None:
        _log.debug("tickets: attach %s from clipboard", ticket_id)
        image_result = clipboard_image()
        if image_result.is_err:
            return Err(image_result.danger_err)
        return Ok((image_result.danger_ok, ".png"))
    _log.debug("tickets: attach %s from %s", ticket_id, source.path)
    try:
        data = source.path.read_bytes()
    except OSError as exc:
        _log.error("tickets: failed to read attachment source %s: %s", source.path, exc)
        return Err(TicketError.WriteFailed)
    return Ok((data, source.path.suffix or ".png"))


# frob:doc docs/modules/tickets.md#public-api
def attach(
    root: Path, ticket_id: str, source: AttachmentSource, caption: str
) -> Result[Attachment, AttachError]:
    """Copy a file (or clipboard image) into tickets/attachments/<id>/ and record it."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    bytes_result = _attachment_bytes(ticket_id, source)
    if bytes_result.is_err:
        return Err(bytes_result.danger_err)
    data, suffix = bytes_result.danger_ok

    if len(data) > _MAX_WARN_BYTES:
        _log.warning(
            "tickets: attachment for %s is %d bytes (>1MB)", ticket_id, len(data)
        )

    sha256 = hashlib.sha256(data).hexdigest()
    dest_path = _next_attachment_path(root, ticket_id, caption, suffix)

    write_result = atomic_write(dest_path, data)
    if write_result.is_err:
        return Err(write_result.danger_err)

    return _record_attachment(root, ticket, dest_path, caption, sha256)


def _next_attachment_path(
    root: Path, ticket_id: str, caption: str, suffix: str
) -> Path:
    """The next `NN-slug.ext` attachment path under the ticket's attachment dir."""
    dest_dir = attachments_dir(root, ticket_id)
    existing = sorted(dest_dir.glob("[0-9][0-9]-*")) if dest_dir.exists() else []
    next_index = len(existing) + 1
    return dest_dir / f"{next_index:02d}-{slugify(caption)}{suffix}"


def _record_attachment(
    root: Path, ticket: Ticket, dest_path: Path, caption: str, sha256: str
) -> Result[Attachment, AttachError]:
    """Append the written attachment to `ticket` and persist the ticket."""
    rel_path = str(dest_path.relative_to(tickets_dir(root)))
    attachment = Attachment(path=rel_path, caption=caption, sha256=sha256)
    updated = ticket.model_copy(
        update={"attachments": ticket.attachments + (attachment,)}
    )
    frontmatter_write = write_ticket(root, updated)
    if frontmatter_write.is_err:
        return Err(frontmatter_write.danger_err)
    _log.info(
        "tickets: attached %s to %s (sha256=%s)", dest_path.name, ticket.id, sha256
    )
    return Ok(attachment)


__all__ = [
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
    "LandReport",
    "Origin",
    "PRIORITY_RANK",
    "Priority",
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
    "drop_ticket",
    "has_approved_review_for_commit",
    "has_live_lease",
    "is_cmd_evidence",
    "is_valid_ticket_ref",
    "land",
    "large_glob_warnings",
    "leased_by",
    "ledger_lock",
    "load_active",
    "load_queue",
    "load_require_review_for_close",
    "mutate_labels",
    "mutate_scope",
    "set_component",
    "set_kind",
    "set_priority",
    "set_sprint",
    "set_tier",
    "sprint_velocity",
    "sprint_view",
    "ticket_flow",
    "Stride",
    "board_view",
    "brief_ticket",
    "epic_rollup",
    "finalize_draft",
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

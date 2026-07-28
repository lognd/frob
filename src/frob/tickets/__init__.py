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

import fnmatch
import getpass
import hashlib
import re
import shlex
import subprocess
import tomllib
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.excludes import is_test_file
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.tickets._archive import (
    _load_merged,
    archive,
    load_active,
    load_queue,
    migrate,
)
from frob.tickets._doable import (
    _over_broad_scope_entries,
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
from frob.tickets._live_tracker import live_tracker_citations
from frob.tickets._models import (
    BOARD_STATES,
    CMD_EVIDENCE_ALLOWED_KINDS,
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
    _done_report_section_lines,
    _glob_is_subset,
    has_substantive_done_report,
    is_cmd_evidence,
    is_valid_ticket_ref,
    matches_collected,
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
from frob.tickets._new_gate_rule_acceptance import (
    missing_acceptance_for_new_rules,
    new_gate_rule_ids,
)
from frob.tickets._new_renumber import (
    finalize_draft,
    new_ticket,
    renumber,
    renumber_one,
)
from frob.tickets._reconcile import ReconcileReport, reconcile
from frob.tickets._scope import mutate_scope
from frob.tickets._store import (
    atomic_write,
    attachments_dir,
    ledger_lock,
    load_all,
    load_archive,
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
# frob:doc docs/modules/tickets.md#public-api
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


def _set_ticket_field(
    root: Path, ticket_id: str, field: str, value: object, *, log_value: object
) -> Result[Ticket, TicketError]:
    """Set one `field` on `ticket_id` to `value` (extracted T-0861): the
    ONE lease-check + ledger-locked-load + `model_copy(update=...)` +
    write + log shape `set_priority`/`set_kind`/`set_sprint`/
    `set_component` each need for their own single-field setter, so the
    accountable single-writer discipline can never desync between fields.
    `log_value` lets a caller log an enum's `.value` instead of the enum
    repr where that reads better; the field name itself is embedded in
    the log line by the caller via `field`."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(update={field: value})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s %s set to %s", ticket_id, field, log_value)
    return Ok(updated)


# frob:ticket T-0411
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_priority.py::TestSetPriority.test_updates_priority_field
def set_priority(
    root: Path, ticket_id: str, priority: Priority
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `priority` field (T-0411) -- the accountable,
    single-writer way to reprioritize a ticket instead of hand-editing
    `tickets.md` frontmatter. Held under `ledger_lock` (same discipline as
    `mutate_scope`) so this can never interleave with a concurrent ledger
    mutation. A no-op write (still logged) if `priority` already matches."""
    return _set_ticket_field(
        root, ticket_id, "priority", priority, log_value=priority.value
    )


# frob:ticket T-0834
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_evidence.py::TestSetKind.test_updates_kind_field
def set_kind(
    root: Path, ticket_id: str, kind: TicketKind
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `kind` field (T-0834) -- the accountable,
    single-writer way to correct a mis-filed kind instead of hand-editing
    `tickets.md` frontmatter, same ledger-locked, no-terminal-state-check
    pattern `set_priority` uses. A no-op write (still logged) if `kind`
    already matches."""
    return _set_ticket_field(root, ticket_id, "kind", kind, log_value=kind.value)


# frob:ticket T-1069
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSetTier.test_updates_tier_field
def set_tier(
    root: Path, ticket_id: str, tier: TicketTier
) -> Result[Ticket, TicketError]:
    """`frob ticket tier <id> <epic|story|ticket>`: set `ticket_id`'s `tier`
    field (T-1069) -- the accountable, single-writer way to reclassify an
    already-created ticket's place in the epic -> story -> ticket hierarchy
    instead of hand-editing `tickets.md` frontmatter, same ledger-locked
    `_set_ticket_field` pattern `set_priority`/`set_kind`/`set_component`/
    `set_sprint` all share. This changes only the `tier` label itself --
    T-0715's structural rules (`doable`'s leaf-only surfacing, `transition`'s
    open-descendant close guard) key off whatever `tier` a ticket currently
    carries, so they apply to the new value on the very next read; this
    function does not re-validate or move `parent` links."""
    return _set_ticket_field(root, ticket_id, "tier", tier, log_value=tier.value)


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintAssign.test_updates_sprint_field
def set_sprint(
    root: Path, ticket_id: str, sprint: str | None
) -> Result[Ticket, TicketError]:
    """`frob ticket sprint assign <id> <label>`: set `ticket_id`'s `sprint`
    field (T-0715) -- the same single-writer, ledger-locked pattern
    `set_component` uses. `sprint=None` clears it back to uncommitted/
    backlog."""
    return _set_ticket_field(root, ticket_id, "sprint", sprint, log_value=sprint)


# frob:ticket T-0938
def _tickets_committed_to(queue: TicketQueue, sprint: str) -> tuple[Ticket, ...]:
    """Every ticket in `queue` carrying `sprint` as its `Ticket.sprint`
    label, id-sorted -- the shared "who's committed to this sprint"
    lookup both `sprint_view` (T-0715, a current-state rollup) and
    `sprint_velocity` (T-0938, a history-mined rollup) start from,
    extracted to keep the two in lock-step rather than drifting two
    copies of the same filter/sort (DUP001)."""
    return tuple(
        sorted(
            (t for t in queue.tickets.values() if t.sprint == sprint),
            key=lambda t: t.id,
        )
    )


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintShow.test_state_rollup_and_velocity
def sprint_view(queue: TicketQueue, sprint: str) -> SprintReport:
    """`frob ticket sprint show <label>`: every ticket committed to
    `sprint` (T-0715), a `TicketState -> count` rollup, and `closed`
    (done-count, the mandate's "closed-count velocity" -- derived from
    current ledger state, not a separate tracked counter). Always returns
    a report, even when no ticket carries this sprint label (`tickets`
    empty, every rollup count zero) -- there is no NotFound case, a sprint
    label is a free-form tag, not an id that must resolve."""
    tickets = _tickets_committed_to(queue, sprint)
    rollup: dict[TicketState, int] = {}
    for t in tickets:
        rollup[t.state] = rollup.get(t.state, 0) + 1
    closed = rollup.get(TicketState.DONE, 0)
    return SprintReport(sprint=sprint, tickets=tickets, rollup=rollup, closed=closed)


_STATE_LINE_RE = re.compile(r"(?m)^state:\s*(\S+)\s*$")


# frob:ticket T-0938
def _ticket_state_in_blob(text: str, ticket_id: str) -> str | None:
    """Read `ticket_id`'s `state:` value out of a full `tickets.md` blob
    (any revision's text, not necessarily the working tree's), by slicing
    the text between this ticket's `<!-- ticket:ID -->` anchor and the
    next one -- the same anchor `_store._LEDGER_MARKER_RE` splits sections
    on. Returns `None` if the anchor is absent from this revision (the
    ticket did not exist yet) or its block has no `state:` line (never
    happens in a well-formed ledger, but a malformed/mid-conflict blob
    must not raise)."""
    anchor = f"<!-- ticket:{ticket_id} -->"
    start = text.find(anchor)
    if start == -1:
        return None
    next_start = text.find("<!-- ticket:", start + len(anchor))
    block = text[start : next_start if next_start != -1 else len(text)]
    match = _STATE_LINE_RE.search(block)
    return match.group(1) if match else None


# frob:ticket T-0938
def _ledger_commit_history(root: Path) -> tuple[tuple[str, str], ...]:
    """Every commit that ever touched `tickets.md` in `root`'s clone,
    oldest-first, as `(sha, author-date-iso)` pairs (`git log --reverse
    --format=%H%x1f%aI -- tickets.md`) -- fetched ONCE per
    `sprint_velocity` call and re-used across every ticket in the sprint,
    since the ledger is one shared file and a per-ticket `git log` call
    would re-walk the same commit list once per ticket for no reason.
    Returns an empty tuple (never raises) if `root` is not a git
    checkout, `tickets.md` has no history yet, or the `git` call fails --
    a caller must treat that the same as "no history observed", matching
    `compute_changed_lines`'s existing best-effort git contract in this
    module."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "--format=%H%x1f%aI",
            "--",
            "tickets.md",
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return ()
    commits: list[tuple[str, str]] = []
    for line in spawned.danger_ok.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, iso = line.partition("\x1f")
        if sha and iso:
            commits.append((sha, iso))
    return tuple(commits)


# frob:ticket T-0938
def _blob_at(root: Path, sha: str) -> str | None:
    """`tickets.md`'s full text at commit `sha` (`git show
    <sha>:tickets.md`), or `None` if that revision can't be read (an
    unresolvable sha, a `git` failure) -- caller treats `None` the same
    as "this revision has no readable ticket state"."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "show", f"{sha}:tickets.md"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout


# frob:ticket T-0938
def _mine_done_transitions(
    root: Path, ticket_ids: Sequence[str]
) -> tuple[SprintTransition, ...]:
    """Mine every `state: done` transition each id in `ticket_ids` has
    ever made in `tickets.md`'s git history (T-0938's derivation source
    -- see `sprint_velocity`'s docstring for the honest tradeoffs of this
    approach): walk `_ledger_commit_history` oldest-first, reading each
    commit's `tickets.md` blob ONCE (`_blob_at`) and checking every
    tracked id's `state:` value against that one blob -- a `done` value
    that differs from the id's previous observed state is a transition.
    A `git log -G<anchor>` pickaxe restriction was tried first and
    rejected: the `<!-- ticket:ID -->` anchor line itself never changes
    across a state edit (only the `state:` line inside its block does),
    so `-G` on the anchor structurally misses every transition after the
    ticket's own creation commit -- a full walk is the only correct
    approach here, not an optimization left undone."""
    if not ticket_ids:
        return ()
    transitions: list[SprintTransition] = []
    prev_state: dict[str, str | None] = dict.fromkeys(ticket_ids)
    for sha, iso in _ledger_commit_history(root):
        blob = _blob_at(root, sha)
        if blob is None:
            continue
        for ticket_id in ticket_ids:
            state = _ticket_state_in_blob(blob, ticket_id)
            if state is None:
                continue
            if state == TicketState.DONE.value and state != prev_state[ticket_id]:
                try:
                    committed_at = datetime.fromisoformat(iso)
                except ValueError:
                    prev_state[ticket_id] = state
                    continue
                transitions.append(
                    SprintTransition(
                        ticket_id=ticket_id,
                        sha=sha,
                        committed_at=committed_at,
                        from_state=prev_state[ticket_id],
                        to_state=state,
                    )
                )
            prev_state[ticket_id] = state
    return tuple(transitions)


# frob:ticket T-0938
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_velocity.py::TestSprintVelocity.test_transitions_mined_from_history  # noqa: E501
def sprint_velocity(
    root: Path, queue: TicketQueue, sprint: str
) -> SprintVelocityReport:
    """`frob ticket sprint velocity <label>` (T-0938): history-derived
    burndown/velocity for every ticket currently committed to `sprint`.

    Derivation source, decided honestly per this ticket's acceptance
    criterion: `tickets.md` carries no transition-history field of its
    own (only each ticket's CURRENT `state`, same as `sprint_view`
    reads) and the "no new storage" mandate rules out adding one. The
    only place a past transition is actually recoverable is git's own
    commit history of `tickets.md` -- so this mines it directly, walking
    every commit that ever touched the ledger (oldest-first) and reading
    each tracked ticket's `state:` field out of that commit's blob, to
    find the specific commits where it flipped INTO `done`. This is
    genuinely history, not a state snapshot -- unlike `sprint_view.
    closed`, `sprint_velocity` sees a ticket that was done and later
    reopened (both transitions appear) and gives each closure a real
    commit + timestamp for a burndown chart's x-axis.

    Known, disclosed gaps (not silently papered over): (1) a ticket's
    CURRENT `sprint` label is used to select which tickets to mine --
    `tickets.md` does not retain sprint-REASSIGNMENT history, so a
    ticket closed under a different sprint label before being
    reassigned will not appear in either sprint's velocity; (2) if
    `tickets.md` was ever squash-merged or hand-edited such that a
    `done` transition never appears as its own commit, that transition
    is invisible to this mining (git history is a lower bound on
    real-world transitions, not a guarantee of completeness) -- both are
    accepted tradeoffs of "no new storage", not bugs.

    Always returns a report, even for a sprint label no ticket carries or
    a `root` with no git history -- same no-NotFound-case contract as
    `sprint_view`."""
    tickets = _tickets_committed_to(queue, sprint)
    transitions = list(_mine_done_transitions(root, tuple(t.id for t in tickets)))
    transitions.sort(key=lambda tr: tr.committed_at)
    closed = len(transitions)
    remaining = sum(1 for t in tickets if t.state != TicketState.DONE)
    return SprintVelocityReport(
        sprint=sprint,
        transitions=tuple(transitions),
        closed=closed,
        remaining=remaining,
        total=len(tickets),
    )


# frob:ticket T-1100
_FLOW_TRAILING_DAYS = 3


# frob:ticket T-1100
# frob:ticket T-1142
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_filed_and_landed_counted_per_day  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_zero_activity_days_are_filled_not_sparse  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_eta_none_when_queue_not_shrinking  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_eta_computed_when_queue_shrinking  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_archived_ticket_still_counts_toward_landed  # noqa: E501
# frob:tests tests/test_tickets_velocity.py::TestTicketFlow.test_archived_ticket_still_counts_toward_filed  # noqa: E501
def ticket_flow(
    root: Path, queue: TicketQueue, *, today: date | None = None
) -> TicketFlowReport:
    """`frob ticket flow` (T-1100): filed/day vs landed/day vs net, plus a
    naive burn-down ETA -- reuses `sprint_velocity`'s T-0938 git-history
    transition mining for the landed side (over the WHOLE queue, not one
    sprint) and each ticket's `created` field for the filed side; no new
    storage, same "no new storage" mandate T-0938 already established.

    T-1142: `queue` alone (whatever the caller passed -- the CLI's own
    `_flow` handler passes `load_active`'s active-only view) UNDERCOUNTS
    both sides for any ticket that has since been archived out of
    `tickets.md` into `tickets-archive.md` by `frob ticket archive`: its
    id is simply absent from `queue.tickets`, so `_mine_done_transitions`
    is never even ASKED to look for its done-transition commit (which
    still exists, readably, in `tickets.md`'s own git history from BEFORE
    the archive-sweep commit removed it -- `_mine_done_transitions`/
    `_ledger_commit_history` walk `tickets.md`'s FULL history, not just
    its current tip, so no separate `tickets-archive.md` mining is even
    needed for the landed side), and its `created` date is missing from
    the filed side the same way. This was T-1100's first real-world run
    (2026-07-28): landed=0 for two days the zero-drive record shows ~50
    lands each, both days followed by an archive sweep. Fixed by merging
    `tickets-archive.md`'s own tickets (`load_archive`, best-effort --
    degrades to `{}` on any load failure rather than blocking the whole
    report) into BOTH the filed-by-day source and the landed-mining id
    set, unconditionally, regardless of what view of the ACTIVE queue the
    caller happened to pass in. `open_count` still only ever counts
    `queue`'s own (active) tickets -- an archived ticket is always
    done/dropped, never a member of `_OPEN_STATES`, so merging the
    archive in cannot change that count either way.

    Builds one `TicketFlowRow` per calendar day from the EARLIEST observed
    filing/landing event through `today` (defaults to `date.today()`,
    injectable for deterministic tests), zero-filled -- a day with no
    activity still gets a row, so the trailing-window average always
    covers a real fixed-size span instead of skipping silently over quiet
    days. Returns an all-zero, single-`today`-row report (no crash, no
    `NotFound`) for an empty queue, same no-error-case contract
    `sprint_velocity` already keeps."""
    archived = load_archive(root)
    archive_tickets = archived.danger_ok if archived.is_ok else {}
    if archived.is_err:
        _log.warning(
            "tickets: ticket_flow could not load tickets-archive.md (%s) -- "
            "landed/filed counts for already-archived tickets are omitted "
            "this run",
            archived.danger_err,
        )
    all_tickets = {**archive_tickets, **queue.tickets}

    filed_by_day: dict[date, int] = {}
    for ticket in all_tickets.values():
        filed_by_day[ticket.created] = filed_by_day.get(ticket.created, 0) + 1

    transitions = _mine_done_transitions(root, tuple(all_tickets.keys()))
    landed_by_day: dict[date, int] = {}
    for transition in transitions:
        day = transition.committed_at.date()
        landed_by_day[day] = landed_by_day.get(day, 0) + 1

    today = today if today is not None else date.today()
    observed_days = list(filed_by_day) + list(landed_by_day) + [today]
    earliest = min(observed_days)

    rows: list[TicketFlowRow] = []
    day = earliest
    while day <= today:
        rows.append(
            TicketFlowRow(
                day=day,
                filed=filed_by_day.get(day, 0),
                landed=landed_by_day.get(day, 0),
            )
        )
        day += timedelta(days=1)

    trailing = rows[-_FLOW_TRAILING_DAYS:] if rows else []
    trailing_net_rate = (
        sum(r.net for r in trailing) / len(trailing) if trailing else 0.0
    )
    open_count = sum(1 for t in queue.tickets.values() if t.state in _OPEN_STATES)
    return TicketFlowReport(
        rows=tuple(rows),
        open_count=open_count,
        trailing_net_rate=trailing_net_rate,
    )


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestSetComponent.test_updates_component_field  # noqa: E501
def set_component(
    root: Path, ticket_id: str, component: str | None
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `component` field (T-0454) -- which module/area this
    ticket belongs to, the same single-writer, ledger-locked pattern
    `set_priority` uses. `component=None` clears it back to uncategorized."""
    return _set_ticket_field(
        root, ticket_id, "component", component, log_value=component
    )


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


# frob:ticket T-0102
# frob:ticket T-0398
# T-0524: frob:doc removed -- this is a thin wrapper delegating to
# has_substantive_done_report (frob.tickets._models), which already
# carries the same docs/modules/tickets.md#public-api anchor; a second
# copy on this private pass-through was redundant (COV007).
def _has_done_report(body: str) -> bool:
    """Whether `body` has a substantive '## Done report' section (D-03):
    thin wrapper kept for call-site stability, delegating to
    `frob.tickets._models.has_substantive_done_report` (the single
    heading-plus-content implementation, dedupe of D-11's twin)."""
    return has_substantive_done_report(body)


def _start_blockers(ticket: Ticket, queue: dict[str, Ticket]) -> list[str]:
    """Blocker ids of `ticket` that are unknown or still in an open state."""
    return [
        b for b in ticket.blocked_by if b not in queue or queue[b].state in _OPEN_STATES
    ]


# frob:ticket T-0417
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


def _done_transition_guard(
    root: Path,
    ticket: Ticket,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
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

    `covers_scope`/`reviewed`/`mutation_evidence`/`evidence_reverified` are
    injected, never computed here: answering "does an evidence id cover a
    touched/scope symbol" needs the obligation graph (`frob.graph`) and the
    `TESTS`-edge index `frob.testing`/`frob.gates` already build, answering
    "is there an approve review naming HEAD" needs `git rev-parse` under
    the caller's root, answering "did the bound evidence kill a mutant"
    needs `frob.gates.mutation_evidence_violations`, and answering "does
    the evidence still pass right now" needs a real test-runner spawn --
    `frob.tickets` deliberately stays free of all four dependencies
    (docs/rework.md cycle-avoidance -- `frob.gates`/`frob.app` are the
    layers allowed to join graph/runner + tickets). `None` (the default,
    matching every caller before D-02/T-0571/T-0844/T-0417) skips each
    check entirely, so existing callers/tests are unaffected; a caller
    with the needed context (`frob.gates.evidence_covers_scope`,
    `has_approved_review_for_commit`, `frob.gates.mutation_evidence_
    violations`, `frob.app.ticket_runner._reverify_evidence_for_close`, or
    its own equivalent) opts in by passing an explicit `True`/`False`.
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
# frob:ticket T-0715
# frob:ticket T-0417
def transition(
    root: Path,
    ticket_id: str,
    to: TicketState,
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a
    substantive Done report, (D-02) an evidence id covering a touched/
    scope symbol whenever the caller supplies `covers_scope=False`,
    (T-0571) an approve-verdict review record naming the current commit
    whenever the caller supplies `reviewed=False`, (T-0844) refuses on
    an unwaived ERROR-severity TEST016 confirmatory-only-evidence finding
    whenever the caller supplies `mutation_evidence=False`, and (T-0417
    N-02) refuses when a fresh re-run of the ticket's recorded evidence
    against the CURRENT tree no longer passes, whenever the caller
    supplies `evidence_reverified=False` (see `_done_transition_guard`'s
    docstring for why these are injected rather than computed here)."""
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
def reverify_close_guard(
    root: Path,
    ticket_id: str,
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
) -> Result[Ticket, TicketError]:
    """`frob ticket reverify`'s (T-1005) state-machine half: re-run the
    EXACT SAME `_done_transition_guard` check `transition(..., TicketState.
    DONE, ...)` runs at close time -- structural (evidence + Done report
    present, no open descendants, no disallowed cmd: evidence, D-02
    covers_scope, T-0572 acceptance binding), T-0571 reviewed (when
    injected), T-0844 mutation_evidence (when injected), T-0417
    evidence_reverified (when injected), and the two ALWAYS-run diff-
    derived checks (T-0854 live-tracker citation, T-0756 new-gate-rule
    acceptance) -- against a ticket that is ALREADY `done`, with NO write
    and NO state transition attempted either way. This closes churn item 6
    (docs/audits/coordination-churn.md): after a post-close send-back
    (e.g. a TEST016 strengthening) lands new scope/evidence/done-report
    edits on a done ticket, nothing could previously re-run close's own
    verification suite (`close` itself refuses done->done via the state
    machine; `start`/`sweep` both refuse a done ticket outright) -- lands
    proceeded on trust in the stale recap alone.

    Refuses immediately (`TicketError.InvalidTransition`, matching the
    state machine's own vocabulary for "wrong state to do this in") unless
    `ticket.state is TicketState.DONE` -- reverify is specifically the
    post-close re-check, not a substitute for `close` on an in-progress
    ticket. `covers_scope`/`reviewed`/`mutation_evidence`/
    `evidence_reverified` are injected exactly like `transition`'s own
    parameters of the same names (the caller, `frob.app.ticket_runner.
    _reverify`, computes them via the identical `_close_guards_for_ticket`
    helper `_close` itself calls -- no duplicated guard-computation
    logic, only the write/transition step is skipped here)."""
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

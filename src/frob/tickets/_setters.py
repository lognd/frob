# frob:waive LARGE001 reason="T-1651-grade, post-T-2834 shape (T-2847): the \
# sprint/flow analytics family already split out to _flow.py in T-2834, leaving only \
# single-ticket field mutators (set_priority/set_kind/set_tier/set_parent/ \
# set_body/set_runs_last/set_runs_last_parallel_safe/set_milestone/ \
# set_scope_breadth_ack/set_no_scope_declared/set_designated_repro_test/ \
# set_sprint/set_component) plus their shared write-path helpers (_set_ticket_field, \
# _refuse_write_if_land_in_progress, _validate_parent_edge, _validate_body_amend, \
# _current_actor). Every one of these is the SAME consumer concern -- mutating exactly \
# one field on exactly one already-loaded Ticket through the same single-writer choke \
# point -- so there is no consumer-set seam left to cut: any split would either \
# duplicate _set_ticket_field/_refuse_write_if_land_in_progress across two files or \
# introduce a cross-file coupling neither the flow split nor the original T-1151 split \
# needed. 1111 lines reflects the number of distinct ticket fields this repo lets an \
# agent mutate, not an uncohered file; a further line-count-driven split here would be \
# strictly worse than the warning per the T-1651 bar."
"""frob.tickets._setters -- the field-setter family (T-1151, T-1123/T-1108
residue, narrowed by T-2834): the single-field setters (`set_priority`/
`set_kind`/`set_tier`/`set_sprint`/`set_component`) split out of
`frob.tickets.__init__` following T-1103's per-family extraction pattern
(verbatim moves, directives intact, public surface re-exported via explicit
imports, zero caller-visible behavior change).

Kept together because every setter shares one accountable single-writer
helper (`_set_ticket_field`).

T-2834: the sprint/flow analytics family (`sprint_view`/`sprint_velocity`/
`ticket_flow` and their git-history-mining helpers) that used to live here
moved to `frob.tickets._flow` -- a distinct concern (mining git history
across the whole queue to report burn-down/velocity, vs. this module's
single-ticket field mutation) that shared no substrate with the setters
beyond an import list. The three names are re-imported and re-exported at
the bottom of this module's import block so `frob.tickets.__init__`'s
existing `from frob.tickets._setters import (sprint_velocity, sprint_view,
ticket_flow)` needs no change.

`_load_ticket_and_queue` and `_OPEN_STATES` intentionally STAY in
`frob.tickets.__init__` (both are shared by several non-setter families
still there -- `transition`, `add_evidence`, `_open_descendant_ids`) -- this
module late-imports both from the package at call time rather than at load
time, the same load-order-safe indirection `_doable.py` uses for
`_doable_sort_key`/`_OPEN_STATES`, since `__init__` imports THIS module
before either name exists yet at its own module scope.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._leases import LeaseError, refuse_if_land_in_progress
from frob.tickets._models import (
    DONE_REPORT_HEADING,
    DROP_REASON_HEADING,
    FAILURE_LOG_HEADING,
    BodyChangeEntry,
    DesignatedReproChangeEntry,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketTier,
    TriageChangeEntry,
    replace_done_report_section,
    validate_milestone,
)
from frob.tickets._store import (
    _split_done_report,
    _store_mode,
    ledger_lock,
    load_all,
    load_archive,
    v2_archive_dir,
    v2_ticket_dir,
    write_archived_ticket,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)


# frob:ticket T-2785
def _refuse_write_if_land_in_progress(root: Path) -> Result[None, LeaseError]:
    """This module's own pre-write land guard (T-2785), mirroring
    `frob.tickets._reconcile._refuse_apply_if_land_in_progress` (T-2291,
    the SAME incident shape): checked BEFORE any lease/lock/write below,
    so a refusal leaves the working tree untouched instead of the pre-
    T-2785 shape -- write first, discover the ledger auto-commit was
    refused only later at the CLI's post-dispatch commit step (out of
    this module's scope), stranding the write uncommitted and DirtyMain-
    blocking every other agent's land. `refuse_if_land_in_progress`
    (T-1619/T-1961) is reused directly, including its own bounded wait --
    a land that finishes within that window is never refused, so a
    genuinely free repository behaves exactly as before this ticket.
    `Ok(None)` when no land is in progress (or the wait resolved before
    timing out); `Err(LeaseError.LandInProgress)`, no write attempted,
    otherwise."""
    land_check = refuse_if_land_in_progress(root)
    if land_check.is_err:
        _log.warning(
            "tickets: %s setter refused (land in progress) -- no ledger "
            "write attempted",
            root,
        )
        return land_check
    return Ok(None)


def _field_str(value: object) -> str | None:
    """Best-effort string form of a ticket field's raw value for a
    `TriageChangeEntry.old_value`/`new_value` (T-2353): an enum's `.value`
    where the field carries one, `None` unchanged (an unset `component`),
    and `str(value)` otherwise -- the same "log the enum's `.value`, not
    its repr" preference `_set_ticket_field`'s `log_value` callers already
    apply, just also applied to the OLD value, which no caller previously
    had a reason to format."""
    if value is None:
        return None
    inner = getattr(value, "value", None)
    return inner if isinstance(inner, str) else str(value)


# frob:ticket T-2353
def _triage_change_entry(
    field: str, old_value: object, new_value: object, reason: str
) -> TriageChangeEntry:
    """Build the `TriageChangeEntry` (T-2353) `_set_ticket_field` appends
    for a reasoned triage-field mutation: formats `old_value`/`new_value`
    (`_field_str`) and stamps `actor`/`at`."""
    from datetime import date as _date

    return TriageChangeEntry(
        field=field,
        old_value=_field_str(old_value),
        new_value=_field_str(new_value),
        reason=reason,
        actor=_current_actor(),
        at=_date.today(),
    )


def _set_ticket_field(
    root: Path,
    ticket_id: str,
    field: str,
    value: object,
    *,
    log_value: object,
    reason: str | None = None,
) -> Result[Ticket, TicketError | LeaseError]:
    """Set one `field` on `ticket_id` to `value` (extracted T-0861): the
    ONE lease-check + ledger-locked-load + `model_copy(update=...)` +
    write + log shape `set_priority`/`set_kind`/`set_sprint`/
    `set_component` each need for their own single-field setter, so the
    accountable single-writer discipline can never desync between fields.
    `log_value` lets a caller log an enum's `.value` instead of the enum
    repr where that reads better; the field name itself is embedded in
    the log line by the caller via `field`.

    T-2353: `reason` (keyword-only) is required by `set_priority`/
    `set_kind`/`set_component`/`set_tier` (each validates non-empty
    before calling in) and, whenever given, appends a `TriageChangeEntry`
    to `ticket.triage_changes` recording `field`, the old and new value,
    `reason`, actor, and date -- the `ScopeChangeEntry` discipline
    (T-0455) applied to these four single-value classification fields. A
    no-op write (`value` already matches) still appends an entry when
    `reason` is given -- a caller who explicitly re-asserted the same
    value with a stated reason gets that recorded, not silently
    swallowed; only a truly unreasoned caller (library-internal, no
    `reason`) skips the audit trail entirely, same as before this
    ticket."""
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        update: dict[str, object] = {field: value}
        if reason is not None:
            # frob:waive OPAQUE001 reason="T-2353: field ranges only over this \
            # module's own hardcoded single-value setter callers (priority/kind/ \
            # component/tier), never external/CLI-controlled input -- same closed, \
            # statically-declared field-set shape as _config_external.py's own T-1038 \
            # OPAQUE001 waivers"
            old_value = getattr(ticket, field, None)
            entry = _triage_change_entry(field, old_value, value, reason)
            update["triage_changes"] = ticket.triage_changes + (entry,)
        updated = ticket.model_copy(update=update)
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s %s set to %s", ticket_id, field, log_value)
    return Ok(updated)


# frob:ticket T-0411
# frob:ticket T-2353
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_priority.py::TestSetPriority.test_updates_priority_field
# frob:tests tests/test_tickets_priority.py::TestSetPriority.test_reason_missing_refuses
# frob:tests \
# tests/test_tickets_priority.py::TestSetPriority.test_reasoned_change_records_triage_e\
# ntry
def set_priority(
    root: Path, ticket_id: str, priority: Priority, *, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """Set `ticket_id`'s `priority` field (T-0411) -- the accountable,
    single-writer way to reprioritize a ticket instead of hand-editing
    `tickets.md` frontmatter. Held under `ledger_lock` (same discipline as
    `mutate_scope`) so this can never interleave with a concurrent ledger
    mutation. A no-op write (still logged) if `priority` already matches.

    T-2353: `reason` is now REQUIRED (`Err(TicketError.TriageReasonMissing)`
    on a blank/whitespace-only value) and recorded into a `TriageChangeEntry`
    appended to `ticket.triage_changes` -- closing the "priority change
    leaves no audit trail" gap this ticket found: `scope`/`accept --amend`
    both already required and recorded a reason, `priority` alone did not."""
    if not reason.strip():
        return Err(TicketError.TriageReasonMissing)
    return _set_ticket_field(
        root, ticket_id, "priority", priority, log_value=priority.value, reason=reason
    )


# frob:ticket T-0834
# frob:ticket T-1616
# frob:ticket T-2353
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_evidence.py::TestSetKind.test_updates_kind_field
# frob:tests \
# tests/test_ticket_evidence.py::TestKindHistory.test_change_after_evidence_recorded
# frob:tests tests/test_ticket_evidence.py::TestKindHistory.test_change_before_any_work_not_recorded  # noqa: E501
# frob:tests tests/test_ticket_evidence.py::TestSetKind.test_reason_missing_refuses
def set_kind(
    root: Path, ticket_id: str, kind: TicketKind, *, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """Set `ticket_id`'s `kind` field (T-0834) -- the accountable,
    single-writer way to correct a mis-filed kind instead of hand-editing
    `tickets.md` frontmatter, same ledger-locked, no-terminal-state-check
    pattern `set_priority` uses. A no-op write (still logged) if `kind`
    already matches.

    T-2353: `reason` is now REQUIRED (`Err(TicketError.TriageReasonMissing)`
    on a blank/whitespace-only value) and recorded into a `TriageChangeEntry`
    appended to `ticket.triage_changes`, the same `set_priority`/T-2353
    accountability this module's other single-value setters gained.

    T-1616: if the ticket already carries evidence and/or a substantive
    Done report at the moment of the change -- i.e. this is not a fresh,
    pre-work reclassification but one that could be relaxing an
    already-earned evidence obligation (a `bug`-kind ticket becoming
    `feature` to dodge BUG002 is the motivating case) -- the change is
    ALSO appended to `kind_history` (never edited, only appended; distinct
    from and in addition to `triage_changes`, since `kind_history`'s
    trigger is conditional on evidence/Done-report state while
    `triage_changes` records every reasoned kind change unconditionally),
    so a reviewer or `frob ticket land` can see it happened instead of
    reading a silent frontmatter edit."""
    if not reason.strip():
        return Err(TicketError.TriageReasonMissing)
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        update: dict[str, object] = {"kind": kind}
        history_entry = _kind_history_entry(ticket, kind)
        if history_entry is not None:
            update["kind_history"] = (*ticket.kind_history, history_entry)
        update["triage_changes"] = ticket.triage_changes + (
            _triage_change_entry("kind", ticket.kind, kind, reason),
        )
        updated = ticket.model_copy(update=update)
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s kind set to %s", ticket_id, kind.value)
    if history_entry is not None:
        _log.warning(
            "tickets: %s kind changed from %s to %s AFTER evidence/Done-report "
            "already existed -- recorded in kind_history: %s",
            ticket_id,
            ticket.kind.value,
            kind.value,
            history_entry,
        )
    return Ok(updated)


# frob:ticket T-2353
def _kind_history_entry(ticket: Ticket, kind: TicketKind) -> str | None:
    """T-1616's `kind_history` line for `set_kind`'s change from `ticket.
    kind` to `kind`, split out of `set_kind` (T-2353, ARCH001) -- `None`
    when this is not a post-evidence/Done-report reclassification (a
    fresh, pre-work kind correction records nothing here)."""
    from frob.tickets._models import has_substantive_done_report

    if kind == ticket.kind or not (
        ticket.evidence or has_substantive_done_report(ticket.body)
    ):
        return None
    done_report = has_substantive_done_report(ticket.body)
    return (
        f"{date.today().isoformat()} {ticket.kind.value}->{kind.value} "
        f"evidence={len(ticket.evidence)} "
        f"done_report={'yes' if done_report else 'no'}"
    )


# frob:ticket T-1069
# frob:ticket T-2353
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSetTier.test_updates_tier_field
# frob:tests tests/test_tickets_tiers.py::TestSetTier.test_reason_missing_refuses
def set_tier(
    root: Path, ticket_id: str, tier: TicketTier, *, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket tier <id> <epic|story|ticket>`: set `ticket_id`'s `tier`
    field (T-1069) -- the accountable, single-writer way to reclassify an
    already-created ticket's place in the epic -> story -> ticket hierarchy
    instead of hand-editing `tickets.md` frontmatter, same ledger-locked
    `_set_ticket_field` pattern `set_priority`/`set_kind`/`set_component`/
    `set_sprint` all share. This changes only the `tier` label itself --
    T-0715's structural rules (`doable`'s leaf-only surfacing, `transition`'s
    open-descendant close guard) key off whatever `tier` a ticket currently
    carries, so they apply to the new value on the very next read; this
    function does not re-validate or move `parent` links.

    T-2353: `reason` is now REQUIRED (`Err(TicketError.TriageReasonMissing)`
    on a blank/whitespace-only value) and recorded into a `TriageChangeEntry`
    appended to `ticket.triage_changes`, the same `set_priority`/T-2353
    accountability this module's other single-value setters gained."""
    if not reason.strip():
        return Err(TicketError.TriageReasonMissing)
    return _set_ticket_field(
        root, ticket_id, "tier", tier, log_value=tier.value, reason=reason
    )


# frob:ticket T-2770
#: rank of each `TicketTier` in the epic -> story -> ticket hierarchy
#: (lower = higher up); `set_parent`'s tier-inversion refusal requires a
#: parent's rank to be NO GREATER than the child's -- same-tier chaining
#: (an epic parenting another epic, T-2770's own T-2384->T-1382 positive
#: control) is allowed, only a LOWER tier parenting a higher one (a
#: `ticket` parenting an `epic`) is refused.
_TIER_RANK: dict[TicketTier, int] = {
    TicketTier.EPIC: 0,
    TicketTier.STORY: 1,
    TicketTier.TICKET: 2,
}


# frob:ticket T-2770
def _parent_creates_cycle(
    queue: dict[str, Ticket], ticket_id: str, parent_id: str
) -> bool:
    """True if walking `parent_id`'s own `parent` chain (any depth) would
    eventually reach `ticket_id` (T-2770) -- i.e. `ticket_id` is already an
    ancestor of `parent_id`, so pointing `ticket_id.parent` at `parent_id`
    would close a ring (the direct `A parent B, B parent A` case and any
    longer one). Terminates on a `seen` id set the same way `effective_
    milestone`'s walk does, so a pre-existing malformed/dangling chain
    cannot loop forever; a dangling `parent` id (not in `queue`) simply
    stops the walk short of a cycle finding."""
    seen = {ticket_id}
    current_id: str | None = parent_id
    while current_id is not None:
        if current_id in seen:
            return True
        seen.add(current_id)
        current = queue.get(current_id)
        current_id = current.parent if current is not None else None
    return False


# frob:ticket T-2770
def _validate_parent_edge(
    queue: dict[str, Ticket], ticket: Ticket, parent_id: str
) -> TicketError | None:
    """`set_parent`'s real structural validation, split out (ARCH001) so
    the setter itself stays a thin ledger-locked load/write shell: refuses
    a `parent_id` not present in `queue` (`ParentNotFound`), one that would
    close a cycle via `_parent_creates_cycle` (`ParentCycle`), or one whose
    tier ranks LOWER than `ticket`'s own (`ParentTierInversion`) -- a
    `ticket` cannot parent an `epic`/`story`, a `story` cannot parent an
    `epic`, but same-tier chaining (an `epic` parenting another `epic`,
    T-2770's own T-2384->T-1382 positive control) is allowed. `None` when
    `parent_id` is a valid target."""
    parent = queue.get(parent_id)
    if parent is None:
        return TicketError.ParentNotFound
    if _parent_creates_cycle(queue, ticket.id, parent_id):
        return TicketError.ParentCycle
    if _TIER_RANK[parent.tier] > _TIER_RANK[ticket.tier]:
        return TicketError.ParentTierInversion
    return None


# frob:ticket T-2770
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_reparents_leaf_to_epic
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_self_parent_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_nonexistent_parent_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_direct_cycle_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_longer_ring_cycle_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_tier_inversion_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_epic_can_parent_epic
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_story_cannot_parent_epic
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_reason_missing_refuses
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_moving_an_existing_parent_drops_the_old_edge  # noqa: E501
# frob:tests tests/test_tickets_parent.py::TestSetParent.test_archived_ticket_routes_to_archive_path  # noqa: E501
def set_parent(
    root: Path, ticket_id: str, parent_id: str, *, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket set-parent <id> <parent-id> --reason TEXT`: the
    accountable, single-writer way to correct `ticket_id`'s `parent` edge
    (T-2770) -- `frob ticket new --parent` was the only place this field
    could previously be set, so a mis-parented ticket had no CLI route to
    fix, only the forbidden hand edit `set_body`/T-2392 exists to prevent
    for the body field.

    Refuses (write nothing) for a blank `reason`
    (`Err(TicketError.ParentTicketReasonMissing)`), `parent_id ==
    ticket_id` self-parenting (`Err(TicketError.ParentSelfReference)`), a
    land genuinely in progress against `root`
    (`Err(LeaseError.LandInProgress)`, T-2785 -- see
    `_refuse_write_if_land_in_progress`), or any of
    `_validate_parent_edge`'s structural checks (nonexistent parent,
    cycle, tier inversion) -- see that function's docstring for the exact
    rule set. T-2770's own measured customer: a `tier=epic` ticket whose
    successor work was filed with `parent: null` reads as "every child
    terminal, epic closeable" to the rot detector even though the epic's
    real goal is unmet; re-parenting the successor onto the epic is the
    fix, and this is the only way to do it without a hand edit.

    Re-parenting a DONE-but-still-active OR archived ticket is allowed
    (parent is organizational metadata, not a state-machine transition,
    and the T-2770 customer instance -- T-2386 -- is exactly a `done`
    ticket needing correction); an archived target routes through
    `write_archived_ticket` via `_ticket_currently_archived`, the same
    `set_body`/T-2678 fix, never creating a duplicate active-tree copy.
    Moving an already-parented ticket simply overwrites the scalar field
    -- the old edge never lingers.

    T-2785: setting `parent_id` to the value `ticket_id` ALREADY carries
    is a clean no-op -- no `TriageChangeEntry` is appended and no write
    is attempted at all (`updated` is returned byte-identical to the
    loaded ticket), the same "no audit event for a non-change" posture
    `_redesignation_entry` already gives `set_designated_repro_test`. The
    measured incident this closes: a `set-parent` call that re-asserted
    an already-current parent (an earlier caller had already performed
    the real move) still appended `old_value == new_value` triage noise
    and, combined with the pre-T-2785 land-in-progress race, was exactly
    what produced the dirty working tree that DirtyMain-blocked the
    fleet."""
    if not reason.strip():
        return Err(TicketError.ParentTicketReasonMissing)
    if parent_id == ticket_id:
        return Err(TicketError.ParentSelfReference)
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, queue = loaded.danger_ok
        if ticket.parent == parent_id:
            _log.info(
                "tickets: %s parent already %s -- no-op, nothing written",
                ticket_id,
                parent_id,
            )
            return Ok(ticket)
        return _write_parent_change(root, ticket, queue, parent_id, reason)


# frob:ticket T-2785
def _write_parent_change(
    root: Path,
    ticket: Ticket,
    queue: dict[str, Ticket],
    parent_id: str,
    reason: str,
) -> Result[Ticket, TicketError | LeaseError]:
    """`set_parent`'s validate-then-write half, split out to keep that
    function under ARCH001's line threshold (T-2785): runs
    `_validate_parent_edge`'s structural checks, then appends the
    `TriageChangeEntry` and writes -- called ONLY for a genuine change
    (`set_parent` already returned early for a no-op); must be called
    from inside the SAME `ledger_lock` hold `set_parent` already took, so
    this never re-acquires it itself."""
    old_parent = ticket.parent
    validation_error = _validate_parent_edge(queue, ticket, parent_id)
    if validation_error is not None:
        return Err(validation_error)
    entry = _triage_change_entry("parent", old_parent, parent_id, reason)
    updated = ticket.model_copy(
        update={
            "parent": parent_id,
            "triage_changes": ticket.triage_changes + (entry,),
        }
    )
    write_result = (
        write_archived_ticket(root, updated)
        if _ticket_currently_archived(root, ticket.id)
        else write_ticket(root, updated)
    )
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s parent set to %s (was %s): %s",
        ticket.id,
        parent_id,
        old_parent,
        reason,
    )
    return Ok(updated)


# frob:ticket T-2498
def _validate_body_amend(mode: str, reason: str, text: str) -> TicketError | None:
    """`set_body`'s pre-lock validation, split out to keep `set_body`
    itself under ARCH001's length threshold (T-2498): rejects a blank
    `reason`, an unrecognized `mode`, or `text` that contains a line
    matching one of this package's own structural section headings (`##
    Done report`/`## Failure log`/`## Drop reason`) -- the ambiguous-
    target case `set_body`'s own docstring documents. Returns the
    `TicketError` to raise, or `None` if `text`/`mode`/`reason` are all
    acceptable."""
    if not reason.strip():
        return TicketError.BodyReasonMissing
    if mode not in ("append", "set"):
        return TicketError.BodyModeConflict
    if any(
        line.strip() in (DONE_REPORT_HEADING, FAILURE_LOG_HEADING, DROP_REASON_HEADING)
        for line in text.splitlines()
    ):
        return TicketError.BodyTextAmbiguousSection
    return None


# frob:ticket T-2498
def _amend_raw_body(raw_body: str, text: str, mode: str) -> str:
    """The actual append/set arithmetic on a ticket's TRUE raw body (T-2498
    -- split out of `set_body` to keep it under ARCH001's length
    threshold): `mode="append"` adds `text` after a blank-line separator
    (skipped if `raw_body` is empty/whitespace-only), `mode="set"`
    replaces it outright. Operates on `raw_body`, never the composite
    body a Done report may have been spliced into -- see `set_body`'s own
    docstring for why that distinction is the whole point of this
    ticket."""
    if mode == "append":
        return f"{raw_body}\n\n{text}" if raw_body.strip() else text
    return text


# frob:ticket T-2678
# frob:tests \
# tests/unit/test_ticket_store.py::TestSetBodyArchivedTicketRouting.test_append_on_archived_ticket_writes_archive_path_only  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestSetBodyArchivedTicketRouting.test_append_on_active_ticket_still_writes_active_path  # noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestSetBodyArchivedTicketRouting.test_single_mode_append_on_archived_ticket_writes_archive_only  # noqa: E501
def _ticket_currently_archived(root: Path, ticket_id: str) -> bool:
    """True when `ticket_id` currently lives ONLY in archive storage, not
    active (T-2678): `set_body` (and any other same-id mutation routed
    through `write_ticket`) must target `write_archived_ticket` for such a
    ticket instead of the plain active-tree `write_ticket` -- writing an
    archived ticket's amendment to the active path creates a FRESH
    `tickets/<id>/` directory alongside the untouched `tickets/archive/<id>/`
    one, the exact DuplicateId corruption T-2678 traces (`frob ticket show`
    then refuses outright, fleet-wide, since the id now resolves to two
    different files). v2 mode: checked by plain path existence, not a full
    `load_all`/`load_archive` parse, so this stays cheap enough to call on
    every `set_body` write. Single mode: archive is one shared
    `tickets-archive.md` monofile with no per-ticket path to check, so this
    loads both stores and tests membership directly -- `set_body`'s own
    caller-visible cost either way, never a hot loop. `dir` mode has no
    archive concept (mirrors `write_archived_ticket`'s own dir-mode refusal)
    and always reads as active (False)."""
    mode = _store_mode(root)
    if mode == "v2":
        archived_path = v2_archive_dir(root, ticket_id) / "ticket.md"
        active_path = v2_ticket_dir(root, ticket_id) / "ticket.md"
        return archived_path.is_file() and not active_path.is_file()
    if mode == "single":
        active = load_all(root)
        if active.is_ok and ticket_id in active.danger_ok:
            return False
        archived = load_archive(root)
        return archived.is_ok and ticket_id in archived.danger_ok
    return False


# frob:ticket T-2392
# frob:doc docs/modules/tickets-data-storage.md#data-models
# frob:tests tests/test_tickets_body.py::TestBodyAmend.test_append_appends_text
# frob:tests tests/test_tickets_body.py::TestBodyAmend.test_set_replaces_text
# frob:tests tests/test_tickets_body.py::TestBodyAmend.test_reason_missing_refuses
# frob:tests tests/test_tickets_body.py::TestBodyAmend.test_append_records_body_change_entry  # noqa: E501
def set_body(
    root: Path,
    ticket_id: str,
    text: str,
    *,
    mode: str,
    reason: str,
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket body <id> (--append TEXT|--append-file PATH | --set
    TEXT|--set-file PATH) --reason TEXT`: amend `ticket_id`'s free-text
    `body` (T-2392) -- the accountable, single-writer front door this
    ticket adds so a directive (e.g. `frob:no-behavior-change reason=...`,
    T-2393's own remedy) can be added to a ticket's body WITHOUT hand-
    editing `tickets/T-####/ticket.md`, the exact operation this repo
    learned to forbid after a hand-typed space-hash broke the ledger YAML
    and took every gate down (see T-2392's own body for the incident).

    `mode` is `"append"` (default shape: `text` is appended after a blank
    line separating it from the existing body, matching how a maintainer
    would hand-type a new paragraph) or `"set"` (replace the body
    outright -- rare, but needed for a genuinely wrong body rather than
    one missing a directive). Held under `ledger_lock` (same discipline as
    every other single-field setter in this module) so this can never
    interleave with a concurrent ledger mutation.

    `reason` is REQUIRED (`Err(TicketError.BodyReasonMissing)` on a
    blank/whitespace-only value) and recorded into a `BodyChangeEntry`
    (T-2392) appended to `ticket.body_changes` -- the `TriageChangeEntry`/
    `ScopeChangeEntry` accountability (T-2353/T-0455) applied to the body
    itself. Unlike those two, the entry stores lengths, not the full text,
    since a ticket body can be many KB (see `BodyChangeEntry`'s own
    docstring) -- the full before/after diff is `tickets.md`'s own git
    history.

    T-2498: `ticket.body` as loaded here is the COMPOSITE view -- v2
    storage splices a sibling `done-report.md` back into `body`
    (`_merge_sibling_done_report`) so every OTHER consumer (close,
    evidence recovery, BUG002) sees one unified text. Operating on that
    composite directly used to silently misroute: an append landed
    textually after the spliced-in `## Done report` heading, so
    `write_ticket`'s own `_split_done_report` (the mechanical inverse)
    read the appended text as part of the Done report and persisted it
    into `done-report.md` instead of `ticket.md`'s real body -- a false
    success (the command reports the append and records a `BodyChangeEntry`)
    with the write landing somewhere the caller never asked for. This now
    unsplices FIRST (`_split_done_report`), amends only the true raw
    `ticket.md` body, then re-splices the untouched report text back in
    before handing the composite to `write_ticket` (whose own split
    recovers the same two pieces) -- so append/set always target the real
    body regardless of whether a Done report exists. `BodyChangeEntry`
    lengths are computed from the raw body too, not the composite, so the
    ledger records what actually changed on disk. If `text` itself
    contains a line matching a structural section heading this package
    writes programmatically (`## Done report`/`## Failure log`/`## Drop
    reason`) the target section is ambiguous -- splicing it in unsplit
    could again be silently reinterpreted as (or swallow) a different
    section on the next write -- so this refuses loudly
    (`Err(TicketError.BodyTextAmbiguousSection)`) instead of writing
    anything. T-2785: also refuses (write nothing) when a land is
    genuinely in progress against `root`
    (`Err(LeaseError.LandInProgress)`), the same pre-write guard
    `set_parent`/`_set_ticket_field` now share -- see
    `_refuse_write_if_land_in_progress`."""
    validation_error = _validate_body_amend(mode, reason, text)
    if validation_error is not None:
        return Err(validation_error)
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    from frob.tickets import _load_ticket_and_queue

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        raw_body, report_text = _split_done_report(ticket.body)
        new_raw_body = _amend_raw_body(raw_body, text, mode)
        new_body = (
            replace_done_report_section(new_raw_body, report_text)
            if report_text is not None
            else new_raw_body
        )
        entry = BodyChangeEntry(
            mode=mode,
            reason=reason,
            actor=_current_actor(),
            at=date.today(),
            old_length=len(raw_body),
            new_length=len(new_raw_body),
        )
        update: dict[str, object] = {
            "body": new_body,
            "body_changes": ticket.body_changes + (entry,),
        }
        updated = ticket.model_copy(update=update)
        write_result = (
            write_archived_ticket(root, updated)
            if _ticket_currently_archived(root, ticket_id)
            else write_ticket(root, updated)
        )
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s body %s (%d -> %d chars): %s",
        ticket_id,
        mode,
        entry.old_length,
        entry.new_length,
        reason,
    )
    return Ok(updated)


# frob:ticket T-1613
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_organization.py::TestRunsLast.test_set_runs_last_updates_field
def set_runs_last(
    root: Path, ticket_id: str, runs_last: bool
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket runs-last <id> <on|off>`: set `ticket_id`'s `runs_last`
    marker (T-1613) -- the accountable, single-writer way to flag/unflag a
    ticket that must stay structurally undoable while any other
    non-runs-last ticket is open, same ledger-locked `_set_ticket_field`
    pattern `set_priority`/`set_kind`/`set_tier` all share. The structural
    enforcement itself (`doable` never surfacing it, `start` refusing it)
    lives in `frob.tickets._doable`/`frob.tickets._evidence` and keys off
    whatever `runs_last` a ticket currently carries -- this function only
    flips the label."""
    return _set_ticket_field(
        root, ticket_id, "runs_last", runs_last, log_value=runs_last
    )


# frob:ticket T-2624
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_organization.py::TestSetRunsLastParallelSafe.test_reason_missing_r\
# efuses
# frob:tests \
# tests/test_tickets_organization.py::TestSetRunsLastParallelSafe.test_ack_sets_both_fi\
# elds
def set_runs_last_parallel_safe(
    root: Path, ticket_id: str, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket runs-last-parallel-safe <id> --reason TEXT`: the
    retroactive setter T-2579 (M4b) left unbuilt -- declares `ticket_id`
    safe to run in parallel with another `runs_last` ticket in the same
    milestone despite neither ordering the other via `blocked_by`
    (MILE004's escape hatch), sets `runs_last_parallel_safe=True` and
    records `reason` in `runs_last_parallel_safe_reason` in one
    ledger-locked write. Same bool+reason shape and same non-blank
    `reason` requirement as `set_scope_breadth_ack`'s T-1484 precedent --
    a declaration with no stated justification is exactly the ambiguity
    MILE004 exists to catch, so it is refused here rather than silently
    accepted. T-2785: also refuses (write nothing) while a land is
    genuinely in progress against `root` -- see
    `_refuse_write_if_land_in_progress`."""
    if not reason.strip():
        return Err(TicketError.RunsLastParallelSafeReasonMissing)
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    from frob.tickets import _load_ticket_and_queue

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(
            update={
                "runs_last_parallel_safe": True,
                "runs_last_parallel_safe_reason": reason,
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s runs_last_parallel_safe set to True (reason=%s)",
        ticket_id,
        reason,
    )
    return Ok(updated)


# frob:ticket T-2574
# frob:doc docs/modules/tickets-data-storage.md#milestones-t-2574-m1
# frob:tests tests/test_tickets.py::TestSetMilestone.test_valid_semver_sets_field
# frob:tests tests/test_tickets.py::TestSetMilestone.test_invalid_semver_refused
def set_milestone(
    root: Path, ticket_id: str, milestone: str | None
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket milestone <id> <value>`: set `ticket_id`'s `milestone`
    field (T-2574 M1) -- the accountable, single-writer way to assign a
    ticket to a shippable milestone, same ledger-locked `_set_ticket_
    field` pattern `set_runs_last`/`set_priority`/`set_kind` all share.
    Unlike `set_runs_last`'s bare bool, a non-`None` `milestone` is
    validated via `validate_milestone` (real semver, T-2574) BEFORE the
    write -- an invalid string is refused here, never accepted and sorted
    arbitrarily later (that read-time-arbitrary-order failure mode is
    exactly what M1 exists to prevent). `milestone=None` clears the field
    unconditionally and needs no validation."""
    if milestone is not None:
        validated = validate_milestone(milestone)
        if validated.is_err:
            return Err(validated.danger_err)
    return _set_ticket_field(
        root, ticket_id, "milestone", milestone, log_value=milestone
    )


# frob:ticket T-1484
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck.test_ack_sets_both_fields
def set_scope_breadth_ack(
    root: Path, ticket_id: str, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket scope-ack <id> --reason TEXT`: acknowledge a
    genuinely-broad scope (WAVE14-B) -- sets `scope_breadth_ack=True` and
    records `reason` in `scope_breadth_ack_reason` in one ledger-locked
    write, the honest TICK009 waive channel that did not exist before this.
    A blank/whitespace-only `reason` is rejected (`Err`) the same way
    `WAIVE001` rejects a reasonless `frob:waive` -- an acknowledgement with
    no stated justification is indistinguishable from ignoring the nudge.
    T-2785: also refuses (write nothing) while a land is genuinely in
    progress against `root` -- see `_refuse_write_if_land_in_progress`."""
    if not reason.strip():
        return Err(TicketError.ScopeBreadthAckReasonMissing)
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    from frob.tickets import _load_ticket_and_queue

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(
            update={
                "scope_breadth_ack": True,
                "scope_breadth_ack_reason": reason,
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s scope_breadth_ack set to True (reason=%s)", ticket_id, reason
    )
    return Ok(updated)


# frob:ticket T-2394
# frob:doc docs/modules/tickets-lifecycle.md#declared-no-scope-t-2394
# frob:tests \
# tests/test_tickets_no_scope.py::TestSetNoScopeDeclared.test_sets_both_fields
# frob:tests \
# tests/test_tickets_no_scope.py::TestSetNoScopeDeclared.test_reason_missing_refuses
def set_no_scope_declared(
    root: Path, ticket_id: str, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket scope <id> --declare-no-scope --reason TEXT` (T-2394):
    declare that `ticket_id` LEGITIMATELY has no file scope (a tier=epic
    rollup, a pure decision record) -- sets `no_scope_declared=True` and
    records `reason` in `no_scope_declared_reason` in one ledger-locked
    write, same shape as `set_scope_breadth_ack`'s T-1484 precedent (the
    opposite problem: acknowledging a scope that is too BROAD, not one
    that is intentionally EMPTY). This is the escape hatch
    `_refuse_empty_scope_on_start` (frob.app.ticket_runner._lifecycle)
    checks before refusing `frob ticket start` on an empty `scope` --
    the fail-loudly doctrine (T-2391) applied here: an empty scope must
    be DECLARED, never merely inferred from silence. A blank/whitespace-
    only `reason` is rejected (`Err`), the same "no stated justification"
    refusal `set_scope_breadth_ack` already enforces. T-2785: also
    refuses (write nothing) while a land is genuinely in progress
    against `root` -- see `_refuse_write_if_land_in_progress`."""
    if not reason.strip():
        return Err(TicketError.NoScopeDeclaredReasonMissing)
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    from frob.tickets import _load_ticket_and_queue

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(
            update={
                "no_scope_declared": True,
                "no_scope_declared_reason": reason,
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s no_scope_declared set to True (reason=%s)", ticket_id, reason
    )
    return Ok(updated)


# frob:ticket T-1749
def _current_actor() -> str:
    """Best-effort identity for a `designated_repro_changes` audit entry's
    `actor` field (T-1749) -- duplicated one-liner from `_evidence.
    _current_actor`/`_accept._current_actor`/`_scope._current_actor`
    rather than imported, matching those modules' own documented
    cross-sibling-module tradeoff (see `_evidence._current_actor`'s own
    docstring)."""
    import getpass

    try:
        return getpass.getuser()
    except OSError:
        return "unknown"


# frob:ticket T-1749
def _redesignation_entry(
    old_value: str | None, node_id: str, reason: str | None
) -> DesignatedReproChangeEntry | None:
    """The `DesignatedReproChangeEntry` (T-1749) to append for this
    designation, or `None` when nothing should be recorded: a FIRST-time
    designation (`old_value is None`) is pure addition, the same "no audit
    event" posture `replace_evidence` gives an `old_node == new_node`
    no-op -- only a genuine REdesignation (an already-set value changing
    to a different one) leaves a trace. `old_value == node_id` (a
    redundant re-designation of the SAME id) is also a no-op, not an
    event -- nothing was actually redirected."""
    from datetime import date

    if old_value is None or old_value == node_id:
        return None
    return DesignatedReproChangeEntry(
        old_value=old_value,
        new_value=node_id,
        reason=reason,
        actor=_current_actor(),
        at=date.today(),
    )


# frob:ticket T-1749
# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/test_ticket_evidence.py::TestSetDesignatedReproTest.test_designates_a_bound_evi\
# dence_id
# frob:tests \
# tests/test_ticket_evidence.py::TestSetDesignatedReproTest.test_refuses_an_id_not_in_e\
# vidence
# frob:tests \
# tests/test_ticket_evidence.py::TestSetDesignatedReproTest.test_redesignation_appends_\
# an_audit_entry
# frob:tests \
# tests/test_ticket_evidence.py::TestSetDesignatedReproTest.test_first_time_designation\
# _appends_no_audit_entry
# frob:tests \
# tests/test_ticket_evidence.py::TestSetDesignatedReproTest.test_redesignating_the_same\
# _id_appends_no_audit_entry
def set_designated_repro_test(
    root: Path, ticket_id: str, node_id: str, *, reason: str | None = None
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket evidence <id> --designate-repro NODE-ID` (T-1670): mark
    `node_id` as the explicit BUG002 repro test, regardless of bind order
    -- `_designated_repro_test` (`frob.gates._mutation_evidence`) reads
    this field first, falling back to the old positional-first-match rule
    only when it is unset. `node_id` must already be one of `ticket_id`'s
    bound `evidence` entries (`Err(DesignatedReproNotInEvidence)`
    otherwise) -- a caller adding NEW evidence and designating one of the
    new ids in the SAME `frob ticket evidence` invocation must bind it
    first, so this check sees it; designating an id that was never bound
    (a typo, or the wrong ticket) is rejected at set time rather than
    silently recorded as a designation that can never match anything in
    `_designated_repro_test`'s own `designated in ticket.evidence` guard.

    T-1749: `reason` (keyword-only, optional) is recorded in a new
    `DesignatedReproChangeEntry` appended to `ticket.
    designated_repro_changes` whenever this call is a genuine
    REdesignation (see `_redesignation_entry`'s docstring for exactly
    which transitions count) -- closing the "no audit trail" half of the
    asymmetry T-1749 found in `--designate-repro` (the same class T-1733
    fixed for `--replace`). `reason=None` is accepted and recorded as
    such; a CLI flag that REQUIRES a reason on redesignation (mirroring
    `--replace`'s `EvidenceReplaceReasonMissing` refusal) is deliberately
    NOT added here -- it needs `src/frob/_cli_parsers/**`/`src/frob/app/
    config.py` wiring outside this ticket's declared scope; see the Done
    report for the follow-up ticket. T-2785: also refuses (write nothing)
    while a land is genuinely in progress against `root` -- see
    `_refuse_write_if_land_in_progress`."""
    land_check = _refuse_write_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    from frob.tickets import _load_ticket_and_queue

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        if node_id not in ticket.evidence:
            _log.warning(
                "tickets: %s --designate-repro %r is not one of this "
                "ticket's bound evidence ids %s -- bind it first "
                "(`frob ticket evidence %s %r`), then designate it",
                ticket_id,
                node_id,
                list(ticket.evidence),
                ticket_id,
                node_id,
            )
            return Err(TicketError.DesignatedReproNotInEvidence)
        entry = _redesignation_entry(ticket.designated_repro_test, node_id, reason)
        update: dict = {"designated_repro_test": node_id}
        if entry is not None:
            update["designated_repro_changes"] = ticket.designated_repro_changes + (
                entry,
            )
        updated = ticket.model_copy(update=update)
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s designated_repro_test set to %s%s",
        ticket_id,
        node_id,
        " (redesignation recorded)" if entry is not None else "",
    )
    return Ok(updated)


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintAssign.test_updates_sprint_field
def set_sprint(
    root: Path, ticket_id: str, sprint: str | None
) -> Result[Ticket, TicketError | LeaseError]:
    """`frob ticket sprint assign <id> <label>`: set `ticket_id`'s `sprint`
    field (T-0715) -- the same single-writer, ledger-locked pattern
    `set_component` uses. `sprint=None` clears it back to uncommitted/
    backlog."""
    return _set_ticket_field(root, ticket_id, "sprint", sprint, log_value=sprint)


# frob:ticket T-2834
# The sprint/flow analytics family (sprint_view/sprint_velocity/ticket_flow
# and their git-history-mining helpers) moved to `frob.tickets._flow` --
# re-imported and re-exported here so `frob.tickets.__init__`'s existing
# `from frob.tickets._setters import (sprint_velocity, sprint_view,
# ticket_flow)` needs no change (verified: `git grep` for all three names
# pre- and post-split shows the same import paths resolving).
from frob.tickets._flow import (  # noqa: E402
    sprint_velocity as sprint_velocity,
)
from frob.tickets._flow import (  # noqa: E402
    sprint_view as sprint_view,
)
from frob.tickets._flow import (  # noqa: E402
    ticket_flow as ticket_flow,
)


# frob:ticket T-0454
# frob:ticket T-2353
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_organization.py::TestSetComponent.test_updates_component_field
# frob:tests \
# tests/test_tickets_organization.py::TestSetComponent.test_reason_missing_refuses
def set_component(
    root: Path, ticket_id: str, component: str | None, *, reason: str
) -> Result[Ticket, TicketError | LeaseError]:
    """Set `ticket_id`'s `component` field (T-0454) -- which module/area this
    ticket belongs to, the same single-writer, ledger-locked pattern
    `set_priority` uses. `component=None` clears it back to uncategorized.

    T-2353: `reason` is now REQUIRED (`Err(TicketError.TriageReasonMissing)`
    on a blank/whitespace-only value) and recorded into a `TriageChangeEntry`
    appended to `ticket.triage_changes`, the same `set_priority`/T-2353
    accountability this module's other single-value setters gained."""
    if not reason.strip():
        return Err(TicketError.TriageReasonMissing)
    return _set_ticket_field(
        root, ticket_id, "component", component, log_value=component, reason=reason
    )

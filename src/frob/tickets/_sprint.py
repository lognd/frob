"""frob.tickets._sprint -- the one-shot sprint->milestone migration (T-5133).

Sprint is a time box (when we work); milestone is the version (what ships
together, T-2574). Before this ticket the two had collapsed: `sprint` was
carrying `v0.NNN.0`-shaped strings on the large majority of open tickets
because there was no other place to put a version. `migrate_sprint_to_
milestone` is the one-shot, idempotent repair: for every OPEN ticket whose
`sprint` is semver-shaped, it moves that value onto `milestone` (only when
`milestone` is still unset -- an existing, DIFFERENT milestone is kept and
the conflict is logged, never silently overwritten) and clears `sprint`.
Running it again is a no-op (nothing left to migrate matches the semver
shape a second time), the same idempotence `frob ticket admin reconcile`
already promises for its own repairs.

`validate_sprint`/`sprint_shape_warning` (`frob.tickets._models`) are the
GOING-FORWARD half of T-5133 (refuse the collapse from recurring); this
module is the BACKWARD-looking one-shot cleanup of the ledger's existing
state.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.tickets._archive import load_active
from frob.tickets._models import _SEMVER_SPRINT_RE, normalize_milestone
from frob.tickets._store import ledger_lock, write_ticket

_log = get_logger(__name__)


# frob:ticket T-5133
# frob:doc docs/modules/tickets-data-storage.md#sprint-is-a-time-box-milestone-is-the-version-t-5133  # noqa: E501
# tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone.test_migrates_unmilestoned_ticket  # noqa: E501
class SprintMigrationReport(BaseModel):
    """`frob ticket sprint migrate`'s one-shot summary (T-5133): counts
    only, no per-ticket detail (a per-ticket log line is emitted at INFO
    for each mutation, this is the roll-up an operator/CI step checks)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scanned: int = 0
    #: sprint was semver-shaped and milestone was unset -- migrated cleanly.
    migrated: int = 0
    #: sprint was semver-shaped but milestone ALREADY held a DIFFERENT
    #: value -- sprint still cleared, but the conflicting value was kept
    #: on milestone and logged, never silently overwritten.
    conflicts: int = 0
    #: ticket carried a v-prefixed milestone (regardless of sprint) --
    #: normalized to the bare form.
    normalized: int = 0


# frob:ticket T-5133
def _migrate_one_ticket(root: Path, ticket) -> tuple[str, int, int, int]:  # noqa: ANN001
    """One ticket's worth of `migrate_sprint_to_milestone`'s repair
    (split out of that function to keep it under ARCH001's threshold,
    T-1813's precedent for the same split reason): computes the field
    update (if any), writes it, and returns `(update_kind, migrated,
    conflicts, normalized)` deltas for the caller's running totals.
    `update_kind` is `"none"`/`"migrated"`/`"conflict"`/`"write_failed"`
    -- purely descriptive, the caller only branches on the int deltas."""
    update: dict[str, object] = {}
    migrated = conflicts = normalized = 0

    sprint_is_semver = bool(ticket.sprint and _SEMVER_SPRINT_RE.match(ticket.sprint))
    if sprint_is_semver:
        stripped = normalize_milestone(ticket.sprint)
        if ticket.milestone is None:
            update["milestone"] = stripped
            migrated = 1
        elif normalize_milestone(ticket.milestone) != stripped:
            conflicts = 1
            _log.warning(
                "sprint migrate: %s sprint=%r conflicts with existing "
                "milestone=%r -- keeping milestone, clearing sprint "
                "anyway (T-5133)",
                ticket.id,
                ticket.sprint,
                ticket.milestone,
            )
        update["sprint"] = None

    if ticket.milestone is not None:
        normalized_milestone = normalize_milestone(ticket.milestone)
        if normalized_milestone != ticket.milestone:
            update["milestone"] = normalized_milestone
            normalized = 1

    if not update:
        return "none", 0, 0, 0
    updated = ticket.model_copy(update=update)
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        _log.error(
            "sprint migrate: %s write failed: %s", ticket.id, write_result.danger_err
        )
        return "write_failed", 0, 0, 0
    _log.info("sprint migrate: %s -> %s", ticket.id, update)
    return "written", migrated, conflicts, normalized


# frob:ticket T-5133
# frob:doc docs/modules/tickets-data-storage.md#sprint-is-a-time-box-milestone-is-the-version-t-5133  # noqa: E501
# tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone.test_conflict_keeps_existing_milestone  # noqa: E501
# tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone.test_normalizes_v_prefixed_milestone  # noqa: E501
# tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone.test_idempotent_second_run_is_a_noop  # noqa: E501
def migrate_sprint_to_milestone(root: Path) -> SprintMigrationReport:
    """`frob ticket sprint migrate` (T-5133): the one-shot, idempotent
    repair described in this module's docstring. Runs OUTSIDE the normal
    single-field setter ceremony (no `TriageChangeEntry`/lease check per
    ticket -- this is a bulk ledger repair, the same "outside the
    ordinary mutation path" posture `frob ticket admin reconcile`
    already has) but still under `ledger_lock` for the whole pass, one
    lock acquisition, not one per ticket. Only OPEN tickets are touched
    (`load_active`'s own view) -- done/dropped/archived tickets are never
    rewritten, matching every other T-5132/T-5133 field's "never touches
    terminal tickets" posture. Per-ticket work is `_migrate_one_ticket`;
    this function is the load, lock, iterate, and roll-up totals."""
    loaded = load_active(root)
    if loaded.is_err:
        _log.error("sprint migrate: could not load active queue: %s", loaded.danger_err)
        return SprintMigrationReport()

    scanned = migrated = conflicts = normalized = 0
    with ledger_lock(root):
        for ticket in loaded.danger_ok.tickets.values():
            scanned += 1
            _kind, d_migrated, d_conflicts, d_normalized = _migrate_one_ticket(
                root, ticket
            )
            migrated += d_migrated
            conflicts += d_conflicts
            normalized += d_normalized

    _log.info(
        "sprint migrate: scanned=%d migrated=%d conflicts=%d normalized=%d",
        scanned,
        migrated,
        conflicts,
        normalized,
    )
    return SprintMigrationReport(
        scanned=scanned,
        migrated=migrated,
        conflicts=conflicts,
        normalized=normalized,
    )


__all__ = ["SprintMigrationReport", "migrate_sprint_to_milestone"]

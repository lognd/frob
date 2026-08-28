---
id: T-3230
title: Audit failed-subprocess-folded-into-positive-finding sites (T-3216 sibling
  survey)
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reconcile.py
- tests/test_ticket_reconcile.py
- src/frob/tickets/_archive.py
- tests/test_tickets_organization.py
- src/frob/tickets/_models.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: triage narrowed fix to the reconcile stale-hold worktree-measurement site;
    remainder split into follow-up tickets
  actor: logan
  at: '2026-08-28'
- op: remove
  glob: src/frob/gates/
  reason: triage narrowed fix to the reconcile stale-hold worktree-measurement site;
    remainder split into follow-up tickets
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: triage narrowed fix to the reconcile stale-hold worktree-measurement site;
    remainder split into follow-up tickets
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: triage narrowed fix to the reconcile stale-hold worktree-measurement site;
    remainder split into follow-up tickets
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_archive.py
  reason: the T-3230 fix changes _live_worktrees return type; _archive.py::_refuse_archive_if_worktrees_live
    is the one other caller and must be updated to keep working and to fail closed
    (refuse archive) rather than fail open (allow archive) on an unmeasurable read
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets_organization.py
  reason: must-fire/must-stay-quiet fixtures for the new _refuse_archive_if_other_worktrees_live
    unmeasurable-git-worktree-list fail-closed path
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/tickets/_models.py
  reason: new TicketError.ArchiveWorktreeMeasurementFailed variant needed to distinguish
    the unmeasurable-worktree-list refusal from ArchiveLiveLeaseExists
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'AFFECT001: document the new TicketError.ArchiveWorktreeMeasurementFailed
    variant'
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3216 fixed one instance of this defect class in _land_git_ops.py/_land.py:
a failed git status subprocess call was folded into "found uncommitted
work" (a POSITIVE finding) instead of a distinct UNMEASURABLE state, and
the resulting DirtyMain refusal message asserted uncommitted work existed
and told the reader retrying could not help -- backwards for the common
transient-contention case.

MEASURED (T-3216's own scope, grep count only, not triaged): 37 call
sites across src/frob/tickets/ and src/frob/gates/ share the exact shape
spawned.is_err or spawned.danger_ok.returncode != 0 -- each is a
candidate for the same class of bug (a failed spawn collapsed into some
other return value the caller cannot tell apart from a genuine negative/
positive result). NOT triaged individually here -- T-3216's scope was
the DirtyMain path only. Someone needs to walk each of the 37, check what
it returns on spawn failure, and confirm the caller can tell "unmeasured"
apart from "measured and found nothing" (or "measured and clean").

Search used: git grep -n "spawned.is_err or spawned.danger_ok.returncode != 0" -- src/frob/tickets/ src/frob/gates/

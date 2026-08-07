---
id: T-1750
title: frob ticket archive corrupts an in-flight worktree's ledger with duplicate
  ids; TICK003 forces it at a non-quiet moment
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_archive.py
- src/frob/tickets/_land_ledger_merge.py
- src/frob/gates/_tickets_gate.py
- tests/test_tickets_organization.py
- docs/modules/tickets.md
- tests/test_gates_tickets_hygiene.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_tickets_hygiene.py
  reason: TICK003's default warn/error thresholds are changing (20/60 -> 10/400) as
    part of this ticket's fix; that file hardcodes the old defaults (21/61 closed
    tickets) and needs updating to match, or it goes red as a direct, mechanical consequence
    of this ticket's own change
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1750's new archive-refuses-live-worktrees guard (v1 path) breaks two pre-existing
    splice-discipline regression tests (TestArchiveSpliceDiscipline, TestArchiveResurrection)
    that deliberately call archive() with a live sibling worktree present to prove
    splice correctness -- they need force=True added to keep testing splice correctness
    rather than tripping the new precondition guard
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_refuses_when_another_worktree_exists
- tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_force_overrides_the_live_worktree_refusal
- tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees::test_no_other_worktree_archives_normally
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_warn_threshold_warns
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors
- tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected
- tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive
designated_repro_test: null
threat: null
component: null
---
`frob ticket archive` is not safe against in-flight worktrees, documents
that requirement in prose, and does not enforce it. TICK003 then FORCES
the operation at an arbitrary moment mid-drive.

What happened, 2026-08-07. TICK003 crossed its threshold (61 closed
tickets un-archived against 60) and began refusing every land repo-wide,
including a completed ticket unrelated to the housekeeping. The
coordinator checked for in-flight LANDS, found none, and ran `frob ticket
archive` -- 62 tickets moved from `tickets.md` to `tickets-archive.md`.

But an agent's WORKTREE was still live with a pre-archive `tickets.md`.
Its next `git merge main` produced a ledger with DUPLICATE TICKET IDS
across active and archive (`DuplicateId` on sweep): the merge driver saw
a deletion on one side and an addition on the other rather than
recognising a MOVE between two files.

Recovery cost that agent a full playbook-10b pass: restore both ledger
files from main, re-apply every scope/evidence/done-report mutation
through the `frob ticket` CLI (never by hand), catch and refile a DROPPED
DRAFT before it became a phantom-citation TICK006 finding, and re-run
`frob ticket start` because the restore had reverted the ticket's own
in-progress transition. All of that to recover from a routine
housekeeping command.

Three separable defects:

1. ARCHIVE DOES NOT ENFORCE ITS OWN PRECONDITION. Its documentation asks
   for "a quiet window, no in-flight worktrees". It should REFUSE when
   `git worktree list` shows any agent worktree, naming them, with
   `--force` for a caller who knows better. A precondition that exists
   only in prose is not a precondition -- the coordinator read that line,
   checked for in-flight lands, and still got it wrong, because "no
   in-flight worktrees" and "no land currently running" are different
   conditions and only one of them is easy to check.

2. THE MERGE DRIVER DOES NOT UNDERSTAND AN ACTIVE->ARCHIVE MOVE. A
   ticket relocated between the two ledger files is a MOVE, and the
   splice should reconcile it as one. Today it yields duplicate ids,
   which is the single most damaging ledger state -- `load_queue` refuses
   outright, so every gate goes down at once. T-1721 taught the general
   lesson here: when the splice cannot answer a question correctly it
   must refuse and name the conflict, never produce a corrupt merge.

3. TICK003 FORCES A QUIET-WINDOW OPERATION AT A NON-QUIET MOMENT. The
   gate blocks all landing until someone runs a command that requires
   conditions the gate never checks. That is a deadlock by construction:
   the more agents are landing, the sooner the threshold trips, and the
   less safe the remedy is. Either the threshold should WARN far enough
   ahead to be scheduled deliberately (it is a housekeeping floor, not a
   correctness one, so blocking on it is disproportionate), or archiving
   must become safe enough to run at any time -- which is defect 2.

Preferred direction: fix 2 so archiving is merge-safe, add 1 as the
belt-and-braces guard, and soften 3 to a warning with a much lower
warn-threshold and an ERROR only far above it.

Regression coverage must include the real shape: a worktree branched
BEFORE an archive pass, merging main AFTER it, asserting the merged
ledger has no duplicate ids and no dropped drafts. A test that archives
with no worktrees present proves nothing about the failure mode.
---
id: T-2714
title: A killed land strands its staged snapshot in the shared root, DirtyMain-blocking
  the whole fleet
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/tickets/_land_git_ops.py
- tests/test_ticket_leases.py
- tests/test_ticket_leases_dispatch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: T-2714's own tests for run()'s pre-dispatch reconciliation wiring, if that
    test module exists as the dispatch-guard test home
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: T-2714's own tests for run()'s pre-dispatch reconciliation wiring, if that
    test module exists as the dispatch-guard test home
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: T-2714's own tests for run()'s pre-dispatch reconciliation wiring, if that
    test module exists as the dispatch-guard test home
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_ticket_leases.py
  reason: T-2714's own tests for run()'s pre-dispatch reconciliation wiring, if that
    test module exists as the dispatch-guard test home
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_ticket_leases_dispatch.py
  reason: T-2714's own tests for run()'s pre-dispatch reconciliation wiring, if that
    test module exists as the dispatch-guard test home
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'T-2714: TICK011 needs a literal Filed: line in the Done report'
  actor: logan
  at: '2026-08-20'
  old_length: 3273
  new_length: 3448
evidence:
- tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_no_marker_is_a_silent_no_op
- tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_finishes_a_killed_commit_when_the_staged_content_is_still_there
- tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_already_advanced_tip_just_clears_the_marker
- tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_nothing_dirty_clears_the_marker_silently
- tests/test_ticket_leases.py::TestLedgerCommitRepairMarker::test_finish_failure_leaves_the_marker_and_the_dirt_for_a_human
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3052ee7bf81fc91ffa40c464c67f77c34c154f3d
---
## Measured three times in one session, 2026-08-20

A `frob ticket land` killed by its own `timeout 540` wrapper leaves the
SHARED ROOT dirty with the land's staged snapshot. A dirty root
DirtyMain-blocks every other agent's land, so one agent's killed land
halts the entire fleet.

Instance 1 (T-2696), captured live:

    M  src/frob/gates/_pii_structural/_emails.py
    M  src/frob/gates/_pii_structural/_keywords.py
    M  src/frob/gates/_pii_structural/_node_index.py
    M  src/frob/gates/_pii_structural/_python_fields.py
    M  tests/test_pii_structural_gate.py
    A  tickets/T-2696/done-report.md
    M  tickets/T-2696/ticket.md
    R  tickets/T-draft-0ca6b1ef/ticket.md -> tickets/T-2711/ticket.md
    A  tickets/T-2712/ticket.md

Everything staged in the index, no MERGE_HEAD, no rebase-merge. Exit 124
(the wrapper's own timeout), no surviving process. The kill landed during
POST-MERGE RE-VERIFICATION, not at the commit step.

Instance 2: a `frob ticket new` whose ledger commit lost a race left
`T-draft-800bd159` plus a modified ticket file stranded the same way.

Instance 3: an agent's `frob ticket scope` mirror-write lost its commit to
a concurrent ledger write, leaving `M tickets/T-2707/ticket.md`.

So this is NOT specific to the timeout path -- any land or ledger write
interrupted between staging and committing strands content in the shared
root and blocks the fleet.

## Why this is separate from T-2679

T-2679 (landed, 2d5ab2161) closed the state-integrity half: a killed land
no longer leaves a ticket reading `state: done` with nothing recording it,
via a new finalize-repair marker. That fix deliberately did NOT address the
shared-root residue, and that was the right call -- different concern,
wider blast radius.

## What makes it expensive

The residue is INDISTINGUISHABLE, to another agent, from abandoned dirt.
Every agent that found it correctly refused to touch it, because guessing
wrong either drops real content or clobbers a live write. So the fleet
stalls until a coordinator adjudicates by reading the staged diff by hand
to decide commit-vs-reset. That happened three times today.

In all three cases the staged tree turned out COMPLETE and CORRECT, and
recovery was simply `git commit` of what was already staged.

## Required shape

Either the land does not stage into the shared root until it can commit
atomically, or an interrupted land leaves a marker the next land (or
`fleet_status`) reconciles automatically and LOUDLY -- the same posture
T-0907 and T-2679's finalize-repair marker already take for ticket state.
An agent finding staged content in the root should be able to learn from
the tool whose it is and whether it is complete, rather than inferring it
from a diff.

## Positive controls, both directions

- a land killed mid-stage leaves the shared root committable-or-clean, and
  a subsequent land by an UNRELATED ticket is not DirtyMain-blocked
- a genuinely dirty root from real uncommitted work is STILL refused
- the reconciliation names the owning ticket and worktree, loudly, rather
  than silently absorbing content

## Do not weaken DirtyMain

It is the guard that stops agents clobbering each other. The bug is that a
killed land CREATES the condition DirtyMain refuses on -- not that it
refuses.

Filed: candidate follow-up noted in the Done report (land's own squash-residue reclaim staying reset-only, not finish-capable) -- not filed as a ticket yet; no other residue
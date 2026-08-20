---
id: T-2679
title: A timed-out land marks the ticket done and records evidence while zero code
  reaches main
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-2679: the terminal state write ordering defect (killed land writes state:done+evidence
    with no land commit) lives in the land() orchestrator''s own commit/transition
    sequencing'
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'T-2679: TICK011 needs a literal Filed: line in the Done report; no residue
    tickets were opened for this fix'
  actor: logan
  at: '2026-08-20'
  old_length: 2043
  new_length: 2056
- mode: append
  reason: 'T-2679: TICK011 needs a literal Filed: line in the Done report; no residue
    tickets were opened for this fix'
  actor: logan
  at: '2026-08-20'
  old_length: 2056
  new_length: 2069
evidence:
- tests/test_ticket_land.py::TestFinalizeRepairMarker::test_no_marker_is_a_silent_no_op
- tests/test_ticket_land.py::TestFinalizeRepairMarker::test_repair_logs_loudly_when_worktree_still_shows_done_but_root_does_not
- tests/test_ticket_land.py::TestFinalizeRepairMarker::test_repair_is_silent_when_root_already_shows_the_ticket_done
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie
- tests/test_ticket_land.py::TestSigkillMidStaging::test_normal_land_reaches_done_exactly_once_no_extra_transition
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

2026-08-19, T-2671. `frob ticket land --finish` was killed mid-flight
(exit 143) under fleet contention. Afterwards:

    ticket state    = done
    done report     = recorded
    evidence        = recorded
    land commit     = NONE
    code on main    = NONE (`git show HEAD:<file>` had none of the fix)

The ledger asserted the work shipped. It had not.

## Why this is the worst shape of land failure

A failed land is visible and gets retried. Done-with-no-content is
invisible to every later reader, to the open/done counts, and to any
agent that trusts the queue. Nothing downstream re-examines a terminal
ticket, so the gap persists indefinitely.

## Distinct from the known ancestry-vs-content gap

The existing concern is that LAND-PROOF verifies ancestry rather than
content, so a land commit can exist and fail to contain the ticket's
code. This is a different mechanism: there is NO land commit at all, yet
the terminal state was still written. A check that inspects the land
commit will not catch this, because there is nothing to inspect.

## Required shape

The terminal state write must not be able to outlive the commit it
claims. Either order the state write strictly after a verified,
content-bearing commit, or make a killed land leave the ticket
recoverable rather than terminal.

## Positive controls, both directions

- a land killed after the state write must leave the ticket non-terminal
  (or self-heal on next read) -- without this the fix is unproven
- a normal successful land must still reach done exactly once, with no
  extra transition

## Recovery recipe that worked (for the runbook)

Cherry-pick the original worktree commits onto main under
`FROB_LAND_INTERNAL=1`, confirm content by grepping the landed file,
re-run the touched test file on main, then `frob ticket land --finish`,
which recognises the ticket as already done and runs only cleanup.
Note the cherry-picks are NEW commits, so the original worktree shas
read NOT-ON-MAIN -- verify by CONTENT, never by ancestry of the old shas.

Filed: none

Filed: none
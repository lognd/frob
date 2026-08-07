---
id: T-1036
title: frob ticket sweep/done-report can rewrite unrelated ticket blocks when main
  advances mid-write
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
designated_repro_test: null
acceptance:
- text: GIVEN the ledger changes on disk between a ticket verb's read and write THEN
    the verb refuses and retries from fresh state instead of writing a stale full-file
    image
  evidence:
  - tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
threat: null
component: null
---
Observed repeatedly by the T-0690 agent under high ledger churn (many concurrent lands): frob ticket sweep and done-report intermittently rewrote OTHER tickets' sections in tickets.md, caught only by a git diff main -- tickets.md check after each CLI call and repaired by splicing the agent's own block onto a fresh main copy. Root-cause the read-modify-write path: it likely reads the whole ledger, mutates one block, and writes the whole file back without checking the on-disk file changed since read (the T-0889 ledger_digest optimistic-concurrency guard may not cover these two verbs, or the worktree copy diverges from the merged state). Fix = extend the optimistic-concurrency digest guard to every ledger-writing verb and add a churn regression test that interleaves a concurrent block edit between read and write.
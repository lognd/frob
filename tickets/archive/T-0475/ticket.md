---
id: T-0475
title: 'ticket land / merge-driver splice resurrects stale ticket states from the
  worktree branch: landing T-0471 re-opened T-0160/T-0187 (queued on main) to in-progress
  because the pre-fork worktree ledger had them in-progress -- splice must not revert
  main''s newer transition for tickets other than the one being landed'
state: dropped
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
subsumed by T-0479: `_splice_only_ticket` (T-0479's Done report) implements
exactly the fix this ticket asked for -- splicing only the landed ticket's
own block onto main's current ledger instead of a whole-ledger merge that
can resurrect a stale sibling state.
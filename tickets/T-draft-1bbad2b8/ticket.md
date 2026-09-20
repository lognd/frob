---
id: T-draft-1bbad2b8
title: ticket start transition must be a ledger write carrying worktree and branch,
  not a lease side effect
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: T-4651
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_leases.py
- tests/unit/tickets/test_start_transition_ledger.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20 (scratchpad/STRANDED.md, 54 in-progress tickets audited): the QUEUED to IN_PROGRESS edge in src/frob/tickets/_evidence.py (the IN_PROGRESS branch near line 281 and the lease record/release near lines 1286-1294) writes only the gitignored lease file; the root ledger learns of the transition only through later mirror commits, so 32 of 71 leases were held against tickets the ledger still called queued and only one ticket (T-4660) carried an explicit start-transition commit. Fix: make the transition commit the root ledger through commit_ticket_ledger_change in the same operation that records the lease, and store worktree and branch as fields in tickets/<id>/ticket.md (the durable record), not only in .git/frob-leases/<id>.json (record_lease near _leases.py line 783). Positive control: after frob ticket work on a fixture ticket, the ledger commit exists on the root branch and the ticket file names the worktree path and branch; frob ticket list at the root shows in-progress without any worktree mirror.

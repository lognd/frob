---
id: T-2108
title: frob ticket land --finish re-attempts a full land on an already-verified ticket
  instead of pure cleanup, failing BUG002 because main now contains the fix
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_finish_idempotent.py
- frob.lock
- tickets/T-2165/ticket.md
- tickets/T-2166/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_finish_idempotent.py
  reason: repro test
  actor: logan
  at: '2026-08-11'
- op: add
  glob: frob.lock
  reason: frob.lock is the ack registry my own frob ack calls wrote to; the two draft
    tickets are carried by this land so the cache-widening finding and doc-drift follow-up
    reach main
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2165/ticket.md
  reason: frob.lock is the ack registry my own frob ack calls wrote to; the two draft
    tickets are carried by this land so the cache-widening finding and doc-drift follow-up
    reach main
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2166/ticket.md
  reason: frob.lock is the ack registry my own frob ack calls wrote to; the two draft
    tickets are carried by this land so the cache-widening finding and doc-drift follow-up
    reach main
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---

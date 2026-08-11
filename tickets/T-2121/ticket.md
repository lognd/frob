---
id: T-2121
title: rapid-debt.jsonl is a shared append-only file every rapid land touches, so
  any ticket declaring it blocks every other land with CrossTicketLeakage (unclaimed)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_machinery_owned_leakage.py
- src/frob/tickets/_land_release.py
- rapid-debt.jsonl
- tickets/T-2094/ticket.md
- tickets/T-2123/ticket.md
- tickets/T-2124/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_machinery_owned_leakage.py
  reason: self-contained repro test for T-2121; imports the shared land-owned-files
    constant
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: self-contained repro test for T-2121; imports the shared land-owned-files
    constant
  actor: logan
  at: '2026-08-11'
- op: add
  glob: rapid-debt.jsonl
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2094/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2123/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tickets/T-2124/ticket.md
  reason: cumulative branch diff from earlier tickets in this same series worktree
    (T-2094 drop, T-2118->T-2123 promotion, verification-probe cleanup), not this
    ticket's own work
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it
designated_repro_test: tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it
threat: null
component: null
anchor: false
anchor_reason: null
---

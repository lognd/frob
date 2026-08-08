---
id: T-1819
title: SCOPE001 false-positives on a ticket's own tickets/<id>/** shard file (LEDGER_PATH
  predates sharded ledger)
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/gates/__init__.py
- tests/test_tickets.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: SCOPE001's own scope_gate check site needs to pass ticket_id through to
    scope_matches for the fix to take effect
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets.py
  reason: unit tests for the sharded-ledger scope fix
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_gates.py
  reason: unit tests for the sharded-ledger scope fix
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope
- tests/test_gates.py::TestScopePrework::test_scope001_own_sharded_ledger_shard_implicitly_in_scope
- tests/test_gates.py::TestScopePrework::test_scope001_another_tickets_shard_still_out_of_scope
designated_repro_test: null
threat: null
component: null
---
`frob.tickets._models.scope_matches`/`LEDGER_PATH` implicitly treats
`tickets.md` as always-in-scope for every ticket (the single-file ledger
era), but this repo has since moved to sharded per-ticket files under
`tickets/<id>/*` (e.g. `tickets/T-1817/ticket.md`, written by `frob
ticket start`'s own auto-commit). SCOPE001 (`scope_gate`) does not know
about the sharded form, so any ticket whose own bookkeeping shard gets
touched (routine `frob ticket start`/`sweep` auto-commits) fires a false
SCOPE001 against its own declared scope unless the ticket happens to
also declare `tickets/<id>/**` explicitly.

Found while working T-1817 (which fixed the sibling false-positive in
`frob.gates._b9_exempt_file` for the same sharded-ledger gap, but that
fix only covers the unscoped/no-active-ticket B9 path, not
`scope_gate`'s own per-ticket declared-scope check).

Fix: extend `scope_matches`/the implicit-ledger rule so a ticket's own
`tickets/<id>/**` shard is always in scope for that ticket, mirroring
`LEDGER_PATH`'s existing `tickets.md`-always-in-scope treatment.
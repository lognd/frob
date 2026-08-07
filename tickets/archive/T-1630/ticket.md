---
id: T-1630
title: 'renumber(root) has no v2 stale-snapshot guard: wire ledger_digest_map into
  _new_renumber'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_store.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_store_stale_snapshot.py::TestRenumberV2StaleSnapshotGuard::test_renumber_root_refuses_when_a_ticket_changes_under_it
designated_repro_test: null
threat: null
component: null
---
`renumber(root)` (the plain contiguous-renumber path in
src/frob/tickets/_new_renumber.py, distinct from `renumber_one`) has no
v2-mode dispatch of its own -- it calls `write_all(root, new_map,
expected_digest=digest)` where `digest = ledger_digest(ledger_path(root))`,
a v1 monofile digest. In a v2-mode repo this string is meaningless
(ledger_path(root) does not exist), and T-1588's write_all now correctly
treats a bare str expected_digest in v2 mode as "no check requested"
rather than misapplying it -- but that means renumber(root) in a v2 repo
gets NO stale-snapshot protection at all: a sibling process's write between
this function's load_all and its write_all is silently clobbered by the
wholesale rewrite, same T-0680 shape T-1588 closed for write_all/
write_archive's primitive.

Fix: give renumber(root) a v2-aware digest snapshot, using
frob.tickets._store.ledger_digest_map(root) in place of the v1
ledger_digest(ledger_path(root)) call, mirroring how renumber_one already
dispatches to renumber_one_v2 for its own v2 path. Filed while working
T-1588 (out of scope there -- T-1588 was scoped to src/frob/tickets/
_store.py only).
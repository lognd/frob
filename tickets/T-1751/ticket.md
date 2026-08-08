---
id: T-1751
title: revisit WIRE001 waiver follow_up citation orphaned by T-1487's close
state: done
kind: docs
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_tickets_lease.py
- tickets/T-1751/**
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1751/**
  reason: SCOPE001 flags the ticket's own ticket.md and the rapid-debt log this land
    profile writes
  actor: logan
  at: '2026-08-08'
- op: add
  glob: rapid-debt.jsonl
  reason: SCOPE001 flags the ticket's own ticket.md and the rapid-debt log this land
    profile writes
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets_lease.py::TestClusterScopeConflict::test_refuses_when_union_scope_collides_with_a_foreign_lease
designated_repro_test: null
threat: null
component: null
---
Found while landing T-1487 (rust python tree-extraction kernel carrier):
tests/test_tickets_lease.py:449 carries a `frob:waive WIRE001 ...
follow_up="T-1487"` directive on `_write_ticket_file`. T-1487's own
scope (frob-core/**, tests/unit/test_extract_native.py, docs/modules/
lang.md, docs/modules/dup.md) never touched this file or fixture, and
T-1487 is closing as delivered-by-T-1220 with no new code -- so this
citation cannot legitimately resolve against T-1487 any longer.

Re-verify whether `_write_ticket_file` still needs the WIRE001 waiver
at all (confirm it is still test-fixture-only, called only by
TestClusterScopeConflict's own methods in this same file per the
existing waiver reason), and either drop the waiver if a real caller
now exists or re-confirm/refresh it with a live follow_up ticket.
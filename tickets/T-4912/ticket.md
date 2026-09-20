---
id: T-4912
title: Fix stale DOC006 pointers accumulated in ticket bodies (CI doc004/doc006 live-repo
  gate)
state: done
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3822/ticket.md
- tickets/T-3823/ticket.md
- tickets/T-4668/ticket.md
- tickets/T-4670/ticket.md
- tickets/T-4691/ticket.md
- tickets/T-4693/ticket.md
- tickets/T-4703/ticket.md
- tickets/T-4741/ticket.md
- tickets/T-4742/ticket.md
- tickets/T-4808/ticket.md
- tickets/T-5135/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-5135/ticket.md
  reason: stale DOC006 pointer surfaced by the post-merge live-repo test; same class
    as the ticket's other bodies
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
designated_repro_test: null
acceptance:
- text: test_doc004_doc006_zero_against_live_repo passes with zero DOC004/DOC006 findings
  evidence:
  - tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/test_docptr_gate.py TestDoc004Doc006ZeroOnFrobsOwnRepo test_doc004_doc006_zero_against_live_repo fails with 13 unresolved DOC006 pointers accumulated in ticket bodies (stale file paths, config-section refs, and CLI invocation refs that no longer resolve). Fix each pointer to resolve, or add a reasoned frob:waive DOC006 if intentionally illustrative or future-facing, in each named ticket.md.
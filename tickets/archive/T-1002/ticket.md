---
id: T-1002
title: 'append-only merge zones: severity block, rule registry, remediation logs never
  conflict'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: high
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/**
- frob.toml
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1002 needs its own guard-suite test class in the shared land test file,
    same as every other _land.py ticket
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses
- tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
- tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates
designated_repro_test: null
acceptance:
- text: given two worktrees each appending a distinct severity line and rule id, when
    both land sequentially, then the second land succeeds without manual conflict
    resolution and both entries are present
  evidence:
  - tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
threat: null
component: null
---
Churn item 3 (~8 occurrences): [gates.severity], _KNOWN_GATE_RULES, and docs/audits remediation logs conflict on nearly every concurrent land and are always resolved keep-both-chronological. Register these as append-only union zones (delimiting marker comments) with land-side union merge, so concurrent appends compose without conflict; refuse only true same-key contradictions (e.g. two different severities for one rule).
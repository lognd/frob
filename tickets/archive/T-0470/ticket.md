---
id: T-0470
title: 'waiver over-breadth + class-ignore placement lint: (1) _match_waiver matches
  symref-LESS (file-scoped) findings by file OR package-PREFIX, so one frob:waive
  can suppress broadly; (2) warn when a class-bound frob:waive/directive is not at
  the class top (likely mis-scoped)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0470 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestTestGate::test_waive003_flags_waiver_reaching_multiple_packages
designated_repro_test: null
threat: null
component: null
---

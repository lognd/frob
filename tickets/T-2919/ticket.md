---
id: T-2919
title: 'PLATFORM001 gate: every POSIX-only primitive must declare a cross-platform
  path or refuse LOUDLY, never warn-and-continue'
state: done
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_walk_lint.py
- tests/test_walk_lint_gate.py
- docs/modules/gates.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: PLATFORM001 detector rides alongside WALK gate
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_walk_lint_gate.py
  reason: PLATFORM001 tests + doc section
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: PLATFORM001 tests + doc section
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_waive.py
  reason: register PLATFORM001 in _KNOWN_GATE_RULES
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_walk_lint_gate.py::TestPlatform001::test_warn_and_continue_fires
- tests/test_walk_lint_gate.py::TestPlatform001::test_loud_refusal_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001::test_no_platform_probe_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001::test_gate_fires_end_to_end
- tests/test_walk_lint_gate.py::TestPlatform001::test_gate_stays_quiet_on_properly_guarded_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

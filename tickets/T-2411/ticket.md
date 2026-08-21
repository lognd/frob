---
id: T-2411
title: wire LANG004 capability_conformance_gate into the check job table
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: wiring LANG004 into a --only-reachable gates-fast stage group requires this
    file too, same T-1044/T-1340 lesson its own comment names -- registered-but-unreachable
    is the exact defect class this ticket exists to avoid
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: wiring regression test for LANG004's frob check job-table registration,
    same precedent as test_deprecated_is_registered_in_all_gates
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_is_registered_in_all_gates
- tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 918ec0c7d0675c95e5afa3a468fe3738c13dbc56
---
T-2365 built capability_conformance_gate (LANG004, src/frob/gates/_lang_conformance.py) -- the behavioral half of the adapter-capability axis, verified directly by tests/test_lang_conformance_gate.py but NOT wired into frob check's job table (src/frob/gates/__init__.py's _GATE_JOBS/_STAGE_GROUPS dicts, mirroring lang_conformance/lang_project_conformance's own entries) because that file was out of T-2365's declared scope. Wire it in the same way lang_conformance_gate/project_lang_conformance_gate are wired (search for 'lang_conformance' in src/frob/gates/__init__.py for the exact pattern: job table entry, stage group membership, --only list membership).
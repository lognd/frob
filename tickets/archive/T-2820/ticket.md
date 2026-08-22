---
id: T-2820
title: REF001/REF002 systematic collapse (glob entrypoints) + promote to error
state: done
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2369
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- tests/unit/gates/test_refs.py
- docs/modules/gates.md
- docs/modules/tickets-data-storage.md
- docs/index.md
- docs/design/test005-ratchet-schedule.md
- docs/investigations/T-2782-land-serialization.md
- docs/investigations/T-2790-check-stage-profile.md
- docs/investigations/T-2796-backlog-reproduction.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
designated_repro_test: null
acceptance:
- text: given REF001/REF002, when frob check --json runs, then zero findings remain
  evidence:
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files
  - tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files
- text: given src/frob/gates/_refs.py's REF001/REF002 severity, when read, then it
    is ERROR not WARNING
  evidence:
  - tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3e19aaf5f85dc630f8f3d34420001cf89f8f1c84
---
Child of T-2369: REF001 (275->0) and REF002 (6->0) both fully burned down and promoted WARN->ERROR. REG008 (18 remaining) stays on the parent T-2369 for a separate batch.
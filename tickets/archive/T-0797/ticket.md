---
id: T-0797
title: 'gates: DEPR001-004 are dead code -- ''deprecated'' missing from _ALL_GATES
  so no frob check run evaluates them'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- src/frob/check/__init__.py
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/docs_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: deprecated gate now real in _ALL_GATES; test_available_stages_cover_every_gate_and_tool
    requires it land in a _STAGE_GROUPS alias too, structurally the same change
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/map_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: 'DEPR002 rebind: directives must cite an open ticket; T-0802 is the sunset-execution
    ticket'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates
- tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
designated_repro_test: null
acceptance:
- text: GIVEN a frob:deprecated directive in the tree WHEN frob check runs (no --only
    filter) THEN the deprecated gate evaluates and DEPR003 in-window warnings appear
    in gate output; frob check --only deprecated is accepted; a regression test locks
    the gate registration
  evidence:
  - tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates
  - tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch
  - tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
threat: null
component: null
---
Promotion of T-0580's worktree draft f226d099 (worktree removed at land before renumbering; refiled by coordinator). deprecated_gate and DEPR001-004 are implemented and unit-tested but 'deprecated' is absent from _ALL_GATES, so no real check run ever evaluates them -- the T-0580 deprecations are currently enforced by nothing (catalogued-is-not-enforced class). One-line registration + regression test. CRITICAL because the user's deprecation decision (map/outline/xref/docs-search, sunset 2026-10-01) silently has no teeth until this lands.
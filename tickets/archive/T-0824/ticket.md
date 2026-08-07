---
id: T-0824
title: protocol_summary gate missing from _STAGE_GROUPS coverage
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
designated_repro_test: null
threat: null
component: null
---
tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
fails on main (post T-0813 merge): the new `protocol_summary` gate
(src/frob/gates/_protocol_summary.py, wired into _ALL_GATES) was not added
to any `_STAGE_GROUPS` membership in src/frob/check/__init__.py, so
`frob check --only <group>` can never reach it and the coverage test fails.

Found while verifying T-0599 (frob-exports triage); out of that ticket's
scope (src/frob/check/__init__.py's _STAGE_GROUPS membership, not its
exports). Fix: add "protocol_summary" to the appropriate _STAGE_GROUPS
bucket in src/frob/check/__init__.py (likely gates-native or gates-fast
depending on cost) and re-run the coverage test.
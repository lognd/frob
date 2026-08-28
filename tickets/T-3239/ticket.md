---
id: T-3239
title: Register TDD001/VMOD001/VERSION001 in _KNOWN_GATE_RULES (REG002 on check-coverage.yaml)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-3224: docs/design/registry/check-coverage.yaml declares handled_by:TDD001, handled_by:VMOD001, and handled_by:VERSION001 entries, but none of those three rule ids is registered in src/frob/gates/_waive.py::_KNOWN_GATE_RULES, even though all three gates are live (frob.gates._tdd_order, frob.gates._vmodel, frob.gates._version_coupling) and TDD001/VMOD001 already got their frob:enforces CHK-GATE-<RULE> directives added under T-3224. This produces 3 REG002 (dangling enforcement reference) findings, failing tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations. T-3224 could not fix this itself: T-2931 holds a live in-progress lease on src/frob/gates/_waive.py for an unrelated WIRE001 change. Fix: once that lease clears, add TDD001, VMOD001, VERSION001 to _KNOWN_GATE_RULES (same one-line-per-id pattern as the CPLACE001/CPLACE002 entries T-3218 added).
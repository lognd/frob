---
id: T-5301
title: Gate rule-id registration and severity wiring for WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- frob.toml
- docs/modules/gates.md
- tests/gates_suite/test_coverage.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_coverage.py
  reason: positive-control test for the WAIVE002 reserved-rule-id round-trip
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: keep the closed-set gate_rule_entries registry in lockstep with _KNOWN_GATE_RULES,
    T-5190 pattern
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_loads_without_error
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_waive002_reserved_websec_id_round_trips_clean
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_waive002_flags_unknown_rule_id_as_ineffective
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_is_frozenset
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5301
branch: t-5301
---
Add all WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL rule-id ranges to _KNOWN_GATE_RULES as a reserved block (placeholder comments naming the future ticket, same shape as PERF015-018's T-5136 reservation) so frob:waive on an unshipped rule id fails loud, not silently. Add a [gates.severity] block: WEBSEC/COMPLY/A11Y default error; SEO/WEBPERF default warn until a repo opts to promote (PERF015-018 precedent). LAUNCH severity is handled separately by WEBSUB-4 (new advisory tier), not this leaf. Positive-control: frob:waive WEBSEC101 reason=... round-trips through known-rule-id checks without raising UnknownRuleId once this leaf lands. Doc: docs/modules/gates.md's rule table (skeleton rows).
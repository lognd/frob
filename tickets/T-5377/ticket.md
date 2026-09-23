---
id: T-5377
title: 'REG008 burn-down: 24 check-coverage.yaml dispositions lack a real frob:enforces
  CHK-GATE edge'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
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
CI run 35819358270 (ubuntu/macos/windows); re-verified failing on dev tip 39b89ed091: tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml fails with 24 REG008 violations against docs/design/registry/check-coverage.yaml -- entries dispositioned handled_by:<RULE> whose rule has no real 'frob:enforces CHK-GATE-<RULE>' edge anywhere in code. Either add the missing frob:enforces directive at each rule's real enforcement site, or re-disposition the stale entries. Distinct from T-5179 (REG002: dispositions naming rules absent from the live registry) and T-3278 (stale ids vs known_gate_rule_ids) -- this is REG008 specifically, the enforces-edge check.
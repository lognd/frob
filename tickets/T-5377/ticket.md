---
id: T-5377
title: 'REG008 burn-down: 24 check-coverage.yaml dispositions lack a real frob:enforces
  CHK-GATE edge'
state: done
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
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
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_ratchet.py
- src/frob/gates/_claim_lint.py
- src/frob/gates/_coverage.py
- src/frob/gates/_guard_closure.py
- src/frob/gates/_sys_branch.py
- src/frob/gates/_pii_structural/__init__.py
- src/frob/gates/_inv.py
- src/frob/gates/_wrapper_drift.py
- src/frob/perf/_loop_variant.py
- src/frob/perf/_cache_effects.py
- src/frob/policy/__init__.py
- src/frob/vet/_scan.py
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/__init__.py
- src/frob/strata/_selfconform_surface_rules.py
- src/frob/gates/_sys_provenance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_ratchet.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_claim_lint.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_guard_closure.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_sys_branch.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_pii_structural/__init__.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_inv.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_wrapper_drift.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/perf/_loop_variant.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/perf/_cache_effects.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/policy/__init__.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/vet/_scan.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/__init__.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/strata/_selfconform_surface_rules.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_sys_provenance.py
  reason: REG008 fix requires adding frob:enforces at each rule's real enforcement
    site across the gate/perf/vet/policy modules, not just the yaml
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5377
branch: t-5377
---
CI run 35819358270 (ubuntu/macos/windows); re-verified failing on dev tip 39b89ed091: tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml fails with 24 REG008 violations against docs/design/registry/check-coverage.yaml -- entries dispositioned handled_by:<RULE> whose rule has no real 'frob:enforces CHK-GATE-<RULE>' edge anywhere in code. Either add the missing frob:enforces directive at each rule's real enforcement site, or re-disposition the stale entries. Distinct from T-5179 (REG002: dispositions naming rules absent from the live registry) and T-3278 (stale ids vs known_gate_rule_ids) -- this is REG008 specifically, the enforces-edge check.
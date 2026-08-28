---
id: T-3224
title: REG005/REG008 findings on docs/design/registry/check-coverage.yaml
state: done
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
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_comment_placement.py
- src/frob/gates/_tdd_order.py
- src/frob/gates/_vmodel.py
- src/frob/gates/_narrative_blocks.py
- src/frob/process/parsers/ruff.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_comment_placement.py
  reason: REG005/REG008 required fixing the gate_rule_total denominator plus adding
    frob:enforces CHK-GATE-<RULE> to each rule's own enforcing code site (TDD001/VMOD001/NARR001/F401
    pre-existing gaps, CPLACE001/CPLACE002 a T-3218 regression)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: REG005/REG008 required fixing the gate_rule_total denominator plus adding
    frob:enforces CHK-GATE-<RULE> to each rule's own enforcing code site (TDD001/VMOD001/NARR001/F401
    pre-existing gaps, CPLACE001/CPLACE002 a T-3218 regression)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_vmodel.py
  reason: REG005/REG008 required fixing the gate_rule_total denominator plus adding
    frob:enforces CHK-GATE-<RULE> to each rule's own enforcing code site (TDD001/VMOD001/NARR001/F401
    pre-existing gaps, CPLACE001/CPLACE002 a T-3218 regression)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_narrative_blocks.py
  reason: REG005/REG008 required fixing the gate_rule_total denominator plus adding
    frob:enforces CHK-GATE-<RULE> to each rule's own enforcing code site (TDD001/VMOD001/NARR001/F401
    pre-existing gaps, CPLACE001/CPLACE002 a T-3218 regression)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: REG005/REG008 required fixing the gate_rule_total denominator plus adding
    frob:enforces CHK-GATE-<RULE> to each rule's own enforcing code site (TDD001/VMOD001/NARR001/F401
    pre-existing gaps, CPLACE001/CPLACE002 a T-3218 regression)
  actor: logan
  at: '2026-08-28'
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-3041's triage (13 live-repo self-conformance tests fail).

Two of T-3041's 13 tests fail on this one registry file, independent of
the SYS100/102/107 family T-3029 already fixed:

  tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
  tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml

Both assert zero REG005/REG008 findings against
docs/design/registry/check-coverage.yaml and both currently fail with 4
real findings each (measured on main post-T-3029, T-3041 investigation):
REG005 ("entry was silently added or dropped without updating the
declared denominator") and REG008 ("handled_by:<RULE> disposition with
no frob:enforces CHK-GATE-<RULE> edge in code -- add the directive to
the enforcing rule, or re-disposition the entry").

Reproduce: run either test above against a checkout of main; both fail
with 4 Violation objects each naming the specific check-coverage.yaml
entries at fault.
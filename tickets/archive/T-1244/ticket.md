---
id: T-1244
title: 'compliance: COMPLIANCE005 verifies disposition strings exist, not that any
  behavior is enforced -- close the drift/vacuity gap'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: high
parent: T-1241
tier: ticket
sprint: null
scope:
- src/frob/strata/_compliance.py
- src/frob/gates/_decisions_compliance.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
- tests/unit/strata/test_compliance.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: COMPLIANCE007 is a new live gate rule id; registering it in known_gate_rule_ids()
    is required for the rule to resolve correctly wherever caught_by/rule-id tokens
    are checked
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: REG010 gate-rule staleness needs a CHK-GATE-COMPLIANCE007 entry for the
    new rule id, mechanical sync
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: compliance discharge/gate test files touched by T-1244's COMPLIANCE007 addition
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_gates.py
  reason: compliance discharge/gate test files touched by T-1244's COMPLIANCE007 addition
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
- tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap
- tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_self_referential_handled_by_is_flagged
- tests/test_gates.py::TestComplianceGate::test_compliance007_fires_warn_on_self_referential_handled_by
- tests/test_gates.py::TestComplianceGate::test_compliance007_silent_on_frob_catalog_entries_self_reference
designated_repro_test: null
acceptance:
- text: GIVEN a CMPL-* row whose handled_by names a rule/RegulationEntry id that does
    not exist anywhere in COMPLIANCE_CATALOG or the known gate rule set WHEN compliance_gate
    runs THEN it fails loud with a named violation (mirrors COMPLIANCE004's caught_by
    integrity check, applied to handled_by too)
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
  - tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap
  - tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_self_referential_handled_by_is_flagged
- text: GIVEN a repo with strata models that declare exposure:public-web or other
    compliance-relevant attrs but evaluate_compliance is never invoked in the gate
    pipeline WHEN frob check runs THEN this gap is either closed (evaluate_compliance
    wired into the gate) or explicitly documented as a known non-goal with a named
    compensating control -- not silently assumed covered by COMPLIANCE005's registry-only
    check
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance007_fires_warn_on_self_referential_handled_by
- text: GIVEN the real repo's own compliance.yaml and current wiring WHEN this ticket
    closes THEN docs/design/registry/EXHAUSTIVENESS-GATE.md states plainly what compliance_gate
    does and does not verify
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance007_silent_on_frob_catalog_entries_self_reference
- text: GIVEN a synthetic compliance.yaml with a CMPL_REGISTRY_UNIT_IDS row set to
    handled_by:COMPLIANCE005 WHEN compliance_gate runs THEN COMPLIANCE007 FAILs the
    row with WARN severity BEFORE this fix's self-reference detection existed there
    was no such finding, and AFTER it exists check_cmpl_registry/compliance_gate PASSes
    the row through to a named, correctly-severitied violation
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance007_fires_warn_on_self_referential_handled_by
threat: null
component: null
---
compliance_gate/COMPLIANCE005 currently only checks that each of the 17 CMPL_REGISTRY_UNIT_IDS carries SOME handled_by/out_of_scope disposition string (_check_cmpl_registry_unit_dispositions) -- it never verifies the named handled_by control (COMPLIANCE005 itself, self-referential for all 17) actually corresponds to a live RegulationEntry/mitigation predicate, and it is silent (empty tuple) on any repo with no compliance.yaml or no strata model at all (runs in ~0.01s -- confirm this is registry-presence-only, not model-driven). Two distinct problems to close: (a) generate-and-verify the registry against code the way the rule registry does -- every CMPL-* row's disposition must resolve to a real, named, currently-existing check function or RegulationEntry.id, not just a non-deferred string (a handled_by:COMPLIANCE005 that is self-referential for 17/27 rows is exactly the catalogued-not-enforced shape this epic exists to close); (b) confirm/document what happens on a repo with strata models present but this registry never wired to evaluate_compliance -- if compliance.yaml presence and evaluate_compliance model-checking are two independently-silent paths, name that gap explicitly rather than letting compliance_gate's green rely on registry-only checking.
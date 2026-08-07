---
id: T-1314
title: 'sys gate: fold evaluate_compliance into the automatic pipeline (SELFAUDIT001
  pattern)'
state: done
kind: security
origin: agent
created: '2026-07-29'
priority: high
parent: T-1241
tier: ticket
sprint: null
scope:
- src/frob/gates/_sys.py
- src/frob/strata/_compliance.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_clean_model_no_violations
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_suppressed_on_design_load_error
designated_repro_test: null
acceptance:
- text: GIVEN a repo with a design/ directory WHEN frob check runs THEN evaluate_compliance
    executes per discovered .strata model inside the sys gate family (SELFAUDIT001-style
    folding, same design/ opt-in precondition), so a model with an exposure:public-web
    node and no privacy-policy mitigation FAILS frob check -- not only the manual
    frob sys audit
  evidence:
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_clean_model_no_violations
- text: GIVEN the folding lands THEN the green-check-red-audit divergence class is
    regression-tested (a model that fails sys audit compliance must fail frob check)
    and the tier (WARN vs ERROR) is decided and documented
  evidence:
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_suppressed_on_design_load_error
threat: null
component: null
---
Reviewer-confirmed gap from the T-1242/T-1244 close 2026-07-29: evaluate_compliance has zero call sites under src/frob/gates/ -- only the registry-string COMPLIANCE005/006/007 checks are wired into frob check; the actual model-evaluation layer (including the new PRIVACY-NOTICE unit) runs only under manual frob sys audit. This is exactly the catalogued-but-check-invisible shape T-0756/SELFAUDIT001 closed for self-conformance/contention/mode/reliability, never extended to compliance. Violates the standing doctrine that nothing important is manual-only. Fold under sys_gate's SELFAUDIT aggregation per the T-0756 precedent.
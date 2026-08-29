---
id: T-draft-88767e9b
title: 'Fix gate:REG002 errors: register VERSION001/TDD001/VMOD001 as known gate rules'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
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
body_changes:
- mode: append
  reason: 'BUG002: no genuine before/after repro exists for a rule-id-registration-only
    diff; declaring no-behavior-change per BUG002 remedy (2)'
  actor: logan
  at: '2026-08-29'
  old_length: 986
  new_length: 1324
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
designated_repro_test: null
acceptance:
- text: GIVEN VERSION001/TDD001/VMOD001 registered in _KNOWN_GATE_RULES WHEN their
    producing gates run against a violating fixture THEN each rule fires through the
    real production invocation (not a mocked/stubbed check)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sub-ticket of T-3343 (triage). Fixes the remaining gate:REG002 3 errors, measured via frob check --only registry --json.

docs/design/registry/check-coverage.yaml's CHK-GATE-VERSION001/CHK-GATE-TDD001/CHK-GATE-VMOD001 entries correctly assert 'VERSION001/TDD001/VMOD001 is a live, enforced gate rule' -- and they are (frob.gates._version_coupling.py, frob.gates._tdd_order.py's RULE_TDD001, frob.gates._vmodel.py all emit these rule ids in real findings). The doc registry was right; src/frob/gates/_waive.py's _KNOWN_GATE_RULES frozenset (REG002's known_rules cross-check set) was simply missing all three. Added them, matching the existing PROFILE001/PLATFORM001 entries' comment style.

Deferred from an earlier attempt (originally part of T-3364) because src/frob/gates/_waive.py carried a live in-progress lease from T-3295 (an unrelated feature actively reworking the same frozenset region) at the time; landed separately now that T-3295 has landed.

Re-measured: gate:REG 3 -> 0.

frob:no-behavior-change reason="registers 3 pre-existing, already-live gate rule ids (VERSION001/TDD001/VMOD001) into the _KNOWN_GATE_RULES frozenset -- these rules already fire in production; this only teaches REG002/the waiver-validity check that they exist. No rule logic, detector, or emitted finding changes anywhere in this diff."
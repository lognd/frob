---
id: T-0756
title: self-audit-green-at-land + new-gate-rule end-to-end acceptance policy (kill
  invoked-by-nothing structurally)
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/gates/**
- src/frob/tickets/**
- docs/modules/gates.md
- tests/test_tickets_new_gate_rule_acceptance.py
- invariants/INV-041.md
- tests/test_gates.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_new_gate_rule_acceptance.py
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: invariants/INV-041.md
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'Evidence test files and the invariant spec for this ticket''s own new

    SELFAUDIT001 gate/new-gate-rule-acceptance machinery must live under

    tests/** and invariants/** respectively; declared scope only covered the

    production src/frob/**/gates.md surface.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: design/frob.strata
  reason: 'Wiring SELFAUDIT001 into frob check for the first time surfaced a real,

    previously-undisclosed red frob sys audit (SYS203 on node=serve, missing

    the same waiver its 4 sibling nodes already carry from T-0724) -- landing

    the new blocking gate while knowingly leaving the repo''s own audit red

    would repeat the exact T-0724 incident this ticket exists to close.

    Adding the one missing sibling-pattern waiver line is a precondition for

    SELFAUDIT001 being usable as a land gate at all, not an unrelated design

    change.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags
- tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added
designated_repro_test: null
acceptance:
- text: GIVEN a change that reddens frob sys audit WHEN land preflight runs THEN land
    errors naming the new self-audit gap; GIVEN a ticket adding a gate rule id with
    no before-fails/after-passes fixture in its evidence THEN close is blocked
  evidence:
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
  - tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
  - tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags
  - tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound
  - tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added
threat: null
component: null
---
Root-cause analysis 2026-07-22: the invoked-by-nothing pattern caused repeated rejects (T-0724 enabling the check reddened frobs OWN sys audit undisclosed; T-0630/T-0595/T-0616/T-0710 built-but-unwired). Two structural fixes: (1) SELF-AUDIT AT LAND: frob check (and frob ticket land preflight) must run the repos own self-conformance/sys-audit and ERROR if the change reddens it -- T-0724s red audit should have been a land gate, not a reviewer catch. selfconform partly does this; extend to run the full sys audit surface (contention, reliability, all SYS families) as a blocking pre-land step so no landed change leaves frobs own model failing. (2) NEW-GATE-RULE ACCEPTANCE POLICY: a ticket that adds a gate/check rule id (detectable: new entry in _KNOWN_GATE_RULES or a new SYS/REL/etc rule) MUST record, as bound acceptance evidence, a fixture that FAILS frob check before and PASSES after -- proving the rule fires through the production invocation, not just its pure function. A new rule with only unit-level evidence and no end-to-end fixture = a close-blocking finding. This makes the catalogued-is-not-enforced doctrine self-enforcing for every future gate.
---
id: T-1155
title: 'gates: new-gate-rule-acceptance preflight lost _KNOWN_GATE_RULES after the
  _waive.py move -- resolve dynamically, fail loudly on miss'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1155 touches docs/modules/gates.md to document the dynamic-resolution
    fix, an in-scope symptom of the same change
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
- tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
designated_repro_test: null
acceptance:
- text: GIVEN the new-gate-rule-acceptance preflight WHEN _KNOWN_GATE_RULES lives
    in any gates module THEN the preflight finds it (import-time resolution or the
    generated registry, not a hard-coded file path) and new-rule detection runs
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
- text: GIVEN the literal genuinely cannot be resolved THEN the preflight FAILS with
    an error instead of warning-and-skipping -- a detection check must never silently
    disable itself
  evidence:
  - tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
threat: null
component: null
---
Observed on a T-1153 close (2026-07-28): WARNING new-gate-rule-acceptance: _KNOWN_GATE_RULES literal not found in src/frob/gates/__init__.py, skipping new-rule detection. The wave-18 gates splits moved _KNOWN_GATE_RULES into gates/_waive.py (T-1139 land 71e91ca0); the preflight's hard-coded path went stale and the check now silently skips -- the catalogued-is-not-enforced failure mode applied to a checker itself. Also exactly the moved-symbol class T-1135's refactor verb would have caught; cite this incident in that epic's design.
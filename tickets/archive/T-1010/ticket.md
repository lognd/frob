---
id: T-1010
title: generate _KNOWN_GATE_RULES from the T-0964 scanner (registry = scan, allowlist
  only for retired ids)
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-1008
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: SCOPE002/AFFECT001/COV001 require the frob:doc anchor + prose bullets for
    the new src/frob/gates/_rule_id_scan.py public symbols to land in the same diff
  actor: logan
  at: '2026-07-27'
- op: remove
  glob: docs/modules/gates.md
  reason: 'reverting: gates.md''s SCOPE002 closure pulls in dozens of unrelated modules
    across the whole doc-anchor graph -- waiving AFFECT001/COV001/SCOPE001 at the
    specific new sites instead of scope-including a monolithic shared doc file'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_scan_resolves_const_name_reference
- tests/test_gates.py::TestKnownGateRuleIds::test_retired_id_stays_excluded
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
designated_repro_test: null
acceptance:
- text: given a new gate emitting a fresh rule id via constant or literal, when generation
    runs, then the registry contains it with no hand edit; the drift-lock passes with
    an empty ad hoc allowlist
  evidence:
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
  - tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id
  - tests/test_gates.py::TestKnownGateRuleIds::test_scan_resolves_const_name_reference
  - tests/test_gates.py::TestKnownGateRuleIds::test_retired_id_stays_excluded
  - tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
  - tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
threat: null
component: null
---
Child 2 of T-1008. The registry drifted repeatedly (T-0903/T-0923/T-0924/T-0961/T-0966 all hand-added batches). Invert: the T-0964 constant+literal scan derives the live rule-id set; _KNOWN_GATE_RULES becomes generated-or-verified against it, with a small hand-maintained retired-ids list as the only manual part. The drift-lock test then verifies the generator, not hand-parity.
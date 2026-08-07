---
id: T-0624
title: 'arch: misc design smells (ARCH1xx) -- mutable default arg, feature envy, data
  clumps, magic literals, dead private code, deep inheritance, temporal coupling'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_normalized.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_models.py
  reason: extend shared ArchCategory for misc design smell checks
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/arch/_normalized.py
  reason: NormalizedParam.default_text field addition
  actor: logan
  at: '2026-07-23'
- op: remove
  glob: src/frob/arch/_smells.py
  reason: release lease -- T-0624's own _smells.py work already committed; T-0625
    needs it (its own scope names this module)
  actor: logan
  at: '2026-07-26'
- op: remove
  glob: src/frob/arch/_models.py
  reason: release lease -- T-0624's own _models.py edit already committed; T-0625
    needs it next
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_arch.py::TestMutableDefaultArg::test_list_literal_default_flagged
- tests/unit/test_arch.py::TestMutableDefaultArg::test_none_default_not_flagged
- tests/unit/test_arch.py::TestFeatureEnvy::test_method_calling_other_receiver_more_than_self_flagged
- tests/unit/test_arch.py::TestFeatureEnvy::test_method_calling_self_more_than_others_not_flagged
- tests/unit/test_arch.py::TestDataClumps::test_same_three_keyword_group_at_three_sites_flagged
- tests/unit/test_arch.py::TestDataClumps::test_group_at_two_sites_not_flagged
- tests/unit/test_arch.py::TestMagicLiteral::test_bare_number_in_condition_flagged
- tests/unit/test_arch.py::TestMagicLiteral::test_zero_and_one_not_flagged
- tests/unit/test_arch.py::TestDeadPrivateCode::test_unreferenced_private_function_flagged
- tests/unit/test_arch.py::TestDeadPrivateCode::test_referenced_private_function_not_flagged
- tests/unit/test_arch.py::TestDeepInheritance::test_chain_beyond_threshold_flagged
- tests/unit/test_arch.py::TestDeepInheritance::test_shallow_chain_not_flagged
- tests/unit/test_arch.py::TestTemporalCoupling::test_guard_clause_on_initialized_flag_flagged
- tests/unit/test_arch.py::TestTemporalCoupling::test_field_not_guarded_not_flagged
- tests/unit/test_arch.py::TestRunSmellChecks::test_combines_all_seven_checks
designated_repro_test: null
threat: null
component: null
---
mutable default argument (list/dict/set literal as a default param value). feature envy (method's body references another object's attrs/methods more than self's). data clumps (same 3+-param group passed together across 3+ call sites). magic numbers/strings in logic (bare literal in a comparison/branch outside a named constant). dead private code (unreferenced private symbol, using the T-0288 call graph so helper-splices don't false-positive). deep inheritance (DIT beyond a configurable threshold). temporal coupling (an _initialized-style flag guarding call order instead of the type system). Acceptance: fixture per sub-check; docs updated.
---
id: T-3009
title: 'Enforce TDD from git history: a verification nodes introducing commit must
  precede its implementation node (T-3004 section 7)'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tdd_order.py
- src/frob/gates/__init__.py
- tests/gates/test_tdd_order.py
- docs/modules/gates.md
- docs/strata/vmodel.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: 'T-3009: TDD-ordering gate module, its tests, and doc updates'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-3009: TDD-ordering gate module, its tests, and doc updates'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/gates/test_tdd_order.py
  reason: 'T-3009: TDD-ordering gate module, its tests, and doc updates'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-3009: TDD-ordering gate module, its tests, and doc updates'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/vmodel.md
  reason: 'T-3009: TDD-ordering gate module, its tests, and doc updates'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: design/frob.strata
  reason: 'T-3009: declare exec capability for new tests/gates/test_tdd_order.py subprocess
    use (SELFAUDIT001)'
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
evidence:
- tests/gates/test_tdd_order.py::TestSymrefHelpers::test_symref_path_splits_on_double_colon
- tests/gates/test_tdd_order.py::TestSymrefHelpers::test_symref_qualname_keeps_the_full_dotted_path
- tests/gates/test_tdd_order.py::TestAstQualnames::test_collects_nested_dotted_qualnames
- tests/gates/test_tdd_order.py::TestAstQualnames::test_a_bare_mention_in_a_docstring_or_comment_is_not_a_definition
- tests/gates/test_tdd_order.py::TestAstQualnames::test_unparseable_source_yields_an_empty_set
- tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_resolves_the_commit_that_added_the_symbol
- tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_returns_none_for_a_symbol_never_added
- tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction::test_a_mere_textual_mention_does_not_count_as_introduction
- tests/gates/test_tdd_order.py::TestClassifyOrder::test_fires_when_implementation_precedes_test
- tests/gates/test_tdd_order.py::TestClassifyOrder::test_stays_quiet_when_test_precedes_implementation
- tests/gates/test_tdd_order.py::TestClassifyOrder::test_fires_when_commits_are_identical
- tests/gates/test_tdd_order.py::TestClassifyOrder::test_reports_unresolved_when_either_commit_is_unresolvable
- tests/gates/test_tdd_order.py::TestClassifyOrder::test_reports_unresolved_on_diverged_history
- tests/gates/test_tdd_order.py::TestTddOrderViolations::test_fires_on_a_planted_implementation_first_pair
- tests/gates/test_tdd_order.py::TestTddOrderViolations::test_stays_quiet_on_a_genuine_test_first_pair
- tests/gates/test_tdd_order.py::TestTddOrderViolations::test_fires_when_test_and_implementation_share_a_commit
- tests/gates/test_tdd_order.py::TestTddOrderViolations::test_reports_unresolved_rather_than_passing_on_an_unresolvable_pair
- tests/gates/test_tdd_order.py::TestTddOrderViolations::test_ignores_non_tests_edges
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

---
id: T-0849
title: 'pattern registry phase 3: work or disposition the 41 recommender rows previously
  deferred to T-0605'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- docs/design/registry/patterns.yaml
- tests/unit/test_arch.py
- tests/test_registry_reconciliation_patterns.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: 'Ticket''s playbook rule (section 4b/hard rules) requires new public

    symbols added to src/frob/arch/_patterns.py''s PATTERN_REGISTRY to carry

    frob:doc edges into docs/modules/arch.md''s design-pattern-registry

    section (the anchor every existing PATTERN_REGISTRY row''s frob:doc

    directive already targets), and the doctrine precedent this ticket is

    extending (T-0605''s own T-0849-phase reasoning) lives in that same

    section. Extending scope to cover this one doc file rather than leaving

    the two new detectors'' frob:doc directives dangling or the doctrine

    undocumented.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_recommends_dataclass
- tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_computed_field_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_extra_method_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_with_decorated_extra_method_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_already_dataclass_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_manual_decorator_wrap_recommends_decorator_syntax
- tests/unit/test_arch.py::TestPatternRecommender::test_two_manual_decorator_wraps_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_decorator_syntax_wrap_not_flagged
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_declared_total_is_346
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations
designated_repro_test: null
threat: null
component: null
---
T-0605 (recommender phase 2) closed having worked its 6 mandated rows; 41 other patterns.yaml rows (DDD-II-*, RELEASEIT-*, and friends) still carried disposition deferred:T-0605 and became REG003 errors the moment it closed (deferral to a closed ticket is not a real deferral -- the registry analogue of WAIVE006). Those 41 rows are re-pointed here. For each: implement a high-precision detector, or record a reasoned not-checkable/out-of-scope disposition, per the same noise mandate as T-0605. Keep the reconciliation pin test green.
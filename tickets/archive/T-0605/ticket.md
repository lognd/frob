---
id: T-0605
title: 'design-pattern recommender phase 2: Adapter, Flyweight/pool, Observer, anemic-domain-model,
  poltergeist/lava-flow, sequential-coupling detectors'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0332
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- docs/modules/arch.md
- tests/unit/test_arch.py
- docs/design/registry/patterns.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestPatternRecommender::test_translating_wrapper_recommends_adapter
- tests/unit/test_arch.py::TestPatternRecommender::test_same_name_wrapper_not_flagged_adapter
- tests/unit/test_arch.py::TestPatternRecommender::test_two_translating_methods_not_flagged_adapter
- tests/unit/test_arch.py::TestPatternRecommender::test_manual_callback_list_recommends_observer
- tests/unit/test_arch.py::TestPatternRecommender::test_append_only_list_not_flagged_observer
- tests/unit/test_arch.py::TestPatternRecommender::test_iterate_without_append_not_flagged_observer
- tests/unit/test_arch.py::TestPatternRecommender::test_anemic_accessors_recommends_move_behavior
- tests/unit/test_arch.py::TestPatternRecommender::test_class_with_real_method_not_flagged_anemic
- tests/unit/test_arch.py::TestPatternRecommender::test_two_accessor_class_not_flagged_anemic
- tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations
- tests/unit/test_arch.py::TestPatternRecommender::test_mixed_delegate_and_translate_methods_fires_both
designated_repro_test: null
acceptance:
- text: GIVEN each of the 6 rows WHEN this ticket closes THEN the row is either detected
    by a tested high-precision detector or carries a reasoned not-checkable/out-of-scope
    disposition AND the patterns reconciliation pin test passes
  evidence:
  - tests/unit/test_arch.py::TestPatternRecommender::test_mixed_delegate_and_translate_methods_fires_both
threat: null
component: null
---
The 6 registry rows T-0332 deferred for precision reasons: each needs a fuzzier structural signal than the >=3-occurrence floors phase 1 shipped, and shipping them imprecise would train users to ignore the advisory channel (the ticket's own noise mandate). Design a high-precision signal per row or record a reasoned not-checkable disposition. Any patterns.yaml entries re-deferred at T-0332 close point HERE -- keep the reconciliation pin test (tests/test_registry_reconciliation_patterns.py) green when this ticket changes dispositions. NOTE: T-0332's Done report references this as T-draft-4fb8deee; drafts do not survive land (T-0577), so this is the real ticket.
---
id: T-0332
title: 'design-pattern recommender: hallmark->pattern + anti-pattern->escape registry
  (advisory)'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
- docs/design/registry/patterns.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0332 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/design/registry/patterns.yaml
  reason: 'reviewer-required: closing T-0332 orphans 41 deferred:T-0332 dispositions;
    re-dispositioning them is part of this ticket per its own EXHAUSTIVENESS DRIFT-LOCK'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestPatternRecommender::test_isinstance_chain_recommends_strategy
- tests/unit/test_arch.py::TestPatternRecommender::test_state_field_chain_recommends_state_machine
- tests/unit/test_arch.py::TestPatternRecommender::test_telescoping_ctor_recommends_builder
- tests/unit/test_arch.py::TestPatternRecommender::test_scattered_construction_across_files_recommends_factory
- tests/unit/test_arch.py::TestPatternRecommender::test_wrap_delegate_recommends_decorator
- tests/unit/test_arch.py::TestPatternRecommender::test_god_class_pairs_with_srp_escape
- tests/unit/test_arch.py::TestPatternRecommender::test_stringly_typed_recommends_newtype
- tests/unit/test_arch.py::TestPatternRecommender::test_two_arm_isinstance_chain_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_normal_ctor_not_flagged_as_telescoping
- tests/unit/test_arch.py::TestPatternRecommender::test_construction_in_two_files_not_flagged
- tests/unit/test_arch.py::TestPatternRecommender::test_short_string_chain_not_flagged_stringly_typed
- tests/unit/test_arch.py::TestPatternRecommender::test_simple_python_no_pattern_recommendations
- tests/unit/test_arch.py::TestPatternRecommender::test_non_state_attribute_chain_not_flagged_state_machine
- tests/unit/test_arch.py::TestPatternRecommender::test_two_method_delegating_wrapper_not_flagged_decorator
- tests/unit/test_arch.py::TestPatternRecommender::test_class_at_threshold_not_flagged_god_object
designated_repro_test: null
threat: null
component: null
---
Positive complement to the SOLID smell catalog (T-0330). An exhaustive PATTERN REGISTRY (structured like the capability registry -- pattern x hallmark x language matrix, covered-or-excused): each entry = a HALLMARK detector (the before-shape), the recommended PATTERN (GoF + modern), the FORCE/tension it resolves, a refactoring sketch, languages. Two directions: HALLMARK->PATTERN (N-arm isinstance/type-switch -> Strategy/polymorphism; growing if-chain on a state field -> State machine; scattered ConcreteX() construction -> Factory/DI; telescoping optional ctor params -> Builder; manual callback lists -> Observer; repeated wrap+delegate -> Decorator; incompatible-interface bridging -> Adapter; expensive-object reuse -> Flyweight/pool) and ANTI-PATTERN->ESCAPE (god object -> SRP decompose; anemic domain model -> move behavior to data; stringly-typed -> newtype; poltergeist/lava-flow -> delete; sequential coupling -> explicit state). CRITICAL DESIGN (do it right, avoid cargo-culting): (1) RECOMMENDATIONS not errors -- advisory/suggestion severity only, forcing a pattern is itself over-engineering; the user said 'recommended'. (2) STRONG-HALLMARK-ONLY / high precision -- recommend only on an unambiguous structural signal; a noisy recommender trains users to ignore it; the library itself must NOT recommend when the code is already simple. (3) PAIRS WITH the SOLID smells -- reuse the same hallmark detectors: the smell is the diagnosis, the pattern is the prescription (one detector, two outputs: 'violates OCP' + 'consider Strategy'). (4) WAIVABLE with a reason so a repo records deliberate exceptions. (5) each recommendation names the FORCE + a concrete sketch, never a bare 'use Strategy'.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: design-pattern-catalog.md (341 patterns) + design-pattern-traps-corpus.md (anti-pattern->escape hallmarks). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.
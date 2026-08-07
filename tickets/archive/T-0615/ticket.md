---
id: T-0615
title: 'arch: N:1 cross-language equivalence meta-test (python/ts/rust/kotlin)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0610
- T-0611
- T-0612
- T-0614
parent: T-0329
tier: ticket
sprint: null
scope:
- tests/unit/test_arch.py
- tests/fixtures/arch/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_one_class_hierarchy_per_language
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_derived_class_has_the_field_and_one_method
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_override_captured_except_pythons_documented_waiver
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_shared_complexity_check_fires_identically_four_ways
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_dispatch_branch_counts_pin_the_documented_per_language_divergence
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_every_module_agrees_the_dispatch_function_exists_and_is_flat
designated_repro_test: null
threat: null
component: null
---
Add equivalent fixture files (same god-class / long-function / deep-nesting shape) in python, typescript, rust, kotlin under tests/fixtures/arch/, and a parametrized meta-test asserting every shared arch check fires the SAME category+severity across all four languages on its equivalent fixture. This is the epic's own closing acceptance criterion (per T-0329 body: 'an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code'). T-0329 cannot close until this passes.
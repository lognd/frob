---
id: T-0447
title: dup R3 indistinguishable from R2 (r3_canonical_hash literal-abstraction/control-flow-desugar
  unimplemented) + no cross-language dup litmus fixtures (T-0199 gaps)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/src/lib.rs
- src/frob/dup/_pipeline.py
- tests/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_dup.py
  reason: T-0447 dup work maps to tests/test_dup.py
  actor: logan
  at: '2026-07-20'
evidence:
- frob-core/src/lib.rs::tests::canonical_hash_is_deterministic_and_shape_sensitive
- frob-core/src/lib.rs::tests::r3_literal_abstraction_collapses_differing_constants
- frob-core/src/lib.rs::tests::r3_literal_abstraction_does_not_collapse_different_operators
- frob-core/src/lib.rs::tests::r3_elif_desugar_matches_manually_nested_if_else
- frob-core/src/lib.rs::tests::r3_elif_desugar_does_not_collapse_different_conditions
- frob-core/src/lib.rs::tests::is_numeric_literal_rejects_identifiers_and_keywords
- frob-core/src/lib.rs::tests::is_string_literal_requires_matching_quotes
- tests/test_dup.py::TestR3LiteralAbstraction::test_r3_fires_where_r2_does_not
- tests/test_dup.py::TestR3LiteralAbstraction::test_r3_does_not_collapse_a_different_operator
- tests/test_dup.py::TestR3ElifDesugar::test_r3_fires_where_r2_does_not
- tests/test_dup.py::TestR3ElifDesugar::test_r3_does_not_collapse_a_different_condition
- tests/test_dup.py::TestCrossLanguageR5Litmus::test_both_languages_parse_into_the_snapshot
- tests/test_dup.py::TestCrossLanguageR5Litmus::test_r5_fires_across_languages
- tests/test_dup.py::TestCrossLanguageR5Litmus::test_r1_r2_r3_do_not_fire_across_languages
designated_repro_test: null
threat: null
component: null
---

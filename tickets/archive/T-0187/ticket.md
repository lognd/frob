---
id: T-0187
title: 'frob dup bleeding-edge: algorithm survey, reverse-templating abstraction,
  exhaustiveness meta-test'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- frob-core/**
- docs/modules/**
- docs/index.md
- tickets.md
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
  reason: T-0187 dup work maps to tests/test_dup.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_matrix_covers_every_rung_clone_type_and_language
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells
- tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r1_python_type1
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_languages_parse_into_the_snapshot
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_smart]
designated_repro_test: null
threat: null
component: null
---
User mandate 2026-07-18: frob dup does the basics (R1-R6 rungs: winnow, WL-hash, candidate_pairs, tree_edit in frob-core; statement-Levenshtein; co-occurrence CFG/DFG proxy) but must be bleeding-edge. Phase 1 RESEARCH (exhaustive-researcher): map the clone-detection state of the art against our implementation -- APTED exact tree edit distance, SourcererCC bag-of-tokens overlap, Oreo metrics-based type-3/4, NiCad normalization+abstraction, DECKARD characteristic vectors, learning-based (ASTNN, FA-AST GNN, CCLearner) with honest feasibility calls for a no-model-dependency tool, cross-language clone detection, and ANTI-UNIFICATION / reverse templating: report each clone group with its abstracted template plus per-instance bindings (the shared skeleton with holes), so the fix suggestion is the extracted function signature, not just 'these are similar'. Phase 2 DESIGN+TICKETS: planner converts the survey into an implementation ticket tree (rust-kernel work vs python orchestration split explicit). Phase 3 META-TEST: exhaustiveness drift-lock in the T-0158/T-0182 mold -- a registry of detectors/rungs/clone-types, parametrized litmus fixtures proving every (clone type 1-4 x supported language x rung) cell either fires on a minimal fixture pair or carries a written exclusion; adding a detector or claiming a clone type without a firing fixture fails the suite. Acceptance: survey doc committed, ticket tree filed, meta-test green over the CURRENT detector set before any new detector lands.
---
id: T-0194
title: 'anti_unify kernel: Plotkin lgg over (labels,parents) node arrays'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_core.py::TestAntiUnify::test_identical_trees_zero_holes
- tests/unit/test_dup_core.py::TestAntiUnify::test_two_near_identical_trees_bind_one_hole
- tests/unit/test_dup_core.py::TestAntiUnify::test_arity_divergence_is_a_hole_not_a_crash
- tests/unit/test_dup_core.py::TestAntiUnify::test_wildly_different_trees_exceed_hole_ceiling
- tests/unit/test_dup_core.py::TestAntiUnify::test_deterministic_across_repeated_calls
- tests/unit/test_dup_core.py::test_frob_core_module_registers_exported_kernels
- tests/unit/test_dup_core.py::test_core_unavailable_path_is_err_not_exception
designated_repro_test: null
threat: null
component: null
---
Survey sec 4: lockstep top-down walk emitting shared nodes and $hole_N at divergence, returning template arrays + binding index pairs; reuses the node-array representation apted_similarity already consumes. Cargo tests incl. hole-ceiling sanity (>50 pct holes = Err back to plain pair).
---
id: T-0801
title: 'dup: control-flow-shape normalization axis (combined-vs-split if) so the real
  git_common_dir pair registers'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_pipeline.py
- tests/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestRealGitCommonDirPairRegisters::test_real_git_common_dir_pair_registers_as_a_duplicate_group
- tests/test_dup.py::TestConditionalShapeDupPairing::test_combined_vs_split_guard_git_common_dir_registers_as_a_duplicate_group
- tests/test_dup.py::TestConditionalShapeNormalization::test_abstracts_if_and_elif_conditions_uniformly
- tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_guard_bodies_do_not_falsely_pair
designated_repro_test: null
acceptance:
- text: GIVEN the real _leases.py::git_common_dir and _exclude_hazard.py::_git_common_dir
    pair WHEN the dup scan runs with both error-channel and control-flow normalization
    THEN they register as a duplicate group (similarity above the 0.6 floor, was 0.444
    with error-channel alone); repo-wide group delta stays bounded and each new pair
    is examined
  evidence:
  - tests/test_dup.py::TestRealGitCommonDirPairRegisters::test_real_git_common_dir_pair_registers_as_a_duplicate_group
threat: null
component: null
---
Promotion of T-0785's worktree draft 2e4385db (worktree removed at land before renumbering). T-0785 landed the error-channel axis; the motivating real pair still differs on a combined-vs-split if structural axis and measures 0.444 (<0.6). Normalize simple guard-shape variants so semantically-one functions pair. Prereq for T-0784's seam unification to be regression-locked by DUP.
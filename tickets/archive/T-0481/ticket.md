---
id: T-0481
title: 'frob.dup._template: consume TreeNode.span for literal source-text rendering'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_template.py
- src/frob/dup/_pipeline.py
- docs/modules/dup.md
- tickets.md
- tests/unit/test_dup_template.py
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
  reason: T-draft-aa52c66f dup work maps to tests/test_dup.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/test_dup.py
  reason: actual test file for build_group_template is tests/unit/test_dup_template.py
    (T-0195); tests/test_dup.py never existed
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_dup_template.py
  reason: actual test file for build_group_template is tests/unit/test_dup_template.py
    (T-0195); tests/test_dup.py never existed
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_one_leaf_divergence_yields_one_hole_with_both_sides
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_identical_bodies_yield_zero_holes
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_three_member_group_folds_to_one_shared_skeleton
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_literal_rendering_preserves_source_text_not_a_skeleton
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_suggested_signature_falls_back_when_not_a_plain_identifier
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_single_member_returns_none
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_unrecoverable_subtree_returns_none_not_raises
- tests/unit/test_dup_template.py::TestHoleParamName::test_reuses_shared_plain_identifier
- tests/unit/test_dup_template.py::TestHoleParamName::test_falls_back_when_members_disagree
- tests/unit/test_dup_template.py::TestHoleParamName::test_falls_back_when_shared_text_is_not_a_plain_identifier
designated_repro_test: null
threat: null
component: null
---
T-0327 added TreeNode.span (byte offsets) threaded through frob.lang._common.export_tree, but frob.dup._template.build_group_template still renders CloneBinding.source_text and CloneTemplate.skeleton_text as a structural label(child,...) skeleton, not the literal source characters the span now makes available. Use span to slice the original source text per docs/modules/dup-sota-survey.md sec 4, and (per that survey) reuse a real identifier name across instances that agree on it in CloneTemplate.suggested_signature instead of always naming holes hole_N. Update docs/modules/dup.md's paragraph noting TreeNode 'does not carry source spans/text today' -- it now does; only the consumption in _template is outstanding.
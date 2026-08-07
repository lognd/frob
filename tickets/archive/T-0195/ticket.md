---
id: T-0195
title: 'reverse-templating report: CloneTemplate/CloneBinding models, extraction-signature
  synthesis in DUP001 messages'
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
blocked_by:
- T-0194
parent: T-0187
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_one_leaf_divergence_yields_one_hole_with_both_sides
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_identical_bodies_yield_zero_holes
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_three_member_group_folds_to_one_shared_skeleton
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_single_member_returns_none
- tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_unrecoverable_subtree_returns_none_not_raises
- tests/test_dup_smart.py::TestGateRules::test_dup001_fires_when_one_side_touched
- tests/test_dup_smart.py::TestGateRules::test_dup002_fires_when_both_sides_touched
designated_repro_test: null
threat: null
component: null
---
Survey sec 4: frozen pydantic CloneTemplate/CloneBinding, CloneReport.groups[].template optional, signature synthesis one param per distinct hole (reuse identifier when both instances agree), DUP001 violation message gains the suggested extraction. The violation hands you the fix, not a percentage.
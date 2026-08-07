---
id: T-0327
title: 'frob.lang.TreeNode: carry source span/text for reverse-templating literal
  source text'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/unit/test_lang_primitives.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_primitives.py::test_export_tree_and_flatten_tree_round_trip
- tests/unit/test_lang_primitives.py::test_symbol_tree_covers_span
designated_repro_test: null
threat: null
component: null
---
T-0195's reverse-templating report (frob.dup._template.build_group_template) renders CloneBinding.source_text and CloneTemplate.skeleton_text as a structural label(child,...) skeleton, not literal source characters, because frob.lang.TreeNode (docs/modules/lang.md) carries only a label + children, no source span/text. Add a span (or byte offsets) field to TreeNode, threaded through frob.lang.symbol_tree's _export_tree, so frob.dup._template can render exact source snippets and (per docs/modules/dup-sota-survey.md sec 4) reuse a real identifier name across instances that agree on it in CloneTemplate.suggested_signature, instead of always naming holes hole_N.
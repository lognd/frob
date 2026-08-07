---
id: T-0495
title: 'frob.lang.TreeNode: carry tree-sitter field names so dup''s type-hole classification
  (T-0287) can cover rust/c/cpp'
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- src/frob/dup/_template.py
- tests/test_dup.py
- tests/unit/test_dup_template.py
- docs/modules/dup.md
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_template.py
  reason: non-vacuous acceptance (rust typed-generic proposal) requires plumbing frob.lang.TreeNode.field
    through _template.py's type-hole classifier; docs need updating to match
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_dup.py
  reason: non-vacuous acceptance (rust typed-generic proposal) requires plumbing frob.lang.TreeNode.field
    through _template.py's type-hole classifier; docs need updating to match
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_dup_template.py
  reason: non-vacuous acceptance (rust typed-generic proposal) requires plumbing frob.lang.TreeNode.field
    through _template.py's type-hole classifier; docs need updating to match
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/dup.md
  reason: non-vacuous acceptance (rust typed-generic proposal) requires plumbing frob.lang.TreeNode.field
    through _template.py's type-hole classifier; docs need updating to match
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/lang.md
  reason: non-vacuous acceptance (rust typed-generic proposal) requires plumbing frob.lang.TreeNode.field
    through _template.py's type-hole classifier; docs need updating to match
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_matching_type_annotations_propose_one_shared_type_var
- tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_value_only_divergence_is_never_misclassified_as_a_type_hole
- tests/unit/test_dup_template.py::TestTypeHoleClassificationC::test_matching_type_annotations_propose_one_shared_type_var
- tests/unit/test_dup_template.py::TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole
designated_repro_test: null
threat: null
component: null
---
found while working T-0287 (dup type-generalizing anti-unification): _template._is_type_position classifies a hole as a TYPE hole by checking whether its immediate parent node's label is a real type-annotation wrapper (python's 'type' node, typescript's 'type_annotation'). Rust/c/cpp place the type node as a direct, unwrapped sibling distinguished only by tree-sitter FIELD NAME (e.g. rust's 'parameter' node's 'type' field vs its 'pattern' field), which frob.lang.TreeNode does not carry today (label + children + span only, per docs/modules/lang.md). Extending TreeNode with an optional per-child field-name array (mirroring frob.lang._common.export_tree's existing recursive shape) would let _template._TYPE_WRAPPER_LABELS-style classification extend to a field-name-based rule for rust/c/cpp, closing the honest gap documented in docs/modules/dup.md's 'Type-hole classification (T-0287)' section and src/frob/dup/_template.py's _TYPE_WRAPPER_LABELS docstring. Out of T-0287's declared scope (frob-core/**, src/frob/dup/**, docs/modules/dup.md, tickets.md, tests/test_dup.py, tests/unit/test_dup_template.py -- does not include src/frob/lang/**).
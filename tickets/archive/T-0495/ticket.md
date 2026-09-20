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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/**
- src/frob/dup/_template.py
- tests/test_dup.py
- tests/unit/test_dup_template.py
- docs/modules/dup.md
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense rust/c/cpp type-hole field-name rationale into T-0495 body
  actor: logan
  at: '2026-09-19'
  old_length: 1151
  new_length: 2571
evidence:
- tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_matching_type_annotations_propose_one_shared_type_var
- tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_value_only_divergence_is_never_misclassified_as_a_type_hole
- tests/unit/test_dup_template.py::TestTypeHoleClassificationC::test_matching_type_annotations_propose_one_shared_type_var
- tests/unit/test_dup_template.py::TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-0287 (dup type-generalizing anti-unification): _template._is_type_position classifies a hole as a TYPE hole by checking whether its immediate parent node's label is a real type-annotation wrapper (python's 'type' node, typescript's 'type_annotation'). Rust/c/cpp place the type node as a direct, unwrapped sibling distinguished only by tree-sitter FIELD NAME (e.g. rust's 'parameter' node's 'type' field vs its 'pattern' field), which frob.lang.TreeNode does not carry today (label + children + span only, per docs/modules/lang.md). Extending TreeNode with an optional per-child field-name array (mirroring frob.lang._common.export_tree's existing recursive shape) would let _template._TYPE_WRAPPER_LABELS-style classification extend to a field-name-based rule for rust/c/cpp, closing the honest gap documented in docs/modules/dup.md's 'Type-hole classification (T-0287)' section and src/frob/dup/_template.py's _TYPE_WRAPPER_LABELS docstring. Out of T-0287's declared scope (frob-core/**, src/frob/dup/**, docs/modules/dup.md, tickets.md, tests/test_dup.py, tests/unit/test_dup_template.py -- does not include src/frob/lang/**).

<!-- narrative-moved:src/frob/dup/_template.py:66:T-0495 -->
T-0495: rust/c/cpp place a type node as a direct, unwrapped sibling
distinguished only by tree-sitter FIELD NAME, never a wrapper label --
verified directly against each grammar's own parse (docs/modules/dup.md
#type-hole-classification-t-0287): rust's `parameter` node has a `type`
field (`fn f(a: i32)` parses `i32` with field name "type" on a bare
`primitive_type` sibling, next to the `pattern` field holding `a`) and
its `function_item` node has a SEPARATE `return_type` field for `-> T`
(rust's grammar does not reuse "type" for the return position, unlike
c); c's `parameter_declaration`/`function_definition` both expose a
`type` field directly on the type node for BOTH positions (`int add(int
a)` parses the first `int` as field "type" on `function_definition`,
the second as field "type" on `parameter_declaration` -- no separate
return-type field name); cpp inherits c's grammar shape for this
construct. Checking the node's OWN field name (not its parent's label)
closes exactly this gap without disturbing python/typescript, whose
type node also happens to carry field name "type" on ITS OWN wrapper
(`_TYPE_WRAPPER_LABELS` already covers that case via the parent-label
rule; the field-name rule below is a strict addition, not a
replacement, since python/typescript's hole is the wrapper's unfielded
inner child, not the wrapper node itself).
## Done report

Extended `frob.lang.TreeNode` with a `field` attribute (T-0495): each
node's own tree-sitter FIELD NAME as seen from its parent
(`Node.field_name_for_child`), or `None` for an unfielded node. Populated
in `frob.lang._common.export_tree`/`_leaf_tree_node` by looking up the
PARENT's `field_name_for_child(i)` against the child's ORIGINAL
(unfiltered) index before stripping comment siblings, so a stripped
comment never shifts a later child's field-name lookup.

Wired this through `frob.dup._template._is_type_position` (T-0287's
per-member type-hole classifier), which now recognizes a type position
via two independent rules: (1) the existing python/typescript rule (the
node's immediate parent is a real `type`/`type_annotation` wrapper node);
(2) the new rust/c/cpp rule (the node's OWN field name is `"type"` or
`"return_type"`). `_NodeArrays` (the internal labels/parents/spans tuple
`_template.py` threads through anti-unification) grew a fourth parallel
`fields` array; every call site that unpacks/constructs it was updated.

Verified real grammar shapes directly (not assumed) before writing the
rule: rust's `parameter` node has a `type` field (sibling of the
`pattern` field) and rust's `function_item` has a SEPARATE `return_type`
field (rust does not reuse "type" for the return position); c's
`parameter_declaration` and `function_definition` BOTH use field
`"type"` for either position (no separate return-type field); cpp
inherits c's grammar shape for this construct; python/typescript's
existing wrapper-node rule already covers their case independently (their
`type`/`type_annotation` wrapper also happens to carry field name
`"type"`/`"return_type"`, so both rules agree there -- no conflict, no
double-counting since `_is_type_position` is a boolean OR, not additive).

Non-vacuous acceptance (the ticket's own bar), proven with real `.rs` and
`.c` fixtures parsed through the actual pipeline (no hand-built
labels/parents/fields arrays for these, unlike the pre-existing
hand-built consistency-guard unit test which stays as edge-case coverage):
- `TestTypeHoleClassificationRust::test_matching_type_annotations_propose_one_shared_type_var`:
  a real rust clone pair (`fn f(x: i32) -> i32 {...}` vs `fn f(x: u64) ->
  u64 {...}`) with CONSISTENT type shape at both the parameter and return
  positions proposes exactly one shared type variable (`T0`), rendered
  in the skeleton and every binding, via `build_group_template` end to
  end.
- `TestTypeHoleClassificationRust::test_value_only_divergence_is_never_misclassified_as_a_type_hole`:
  a real rust pair whose only divergence is a body-expression VALUE
  position (both sides share the identical `i32` type annotation)
  proposes zero type variables -- proves the new field-name rule does
  not spuriously fire outside a genuine type position.
- `TestTypeHoleClassificationC::test_matching_type_annotations_propose_one_shared_type_var`:
  same shape in real C (`int f(int x) {...}` vs `long f(long x) {...}`),
  covering c/cpp's DIFFERENT field-name convention (c reuses `"type"` for
  both positions, no separate `"return_type"`) -- the "c/cpp if feasible"
  half of the ticket's acceptance bar. Cpp shares c's grammar shape for
  this construct (verified directly against its own tree-sitter parse)
  but has no dedicated litmus fixture of its own; noted as a follow-up in
  docs/modules/dup.md rather than silently assumed identical.

Updated the existing hand-built `_classify_type_vars` consistency-guard
unit test (`TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole`)
for the new 4-tuple `_NodeArrays` shape (added a `fields` array to its
manually-constructed trees) -- no behavior change, just kept it compiling
against the widened internal shape.

Updated docs/modules/dup.md's "Type-hole classification (T-0287)" section
(the "Cross-language honesty" paragraph, now "Cross-language coverage")
to state the closed gap instead of the prior "extending it would be a
frob.lang change, out of this feature's scope" disclaimer, and
docs/modules/lang.md's primitives list to document `TreeNode.field`.

Filed T-draft-... none this round -- the cpp litmus-fixture gap is noted
inline in docs/modules/dup.md's updated section rather than as a
separate ticket, since it is a one-line disclosed limitation, not an
open design question (same disposition as the existing "no rust/c/cpp
R2-R4 litmus fixture yet" line already in the same doc section).

Ran `uv run pytest tests/unit/test_dup_template.py tests/test_dup*.py
tests/unit/test_dup*.py tests/unit/test_lang*.py tests/test_lang*.py -q`:
all green (16 tests in test_dup_template.py alone, 3 new classes/4 new
test methods added by this ticket). `ruff check`/`ruff format --check`/
`ty check` all clean on every touched file (both `uv run ruff` and the
bare PATH `ruff`). No frob-core (rust) files touched -- cargo tests not
run, per the mission's "if you touch frob-core" qualifier.

### Changed
```
 .frob-release.json              |   2 +-
 docs/modules/dup.md             |  70 +++++++---
 docs/modules/lang.md            |   5 +
 src/frob/dup/_legacy.py         |  16 ++-
 src/frob/dup/_template.py       |  91 +++++++++----
 src/frob/lang/_common.py        |  32 +++--
 src/frob/lang/_models.py        |  14 ++
 tests/test_dup_cross_lang.py    | 152 +++++++++++++++------
 tests/unit/test_dup_template.py | 109 ++++++++++++++-
 tests/unit/test_memo.py         |  41 ++++++
 tickets.md                      | 293 ++++++++++++++++++++++++++++++++++++++--
 11 files changed, 714 insertions(+), 111 deletions(-)
```

### Evidence
- `tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_matching_type_annotations_propose_one_shared_type_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestTypeHoleClassificationRust::test_value_only_divergence_is_never_misclassified_as_a_type_hole` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestTypeHoleClassificationC::test_matching_type_annotations_propose_one_shared_type_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestTypeHoleClassification::test_type_position_in_one_member_only_stays_a_value_hole` (pytest node id, verified passing when recorded)

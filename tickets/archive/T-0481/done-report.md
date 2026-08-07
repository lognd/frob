## Done report

Made CloneTemplate.skeleton_text and CloneBinding.source_text render the
literal source characters via TreeNode.span byte offsets instead of the
prior structural label(child, ...) skeleton, and taught
CloneTemplate.suggested_signature to reuse a real identifier name when
every member's bound text at a hole agrees on one plain identifier,
falling back to hole_N otherwise. Fixed the COV005 fallout from the WIP
diff (frob:doc directives that had ridden onto the newly extracted
private helpers _region_tree/_render_literal instead of staying on the
public build_group_template), added a termination invariant to the new
recursive _render_literal, corrected the ticket's stale scope glob
(tests/test_dup.py never existed; the real coverage lives in
tests/unit/test_dup_template.py, via frob ticket scope), and refreshed
the pre-work sweep. Updated docs/modules/dup.md's "Readable rendering,
not literal source" section to describe the new literal-rendering
behavior and the suggested_signature identifier-reuse rule.

CAVEAT (pre-existing, not introduced by this ticket, out of T-0481's
scope to fix): `git diff main --stat` in this worktree shows
`src/frob/strata/_code_binding.py` and
`tests/unit/strata/test_code_binding.py` reverting T-0416's landed
docstring wording and regression test, even after a clean `git merge
main` with no reported conflicts on those files. Confirmed this predates
any change in this session -- `git diff <pre-session-WIP-commit> main`
for those two files already showed the same divergence before I touched
anything. Neither file is in T-0481's scope; I did not touch them. The
coordinator should re-merge/patch main's version of those two files
before landing this branch, or the land will silently revert T-0416.

### Changed
```
 src/frob/dup/_template.py | 204 +++++++++++++++++++++++++++++++++++++---------
 tickets.md                |   2 +-
 2 files changed, 168 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_one_leaf_divergence_yields_one_hole_with_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_identical_bodies_yield_zero_holes` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_three_member_group_folds_to_one_shared_skeleton` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_literal_rendering_preserves_source_text_not_a_skeleton` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_suggested_signature_falls_back_when_not_a_plain_identifier` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_single_member_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestBuildGroupTemplate::test_unrecoverable_subtree_returns_none_not_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestHoleParamName::test_reuses_shared_plain_identifier` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestHoleParamName::test_falls_back_when_members_disagree` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_template.py::TestHoleParamName::test_falls_back_when_shared_text_is_not_a_plain_identifier` (pytest node id, verified passing when recorded)

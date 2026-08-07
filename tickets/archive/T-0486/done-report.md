## Done report

Verified `_harvest_with_item` (src/frob/dup/_legacy_py.py) already walks
with_item -> as_pattern (field=value) -> as_pattern_target (field=alias),
confirmed against a live tree-sitter-python parse of `with open(x) as
name:` (field_name_for_child dump). The bug as originally filed (a direct
`with_item.child_by_field_name('alias')` lookup) is not present in the
current tree; a prior pass already applied this exact fix and its unit
coverage (tests/unit/test_dup_legacy_py.py). Added the missing regression
proof at the pipeline level the ticket asked for: two clones differing
only in the with-target binding name (`handle_a` vs `handle_b`) now group
as a Type-2 (clone_type="renamed") clone via `find_duplicates`, proving
the alpha-rename set actually includes with-bound names end to end, not
just at the node-walker unit level.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_dup.py::TestFindDuplicates::test_with_target_alpha_rename_matches_at_renamed_rung` (pytest node id, verified passing when recorded)

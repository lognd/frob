## Done report

Root-caused via direct `frob.lang._extract.extract()` calls (not
assumed): rust's grammar keeps each `#[...]` as its own SIBLING
`attribute_item` node directly before the item it decorates -- unlike
python's `decorated_definition`, which wraps the whole decorator stack
plus the `def` into one node whose span already starts at the first
decorator. A rust item's own tree-sitter span therefore starts at the
`pub fn`/`pub struct`/... keyword line, never at a preceding
attribute. `find_following_symbol` only looks within 2 lines past a
comment (block)'s end line -- one attribute line above the comment
still lands the item's span within that window (1-line gap), but 2+
stacked attribute lines push the item's un-widened span 3+ lines below
the comment, outside the window. Confirmed directly: `extracted 1
symbols, 1 comments` with `following=None` for the 2-attribute case
pre-fix, `following='Foo'` post-fix; 0/1-attribute and below-all-
attributes placements were unaffected either way.

Fix: added `_symbol_span(node)` to `src/frob/lang/_walk_rust.py` --
`span_of(node)` widened backward to the earliest directly-preceding
`attribute_item` sibling, used for the `RawSymbol.span` field ONLY (the
field `find_enclosing_symbol`/`find_following_symbol` compare against
for comment binding). `sig_tokens`/`body_tokens` still hash `node`
itself directly, unaffected -- this is purely a comment-binding-window
fix, mirroring `_walk_python.py::_effective_node`'s python decorator
handling. Used in both `_function_symbol` and `_named_symbol` (structs/
traits/enums/consts/statics all route through one of these two).

Tests added (`tests/test_lang.py::TestParseTsRustCppC`, all against
real `parse_file()` + real `.rs` fixture files, not mocks):
`test_rust_directive_binds_above_stacked_attributes` (2 attributes,
the reported bug), `test_rust_directive_binds_above_single_attribute`
(1 attribute, already worked -- guard against regressing it),
`test_rust_directive_binds_directly_above_keyword_no_attrs` (0
attributes), `test_rust_directive_binds_below_attributes_workaround_
placement` (the lithos/feldspar WORKAROUND placement -- directive
below all attributes, directly above the keyword -- confirmed it was
never broken and stays valid after this fix, per the coordinator's
explicit requirement).

All 4 new tests plus the full existing `TestParseTsRustCppC` class
pass (9/9). Full repo suite result in the final aggregate report.

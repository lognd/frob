## Done report

Shape taken: (A) with a (B)-style resolution, per the prior diagnosis's two
options -- neither pure shape fit cleanly, so I combined them: emit a real,
bindable AST-level symbol for the macro block (shape A, so the comment
DSL's existing following-symbol mechanism attaches the directive instead of
falling through to the bare-path fallback), then resolve that symbol's
TESTS edges at FILE granularity against cargo-collected ids (shape B,
since proptest's expansion names each synthesized #[test] fn after its OWN
`fn` identifier inside the macro's opaque token_tree -- verified directly
with `tree_sitter_language_pack.get_parser("rust")`: a `proptest! { #[test]
fn foo(...) {...} }` block parses to one `macro_invocation` node whose body
is a single `token_tree` with zero `function_item` descendants, so no
exact per-case node id can ever be derived from the AST alone without
scanning raw tokens inside the tree -- a separately-scoped effort).

Changed:
- src/frob/lang/_walk_rust.py::_TEST_MACRO_NAMES -- recognized
  test-generating macro names (proptest, prop_compose), extensible.
- src/frob/lang/_walk_rust.py::_MACRO_SYMBOL_SUFFIX -- private (no doc
  obligation) `!` qualname marker (never valid in a real rust identifier)
  flagging a macro stand-in symbol without needing a 6th SymbolKind.
- src/frob/lang/_walk_rust.py::_rust_test_macro_name -- macro-name
  recognition for one macro_invocation node.
- src/frob/lang/_walk_rust.py::_macro_symbol -- builds the non-public
  stand-in RawSymbol for a recognized test-macro block.
- src/frob/lang/_walk_rust.py::_visit -- new branch appending a
  _macro_symbol for a recognized test-generating macro_invocation.
- src/frob/lang/_walk_rust.py::_walk_rust -- docstring updated.
- src/frob/gates/__init__.py -- imports _MACRO_SYMBOL_SUFFIX.
- src/frob/gates/__init__.py::_macro_symbol_file -- detects a macro
  stand-in symref and extracts its file path.
- src/frob/gates/__init__.py::_macro_file_collected -- file-granularity
  "does this file have >=1 collected case" check.
- src/frob/gates/__init__.py::_valid_edges -- new branch: a macro-stand-in
  edge validates via _macro_file_collected instead of exact/prefix node-id
  matching.
- src/frob/gates/__init__.py::_case_count -- new branch: a macro-stand-in
  edge counts every collected case under the same file (can't isolate
  which cases came from the block itself, since none are named after it).
- TEST001/TEST002 (`_test001_002_one`) are unaffected: the macro stand-in
  symbol is minted `public=False`, so it is never itself subject to
  TEST001/TEST002's "public symbol owes a unit test" obligation -- only
  its role as an edge *target* for other public symbols' directives
  matters, and that path is unchanged (a directive whose src IS the macro
  stand-in only shows up via TEST003/TEST007 package-level edges in
  practice, which is what this ticket's litmus exercises).
- Real #[test] fn binding (function_item nodes, _function_symbol,
  _symbol_span's attribute-stack widening) untouched -- no macro name
  outside _TEST_MACRO_NAMES gets a stand-in symbol (verified by
  test_rust_non_test_macro_does_not_bind: a plain `vec!` macro mints
  nothing).

Rust litmus fixture/tests added (all via the tmp_path `_write` + tree-sitter
parse pattern every other rust binding test in this repo already uses --
no real Cargo.toml/proptest dev-dependency exists in this repo's own
frob-core/strata-core crates, so no `.rs` source under those crates
changed and no new buildable crate was needed):
- tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_proptest_macro_block
  -- a `// frob:tests ... kind="integration"` comment directly above a
  `proptest! { #[test] fn prop_roundtrip(...) {...} }` block binds
  (`comment.following == "proptest!"`), and the emitted symbol is
  `kind=FUNCTION, public=False`.
- tests/test_lang.py::TestParseTsRustCppC::test_rust_non_test_macro_does_not_bind
  -- a `vec!` macro invocation mints no `!`-suffixed symbol.
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_proptest_macro_block
  -- the real litmus: a `frob:tests strata-core/src/lib.rs kind="integration"`
  comment above a `proptest! {...}` block in
  `strata-core/tests/prop_parse.rs`, with `CollectedTests` simulating
  cargo's real output (`strata-core/tests/prop_parse.rs::prop_parse_roundtrip`,
  named after the fn inside the macro body, never after `proptest!`
  itself), satisfies TEST003 -- `"TEST003" not in _rules(violations)`.

Evidence (collected, verified with a real pytest run, not estimated):
```
tests/test_gates.py::TestTestGate::test_test003_satisfied_by_proptest_macro_block
tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_proptest_macro_block
tests/test_lang.py::TestParseTsRustCppC::test_rust_non_test_macro_does_not_bind
```
`pytest tests/test_gates.py::TestTestGate::test_test003_satisfied_by_proptest_macro_block tests/test_lang.py::TestParseTsRustCppC::test_rust_directive_binds_above_proptest_macro_block tests/test_lang.py::TestParseTsRustCppC::test_rust_non_test_macro_does_not_bind -v`
-> `3 passed in 1.01s`.

Also run clean: `pytest tests/test_testing.py tests/test_gates.py tests/test_lang.py -q` (all pass), full `pytest -q` (all pass, no regressions), `ruff check` + `ruff format --check` (both PATH and `uv run` variants) clean, `ty check` clean on both touched source files.

No `.rs` file inside `frob-core/`/`strata-core/` was changed (this is a
python-side extraction/gates fix only), so `cargo test` for those crates
is unaffected by this change; `make core` was re-run in this worktree and
both crates still build.

Filed: none (no out-of-scope discoveries).

Gates: `frob check --stamp-baseline` (before) then `frob check --delta`
(after) both show `0 errors`; the sole reported delta warning
(`TEST005: src/frob/testing/_collect.py::collect_python_tests branch
coverage 85.7%...`) was confirmed PRE-EXISTING and unrelated -- reproduced
identically by stashing this ticket's diff, re-running `make coverage` +
`frob check --delta` against the unmodified tree (same warning, same
file/line, `collect_python_tests` has nothing to do with this rust/gates
fix), then restoring the diff. `frob check --ticket T-0318` (after a
fresh `frob ticket sweep T-0318` re-run since the sweep goes stale on
every edit): `0 errors, 1 warning, 204 waived` -- the one warning is the
same pre-confirmed-pre-existing `collect_python_tests` TEST005. Getting to
0 errors under `--ticket` (which additionally runs SCOPE001/PRE001/COV001
against this ticket) required one fix beyond the --delta pass: the new
module-level constant `_walk_rust.py::MACRO_SYMBOL_SUFFIX` tripped COV001
(public symbol, no frob:doc edge) -- renamed to `_MACRO_SYMBOL_SUFFIX`
(private, matching every other internal constant in this module) rather
than adding a doc edge, since `docs/modules/lang.md` is outside this
ticket's declared scope and the constant has no reason to be part of the
module's public surface (only `frob.gates`, an already-coupled internal
consumer via `frob.lang._walk_rust`, imports it). `git diff main
--diff-filter=D --stat` is empty (deletion-filter clean).

NOT closing -- leaving for reviewer per playbook section 11.

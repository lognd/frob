## Done report

Wired tree-sitter-kotlin into frob.lang as a raw-walk-only layer (no
normalized-model mapping, per this ticket's explicit scope cut -- that
adapter is T-0614's job, blocked on this ticket plus T-0610).

`tree-sitter-language-pack` (already a pyproject dependency) bundles a
kotlin grammar directly -- `get_parser("kotlin")`/`get_language("kotlin")`
both resolve without adding a separate `tree-sitter-kotlin` pin. Verified
interactively before writing any code. Documented this decision inline in
pyproject.toml so a future reader does not re-litigate "why no kotlin
pin".

Added `src/frob/lang/_walk_kotlin.py`, mirroring `_walk_typescript.py`/
`_walk_rust.py`'s module shape but intentionally minimal: `parse_kotlin`
(source bytes -> tree-sitter `Tree` via the language pack) and
`raw_kotlin_tree` (source bytes -> `TreeNode`, reusing `_common.py`'s
existing `export_tree` primitive with kotlin's two comment node types,
`line_comment`/`multiline_comment`). No `_EXTENSION_TABLE`/`_WALKERS`/
`COMMENT_TYPES` central-dispatch wiring in `frob.lang.__init__`/
`_extract.py` -- deliberately left to T-0614 per the ticket's declared
scope (only `pyproject.toml` + `_walk_kotlin.py`).

Extended scope (via `frob ticket scope --add`, each with a reason) for
files the ticket's own acceptance criteria structurally required but
were not in the planner's initial scope list:
- `tests/unit/test_lang_kotlin.py` -- the smoke test the acceptance
  criteria explicitly asks for (".kt fixture parses without error"; top-
  level node types include class/fun).
- `CHANGELOG.md`, `uv.lock`, `.frob-release.json` -- REL001 fired
  because the two new public functions plus the public `COMMENT_TYPES`
  constant are a MINOR public-API change; `pyproject.toml`'s version
  needed bumping (already in scope) and a matching CHANGELOG entry.

This session's `main` moved forward several times WHILE this ticket was
in flight (other agents landing T-0325, T-0501, T-0609, T-0264, etc. in
parallel), each of which was itself a public-API-changing release bump --
`pyproject.toml`'s version went 0.77.0 -> 0.78.0 -> 0.79.0 -> 0.80.0
across three `git merge main` passes as the target moved, with the
CHANGELOG's own version headings, `.frob-release.json`'s stamped
manifest, and `uv.lock` re-resolved and re-committed at each step. The
final state (0.80.0) is the union of this ticket's public API plus
everything else that landed on `main` up to the last merge; `frob release
check` at the end reports "since 0.80.0: none change -> need >= 0.80.0
(current 0.80.0): OK" and `git diff main --diff-filter=D --stat` is empty
(the deletion-filter land rule, playbook section 9) after the final
merge.

Smoke test (tests/unit/test_lang_kotlin.py, 6 tests, all passing):
verifies a trivial `.kt` fixture (class + fun) and a `.kts` script
fixture both parse with `not tree.root_node.has_error`; asserts
`class_declaration` is a top-level child and `function_declaration`
appears somewhere in the tree (the ticket's literal "class, fun" node-
type acceptance check); and covers `raw_kotlin_tree`'s TreeNode shape
plus comment-stripping.

Every new public symbol (`parse_kotlin`, `raw_kotlin_tree`,
`COMMENT_TYPES`) carries a `frob:ticket T-0613`, a `frob:doc` edge to
`docs/modules/lang.md#per-language-walker-notes` (an existing anchor --
docs/modules/lang.md itself is out of scope so no new anchor was added),
and `frob:tests` edges to the specific test methods that exercise it.

Gates: `frob check --ticket T-0613` is clean (0 errors, ruff-check/ruff-
format/ty/frob-cycle/frob-dup/frob-arch/frob-exports/gate:ARCH/COV/DEAD/
INV/LANG/PERF/PII/REF/SEC/TEST/WAIVE/WALK all pass -- final gate-summary
"0 errors, 385 warnings, 188 waived" measured after the last merge and
`make core` rebuild).

### Changed
```
 .frob-release.json             |   3 ++
 CHANGELOG.md                   |   1 +
 pyproject.toml                 |   7 +++
 src/frob/lang/_walk_kotlin.py  |  58 ++++++++++++++++++++++
 tests/unit/test_lang_kotlin.py |  90 +++++++++++++++++++++++++++++++++
 tickets.md                     | 110 +++++++++++++++++++++++++++++++++++++++--
 6 files changed, 266 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kts_fixture_parses_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_top_level_node_types_include_class_and_fun` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_returns_tree_node` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comments_are_stripped` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comment_types_cover_kotlin_line_and_block_comments` (pytest node id, verified passing when recorded)

## Done report

Wires kotlin into `frob.lang`'s central dispatch so a real `.kt`/`.kts`
file reaches `frob.lang.parse_file`/`frob check` without a `KeyError`
(this ticket's own acceptance criterion) -- the gap T-0614's Done report
flagged and filed this ticket for.

Adds `frob.lang._walk_kotlin._walk_kotlin`, a `RawSymbol` walker mirroring
`_walk_rust.py`/`_walk_typescript.py`'s shape (positional node-type lookups
throughout, not field-based -- `tree-sitter-kotlin`'s grammar exposes
almost no named fields, verified interactively before writing any walker
code, matching `frob.arch._kotlin`'s T-0614 finding for the same grammar).
Maps: top-level and class-member `function_declaration`s (FUNCTION/METHOD);
`class_declaration` (kotlin's grammar folds `interface` into the same node
type, so both come back as CLASS for free) with its `class_body` members
recursed into; top-level `property_declaration`s (`val`/`var`, mapped to
CONST -- kotlin's analogue of rust's `const_item`/`static_item`); and
`type_alias` (mapped to TYPE, kotlin's analogue of rust's `type_item`).
Publicness (`_kt_public`): kotlin is public-by-default -- only an explicit
`private`/`protected`/`internal` `visibility_modifier` narrows it (the
inverse of rust's opt-in `pub`). KDoc (`/** ... */`) binds as `doc_text`
via the shared `_leading_doc_comment` helper, same as every other grammar.

Registers `.kt`/`.kts` in `frob.lang.__init__`'s `_EXTENSION_TABLE` (both
routing through the SAME `get_parser("kotlin")` chokepoint T-0613's
`parse_kotlin` already used standalone) and adds a `"kotlin"` entry to
`_extract.py`'s `_WALKERS`/`COMMENT_TYPES` dispatch tables -- the two
pieces T-0614's Done report identified as the missing link (wiring
`_EXTENSION_TABLE` alone, without a `_WALKERS` entry, would `KeyError` on
any real `.kt` file `frob check` scanned).

NOT changed: `frob.arch._kotlin.KotlinAdapter` (T-0614, already landed,
untouched); this ticket only wires the `frob.lang` RawSymbol/graph path.
`object_declaration` (kotlin singleton syntax), `enum class`'s
`enum_class_body`/`enum_entry`, and a class's `secondary_constructor` are
NOT mapped to a `RawSymbol` -- the same scope cut T-0614's arch adapter
already documented for the identical grammar gap (no equivalent construct
exists for `NormalizedClass`/`RawSymbol` either way); left for a follow-up
if a real repo needs them, not silently dropped.

Verified against hand-built kotlin snippets (no shared `tests/fixtures`
dir exists for kotlin, matching the TS/rust/T-0614 precedent): 15 tests in
`tests/unit/test_lang_kotlin.py` -- the 6 pre-existing T-0613 smoke tests
(untouched, still pass) plus 9 new ones: `TestWalkKotlin` (6 tests: top-
level function, class+method, bodyless interface method, private-is-not-
public, top-level property+typealias, leading KDoc binds as doc_text) and
`TestParseFileDispatchesKotlin` (3 tests: a real `.kt` file on disk flows
through `frob.lang.parse_file` into `RawSymbol`s with no `KeyError`, a
`.kts` script resolves the same "kotlin" language label, and
`supported_languages()`/`supported_extensions()` both learn about kotlin).

Mutation-kill hand-verified (per playbook): flipped `_kt_public`'s `not`
(private symbols would read public) -- 2 tests failed as expected, both
caught; flipped the class-vs-top-level `in_class` guard on the property
walk (`and not in_class` -> `and in_class`) -- the top-level property test
failed with a KeyError as expected. Both reverted after confirming the
kill.

Gates: `uv run frob check --only lint --ticket T-0723` clean (ruff-check/
ruff-format/ty, 0 issues) under both the project-pinned `uv run ruff` and
the PATH `ruff`. `uv run frob check --only static --ticket T-0723`: 0
errors (pre-existing warnings only, none touching this ticket's files).
`uv run frob check --only gates-fast --ticket T-0723`: 0 errors after
fixing one real finding this diff introduced (COV005 -- an earlier
`frob:doc` directive on the private `_walk_kotlin` function rode along
from a nearby public symbol's anchor; removed, matching `_walk_rust.py`'s
own precedent of no `frob:doc` on its private walker) and refreshing the
pre-work sweep (`frob ticket sweep T-0723`, PRE001). The one remaining
error there, `TICK003` (61+ closed tickets un-archived in `tickets.md`,
threshold 60), is a pre-existing, repo-wide ledger-archival debt unrelated
to this ticket's scope -- not caused by this change and not something a
single-ticket worktree should fix. `uv run frob check --only gates-native
--ticket T-0723` and `--only gates-security --ticket T-0723` both 0
errors. Deletion filter (`git diff main --diff-filter=D --stat`) empty
after a mid-ticket `git merge main` (main had advanced past this
worktree's original merge point; the ledger merge-driver spliced
`tickets.md` cleanly, no manual conflict resolution needed).

No drafts filed -- the only out-of-scope constructs found (object
declarations, enum bodies, secondary constructors) were already documented
scope cuts in T-0614's Done report for the identical grammar gap, not new
discoveries.

### Changed
```
 src/frob/lang/__init__.py      |   9 ++
 src/frob/lang/_extract.py      |   3 +
 src/frob/lang/_walk_kotlin.py  | 184 +++++++++++++++++++++++++++++++++++++++--
 tests/unit/test_lang_kotlin.py | 124 ++++++++++++++++++++++++++-
 4 files changed, 311 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kts_fixture_parses_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_top_level_node_types_include_class_and_fun` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_returns_tree_node` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comments_are_stripped` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comment_types_cover_kotlin_line_and_block_comments` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_walks_top_level_function` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_walks_class_and_method` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_interface_method_has_no_body` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_private_symbol_is_not_public` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_top_level_property_and_typealias` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_leading_kdoc_comment_binds_as_doc_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kt_file_parses_into_the_symbol_graph` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kts_extension_also_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kotlin_is_a_supported_language_and_extension` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

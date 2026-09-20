## Done report

T-3232 -- frob.docs/frob.xref narrower per-language coverage than frob.lang

WHY

T-2996's cross-check found two places where frob.docs and frob.xref
hand-maintained their own, narrower copy of "which languages frob.lang
supports" instead of reading frob.lang's own registry:

1. frob.docs.extract_docstrings hard-filtered to
   `parsed.language != "python": return []`, so every non-python
   docstring (csharp XML doc comments, rust ///, java javadoc, etc,
   all of which frob.lang's per-language walkers already attach to
   RawSymbol.doc_text) was silently discarded.

2. frob.xref's `_LANG_EXTS` (the `--lang` filter) only had entries for
   python/c/cpp/strata, and `_SOURCE_EXTS` (which files get the precise
   tree-sitter-backed resolver vs. the cruder plain-text-scan fallback)
   only covered python+cpp -- so csharp/java/kotlin/bash/cuda/zig/
   typescript files always fell to the text-scan fallback, and
   `--lang csharp` filtered to zero files outright.

WHAT CHANGED

- src/frob/docs/__init__.py: extract_docstrings no longer filters by
  language; it dispatches on whatever frob.lang.parse_file returns.
  The module-level docstring extraction (_module_entries) is still
  python-only by necessity -- it uses python's own `ast` module, which
  cannot parse any other language, and RawSymbol/RawComment carry no
  module-docstring-equivalent for other languages.

  Fixing this exposed a second, latent bug in the same function:
  _docstring_for_symbol's CLASS branch used `"." not in sym.qualname`
  to distinguish a top-level class from a nested one. That check only
  worked because python has no namespace prefix on a top-level class's
  qualname. csharp/java/kotlin qualify even top-level classes with
  their namespace (e.g. "Frob.Sample.Widget"), so the old check
  misclassified every namespaced top-level class as "nested" and
  silently dropped its docstring -- which would have made the C# proof
  case fail with the class docstring simply missing, no error. Fixed
  by comparing each CLASS symbol's owner (qualname before the last
  dot) against the set of this file's own class qualnames, so "owner
  is a namespace, not another class in this file" reads as top-level
  regardless of dots in the name.

- src/frob/xref/__init__.py: _LANG_EXTS is now built once from
  frob.lang.supported_extensions() + frob.lang.language_for_extension()
  (a loop, not a second hand-typed table) plus the pre-existing cpp
  extras frob.lang's own table still lacks (.c++/.hxx/.h++, kept
  explicitly so this narrowing does not regress them). _SOURCE_EXTS is
  now frob.lang.tree_sitter_extensions() (every grammar frob.lang
  registers) plus those same cpp extras, so csharp/java/kotlin/bash/
  cuda/zig/typescript files route through the parsed resolver
  (_search_parsed) instead of the text-scan fallback.

- src/frob/lang/_extract.py: iter_identifiers' _IDENTIFIER_TYPES table
  (a SEPARATE hand-maintained language list from the one above, one
  level down -- this is what turns a parsed tree into the flat
  identifier-occurrence list frob.xref's usage search walks) had no
  csharp entry. Without it, _search_parsed found a csharp definition
  fine (that comes from RawSymbol, unaffected) but zero usages --
  iter_identifiers returned () for every csharp file. Added a
  "csharp": {"identifier"} entry, measured directly against the parse
  tree of tests/fixtures/lang/sample.cs (tree-sitter-c-sharp's
  identifier leaf is plainly "identifier", confirmed by walking the
  tree and listing every leaf node type containing "ident").

  java/cuda/kotlin/bash/zig/typescript are the same gap, still
  unfixed -- filed as T-4558 rather than guessed at, since
  each grammar's own leaf node naming needs the same kind of
  measurement against a real parse tree before an entry can be
  trusted (bash and zig in particular did not show an "identifier"-
  named leaf at all when checked, so this is not a one-line copy
  job).

- docs/modules/app.md, docs/commands/xref.md: updated the frobdocs-
  library and xref-command descriptions to state the actual language
  set / --lang contract instead of the stale python-only / python-or-
  cpp text (DRIFT prevention).

PROVEN CASE (the ticket's Deliver section)

Both proven against the existing static fixture
tests/fixtures/lang/sample.cs (a namespaced `Frob.Sample.Widget` public
class with XML `<summary>` doc comments on the class and its `Render`
method, which calls `Widget.Add`):

- frob.xref.xref("Add", <sample.cs>) and
  frob.xref.xref("Add", <sample.cs>, lang="csharp") both find the
  Widget.Add definition AND the Render() call-site usage.
  (tests/unit/test_xref.py::test_csharp_finds_definition_and_usage,
  test_csharp_finds_definition_and_usage_with_explicit_lang)

- frob.docs.extract_docstrings(<sample.cs>) returns both the class's
  "Adds two numbers" doc comment (symbol "Frob.Sample.Widget", kind
  "class") and the method's "Renders the widget" doc comment (symbol
  "Frob.Sample.Widget.Render", kind "method").
  (tests/unit/test_docs_module.py::test_extract_docstrings_csharp_class_and_method)

TESTS PER CRITERION

Criterion 1 (shared table, no dup language list):
  - tests/unit/test_xref.py::test_csharp_finds_definition_and_usage_with_explicit_lang
    (exercises the rebuilt _LANG_EXTS end to end)
  - Full existing test_xref.py / test_docs_module.py suites still pass
    unchanged for python/cpp (31/31 total, see below) -- proves the
    refactor is not a narrowing in disguise.

Criterion 2 (xref proven C# case):
  - tests/unit/test_xref.py::test_csharp_finds_definition_and_usage
  - tests/unit/test_xref.py::test_csharp_finds_definition_and_usage_with_explicit_lang

Criterion 3 (docs proven C# case):
  - tests/unit/test_docs_module.py::test_extract_docstrings_csharp_class_and_method
  - tests/unit/test_docs_module.py::test_extract_docstrings_unparseable_extension_returns_empty
    (renamed/reworked from the old
    test_extract_docstrings_non_python_file_returns_empty, which
    encoded the exact behavior this ticket removes -- now asserts the
    real remaining boundary, an extension frob.lang has no grammar for
    at all, rather than "non-python")

VERIFICATION RUN (verbatim tails)

$ PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist \
    tests/unit/test_docs_module.py tests/unit/test_xref.py
...............................                                          [100%]
SUITE-RESULT: exitstatus=0 collected=31 failed=0

$ PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist \
    tests/test_lang.py tests/system/test_cli_xref.py
........................................................................ [ 52%]
.................................................................        [100%]
SUITE-RESULT: exitstatus=0 collected=137 failed=0

$ ruff check <5 changed files>
All checks passed!

$ ruff format --check <5 changed files>
5 files already formatted

OUT OF SCOPE, NOT FIXED HERE

- java/cuda/kotlin/bash/zig/typescript entries in
  frob.lang._extract._IDENTIFIER_TYPES -- filed as T-4558
  (scope src/frob/lang/_extract.py). Until that lands, xref finds
  definitions but not usages for those languages' files (same gap
  T-3232 just fixed for csharp).

NOT LANDED per brief -- this worktree stays as-is for the coordinator
to land.

### Changed
```
 CHANGELOG.md                       |   3 +
 docs/commands/xref.md              |   4 +-
 docs/modules/app.md                |   8 ++
 src/frob/docs/__init__.py          |  64 +++++++++++---
 src/frob/lang/_extract.py          |  13 +++
 src/frob/xref/__init__.py          |  54 +++++++++---
 tests/unit/test_docs_module.py     |  35 +++++++-
 tests/unit/test_xref.py            |  40 +++++++++
 tickets/T-3232/done-report.md      | 174 +++++++++++++++++++++++++++++++++++++
 tickets/T-3232/ticket.md           |  13 ++-
 tickets/T-4558/ticket.md |  30 +++++++
 11 files changed, 403 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/unit/test_xref.py::test_csharp_finds_definition_and_usage_with_explicit_lang` (pytest node id, verified passing when recorded)
- `tests/unit/test_xref.py::test_csharp_finds_definition_and_usage` (pytest node id, verified passing when recorded)
- `tests/unit/test_docs_module.py::test_extract_docstrings_csharp_class_and_method` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Acceptance amendments
- [4] remove: removed "frob.docs.extract_docstrings and frob.xref's --lang/parsed-search dispatch on frob.lang's supported language set via a single shared table (frob.lang.supported_extensions/language_for_extension/tree_sitter_extensions), no second hand-maintained language list" (reason: duplicate created by a redundant accept retry while a stale land pid caused a false LandInProgress refusal; logan, 2026-09-16)

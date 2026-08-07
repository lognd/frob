## Done report

Reproduced: `frob.arch._models.ArchCategory` (`ArchCategory = Literal['pattern',
'signature', 'cve', 'crypto-hazard']`, a module-level bare-Literal type
alias) was never a graph symbol before this fix -- confirmed by parsing the
real file and checking `parsed.symbols` for the qualname before/after.
Only def/class nodes and SCREAMING_CASE constant assignments were walked
into `RawSymbol`s by `frob.lang._walk_python._visit`; a plain-CapWords
module-level assignment (type alias or otherwise) fell through both
branches silently.

Scope correction: the ticket named `src/frob/graph/**` as the fix location,
but the actual symbol walker lives in `src/frob/lang/_walk_python.py` --
`frob.graph` only consumes the `RawSymbol` tuples `frob.lang`'s per-language
walkers already produced (`frob.graph.__init__._symbol_record` wraps a
`RawSymbol` into a `SymbolRecord`, nothing more). Scope-added
`src/frob/lang/**` (the real fix location), `tests/test_lang.py` (the
walker's existing test module, where the regression tests live), and
`docs/modules/arch.md` (to remove the now-obsolete DOC006 waiver comment
this fix makes stale) with `--reason` recorded.

Fix (`src/frob/lang/_walk_python.py`): new `_type_alias_symbol` recognizes
three shapes and emits a `SymbolKind.TYPE` `RawSymbol` (the same bucket
every OTHER language walker -- Rust `type_item`, TypeScript
`type_alias_declaration`, Kotlin, C -- already uses for its own type
aliases; python was the one walker never populating it):
1. `type X = ...` (py>=3.12 `type_alias_statement`, a distinct grammar
   node) -- unambiguous, matched by node type.
2. `X: TypeAlias = ...` (PEP 613 explicit annotation, bare or dotted
   `typing.TypeAlias`) -- unambiguous, matched via the assignment's own
   `type` (annotation) field.
3. Bare `X = Literal[...]` (this repo's own idiom, the real repro) --
   deliberately narrow: only fires when the RHS is textually a
   `Literal[...]`/`typing.Literal[...]` subscript, not any arbitrary
   call/expression (that would silently re-scope `_const_symbol`'s
   existing SCREAMING_CASE constant population). Widening to
   `Union[...]`/`Optional[...]`/`TypeVar(...)` bare-RHS shapes is filed as
   a deliberate, separate follow-up (T-1033) rather than bundled
   in.

`_visit` tries the type-alias check FIRST, falling back to `_const_symbol`
only when it doesn't match -- mutually exclusive (a SCREAMING_CASE name
annotated `TypeAlias` is classified TYPE, never double-counted as CONST
too).

Regression tests (`tests/test_lang.py::TestParsePython`): bare
`X = Literal[...]`, annotated `X: TypeAlias = ...`, py>=3.12 `type X = ...`,
a private (`_`-prefixed) alias staying non-public, and an explicit guard
(`test_ordinary_assignments_are_unaffected_by_type_alias_detection`)
proving a SCREAMING_CASE constant, a bare non-Literal call assignment, and
a tuple-unpacking assignment all keep their exact pre-fix behavior (CONST
stays CONST; a non-type-alias-shaped bare assignment and a tuple target
both stay unindexed, unchanged).

Ripple check (T-1028 acceptance criterion 4): measured `frob check --only
dead_symbols` and `frob check --only coverage` BEFORE (walker reverted via
`git checkout <parent-commit> -- src/frob/lang/_walk_python.py tests/
test_lang.py docs/modules/arch.md`, gates run, then restored) and AFTER
this fix, full repo, both directions:
- dead_symbols: 0 errors, 13 warnings both before and after -- NO
  movement. The three newly-indexed symbols in this repo (ArchCategory,
  and the fixture/test-only aliases this change itself adds) are all
  referenced elsewhere, so none newly read as dead.
- coverage: 0 errors, 43 warnings both before and after (this repo's own
  `_walk_python.py`/`test_lang.py` COV002 findings from MY OWN new code
  were fixed with `frob:ticket T-1028` edges before this final
  measurement, so the net repo-wide count is unchanged from baseline).

No non-trivial gate-count movement to disclose or file a follow-up for.

### Changed
```
 docs/modules/arch.md          |   4 +-
 src/frob/lang/_walk_python.py | 132 ++++++++++++++++++++++++++++++++++++++++--
 tests/test_lang.py            |  96 ++++++++++++++++++++++++++++++
 tickets.md                    |  42 +++++++++++++-
 4 files changed, 265 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestParsePython::test_bare_literal_assignment_extracted_as_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_annotated_type_alias_extracted_as_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_py312_type_statement_extracted_as_type_symbol` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_private_type_alias_is_not_public` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_ordinary_assignments_are_unaffected_by_type_alias_detection` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 3944 warning(s), 339 waived
- error-findings: none (measured, zero errors)
